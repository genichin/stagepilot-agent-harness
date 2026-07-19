#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPL = ROOT / 'scripts' / 'runner-launch-impl.sh'
QC = ROOT / 'scripts' / 'runner-launch-qc.sh'
SUPERVISE = ROOT / 'scripts' / 'supervise_worker.py'


class SupervisedLauncherPathResolutionTest(unittest.TestCase):
    def run_launcher(
        self,
        launcher: Path,
        handoff_name: str,
        extra_args: list[str] | None = None,
        *,
        with_verdict_output: bool = False,
    ) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project = tmp_path / 'project'
            bin_dir = tmp_path / 'bin'
            capture_file = tmp_path / 'python3-argv.json'
            bin_dir.mkdir(parents=True)
            project.mkdir()
            subprocess.run(['git', 'init', '-q'], cwd=project, check=True)

            delivery_dir = project / '.stagepilot' / 'delivery' / 'case'
            delivery_dir.mkdir(parents=True)
            handoff = delivery_dir / handoff_name
            state = delivery_dir / 'state.json'
            handoff.write_text('stub handoff\n', encoding='utf-8')
            context = delivery_dir / handoff_name.replace('.md', '-implementation-context.md')
            context.write_text(
                '# Implementation context\n\n'
                '## Target files\n- tracked.txt\n\n'
                '## Edit anchors\n- tracked.txt: beginning of file\n\n'
                '## Service seams\n- N/A; direct file edit only.\n\n'
                '## Return shape\n- N/A; no data contract change.\n\n'
                '## Render insertion point\n- N/A; no UI render insertion.\n\n'
                '## Test assertions\n- existing tracked.txt assertion remains representative.\n\n'
                '## Forbidden data exposure\n- N/A; no sensitive data path.\n\n'
                '## Allowed search budget\n- No broad search unless listed anchors fail.\n\n'
                '## Validation commands\n- python3 -m pytest -q\n\n'
                '## First progress deadline\n- 2 minutes; write progress artifact before broad reading.\n',
                encoding='utf-8',
            )
            state.write_text('{}\n', encoding='utf-8')
            verdict_output = delivery_dir / 'qc-verdict.json'
            if with_verdict_output:
                verdict_output.write_text('{"controller_template": true}\n', encoding='utf-8')

            python_stub = bin_dir / 'python3'
            python_stub.write_text(
                '#!/usr/bin/python3\n'
                'import json, os, sys\n'
                'Path = __import__("pathlib").Path\n'
                'capture = Path(os.environ["CAPTURE_FILE"])\n'
                'capture.write_text(json.dumps(sys.argv[1:]), encoding="utf-8")\n'
                'raise SystemExit(0)\n',
                encoding='utf-8',
            )
            python_stub.chmod(0o755)

            hermes_stub = bin_dir / 'hermes'
            hermes_stub.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
            hermes_stub.chmod(0o755)

            env = os.environ.copy()
            env['PATH'] = f"{bin_dir}:{env['PATH']}"
            env['CAPTURE_FILE'] = str(capture_file)

            launch_args = [str(launcher), '--supervised', '--foreground-supervised', *(extra_args or [])]
            if with_verdict_output:
                launch_args.extend(['--verdict-output', str(verdict_output)])
            launch_args.extend([str(handoff), str(state)])
            result = subprocess.run(
                launch_args,
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
            argv = json.loads(capture_file.read_text(encoding='utf-8'))
            progress_path = project / '.stagepilot' / 'worker-progress' / handoff_name.replace('.md', '.md')
            return {
                'argv': argv,
                'stdout': result.stdout,
                'project': str(project),
                'progress_path': str(progress_path),
                'verdict_output': str(verdict_output),
            }

    def assert_common(
        self,
        observed: dict,
        label: str,
        profile: str,
        handoff_name: str,
        *,
        expect_preset: bool,
    ) -> None:
        argv = observed['argv']
        project = observed['project']
        progress_path = observed['progress_path']
        self.assertEqual(argv[0], str(SUPERVISE))
        self.assertIn('--label', argv)
        self.assertEqual(argv[argv.index('--label') + 1], label)
        self.assertIn('--workdir', argv)
        self.assertEqual(argv[argv.index('--workdir') + 1], project)
        self.assertIn('--profile', argv)
        self.assertEqual(argv[argv.index('--profile') + 1], profile)
        self.assertIn('--progress-artifact', argv)
        self.assertEqual(argv[argv.index('--progress-artifact') + 1], progress_path)
        if expect_preset:
            self.assertIn('preset: default', observed['stdout'])
        self.assertIn('checkpoint_minutes: 10', observed['stdout'])
        self.assertIn('max_minutes: 60', observed['stdout'])
        if profile in {'dev-impl', 'dev-qc'}:
            self.assertIn('env', argv)
            env_index = argv.index('env')
            self.assertEqual(argv[env_index + 1], f'HERMES_CWD={project}')
            self.assertEqual(argv[env_index + 2], f'TERMINAL_CWD={project}')
            self.assertEqual(argv[env_index + 3], 'hermes')
        if profile == 'dev-impl':
            self.assertIn('first_progress_minutes: 2', observed['stdout'])
            self.assertIn('readiness_gate: 1', observed['stdout'])
            self.assertIn('implementation_context:', observed['stdout'])
            prompt = argv[-1]
            self.assertIn('PATCH-FIRST MODE', prompt)
            self.assertIn('patch/write an in-scope file', prompt)
            self.assertIn('Do not rediscover or redesign service/data-source choices', prompt)
            self.assertIn('WORKER LANE SESSION', prompt)
            self.assertIn('Same-lane continuity is valid only for healthy same-handoff follow-up', prompt)
            self.assertIn('bounded same-scope correction', prompt)
        if profile == 'dev-qc':
            self.assertIn('first_progress_minutes: 5', observed['stdout'])
            prompt = argv[-1]
            self.assertIn('WORKER LANE SESSION', prompt)
            self.assertIn('First review and re-review after implementation rework are fresh by default', prompt)
            self.assertIn('supervisor evidence is incomplete', prompt)
        self.assertIn(f'progress_artifact: {progress_path}', observed['stdout'])
        self.assertNotIn(f'{project}/scripts/supervise_worker.py', observed['stdout'])

    def test_impl_supervised_launcher_uses_harness_helper_and_target_worktree(self) -> None:
        observed = self.run_launcher(IMPL, 'impl-handoff.md', extra_args=['--preset', 'default'])
        self.assert_common(observed, label='impl', profile='dev-impl', handoff_name='impl-handoff.md', expect_preset=True)


    def test_impl_supervised_defaults_to_background_and_writes_exit_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project = tmp_path / 'project'
            bin_dir = tmp_path / 'bin'
            capture_file = tmp_path / 'python3-argv.json'
            bin_dir.mkdir(parents=True)
            project.mkdir()
            subprocess.run(['git', 'init', '-q'], cwd=project, check=True)
            delivery_dir = project / '.stagepilot' / 'delivery' / 'case'
            delivery_dir.mkdir(parents=True)
            handoff = delivery_dir / 'impl-handoff.md'
            state = delivery_dir / 'state.json'
            context = delivery_dir / 'impl-handoff-implementation-context.md'
            handoff.write_text('stub handoff\n', encoding='utf-8')
            state.write_text('{}\n', encoding='utf-8')
            context.write_text(
                '# Implementation context\n\n'
                '## Target files\n- tracked.txt\n\n'
                '## Edit anchors\n- tracked.txt: beginning\n\n'
                '## Service seams\n- N/A.\n\n'
                '## Return shape\n- N/A.\n\n'
                '## Render insertion point\n- N/A.\n\n'
                '## Test assertions\n- N/A.\n\n'
                '## Forbidden data exposure\n- N/A.\n\n'
                '## Allowed search budget\n- none.\n\n'
                '## Validation commands\n- true\n\n'
                '## First progress deadline\n- 2 minutes.\n',
                encoding='utf-8',
            )
            python_stub = bin_dir / 'python3'
            python_stub.write_text(
                '#!/usr/bin/python3\n'
                'import json, os, sys\n'
                'Path = __import__("pathlib").Path\n'
                'capture = Path(os.environ["CAPTURE_FILE"])\n'
                'capture.write_text(json.dumps(sys.argv[1:]), encoding="utf-8")\n'
                'raise SystemExit(0)\n',
                encoding='utf-8',
            )
            python_stub.chmod(0o755)
            hermes_stub = bin_dir / 'hermes'
            hermes_stub.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
            hermes_stub.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = f"{bin_dir}:{env['PATH']}"
            env['CAPTURE_FILE'] = str(capture_file)
            session = 'test-impl-supervised-bg'
            subprocess.run(['tmux', 'kill-session', '-t', session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            result = subprocess.run(
                [str(IMPL), '--supervised', '--session-name', session, str(handoff), str(state)],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
            self.assertIn('background: true', result.stdout)
            self.assertIn('poll: wait for exit_file', result.stdout)
            exit_file = None
            for line in result.stdout.splitlines():
                if line.startswith('exit_file: '):
                    exit_file = Path(line.split(': ', 1)[1])
            self.assertIsNotNone(exit_file)
            assert exit_file is not None
            # Background mode returns immediately; the runner is responsible for
            # polling the advertised exit/log/final-result artifacts. Do not depend
            # on tmux inheriting this test process environment.
            self.assertIn('log_file: ', result.stdout)
            self.assertIn('supervised: true', result.stdout)


    def test_impl_launcher_auto_supervises_when_handoff_names_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project = tmp_path / 'project'
            bin_dir = tmp_path / 'bin'
            capture_file = tmp_path / 'python3-argv.json'
            bin_dir.mkdir(parents=True)
            project.mkdir()
            subprocess.run(['git', 'init', '-q'], cwd=project, check=True)

            delivery_dir = project / '.stagepilot' / 'delivery' / 'case'
            delivery_dir.mkdir(parents=True)
            context = delivery_dir / 'custom-context.md'
            context.write_text(
                '# Implementation context\n\n'
                '## Target files\n- tracked.txt\n\n'
                '## Edit anchors\n- tracked.txt: beginning of file\n\n'
                '## Service seams\n- N/A; direct file edit only.\n\n'
                '## Return shape\n- N/A; no data contract change.\n\n'
                '## Render insertion point\n- N/A; no UI render insertion.\n\n'
                '## Test assertions\n- existing tracked.txt assertion remains representative.\n\n'
                '## Forbidden data exposure\n- N/A; no sensitive data path.\n\n'
                '## Allowed search budget\n- No broad search unless listed anchors fail.\n\n'
                '## Validation commands\n- python3 -m pytest -q\n\n'
                '## First progress deadline\n- 2 minutes.\n',
                encoding='utf-8',
            )
            handoff = delivery_dir / 'impl-handoff.md'
            handoff.write_text(f'Implementation context: `{context}`\n', encoding='utf-8')
            state = delivery_dir / 'state.json'
            state.write_text('{}\n', encoding='utf-8')

            python_stub = bin_dir / 'python3'
            python_stub.write_text(
                '#!/usr/bin/python3\n'
                'import json, os, sys\n'
                'Path = __import__("pathlib").Path\n'
                'capture = Path(os.environ["CAPTURE_FILE"])\n'
                'capture.write_text(json.dumps(sys.argv[1:]), encoding="utf-8")\n'
                'raise SystemExit(0)\n',
                encoding='utf-8',
            )
            python_stub.chmod(0o755)
            hermes_stub = bin_dir / 'hermes'
            hermes_stub.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
            hermes_stub.chmod(0o755)

            env = os.environ.copy()
            env['PATH'] = f"{bin_dir}:{env['PATH']}"
            env['CAPTURE_FILE'] = str(capture_file)
            result = subprocess.run(
                [str(IMPL), '--foreground-supervised', str(handoff), str(state)],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
            self.assertIn('notice: auto-enabled --supervised', result.stderr)
            self.assertIn(f'implementation_context: {context}', result.stdout)
            argv = json.loads(capture_file.read_text(encoding='utf-8'))
            self.assertEqual(argv[0], str(SUPERVISE))
            self.assertIn('--first-progress-minutes', argv)

    def test_impl_readiness_gate_requires_data_contract_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project = tmp_path / 'project'
            bin_dir = tmp_path / 'bin'
            bin_dir.mkdir(parents=True)
            project.mkdir()
            subprocess.run(['git', 'init', '-q'], cwd=project, check=True)
            delivery_dir = project / '.stagepilot' / 'delivery' / 'case'
            delivery_dir.mkdir(parents=True)
            handoff = delivery_dir / 'impl-handoff.md'
            state = delivery_dir / 'state.json'
            context = delivery_dir / 'impl-handoff-implementation-context.md'
            handoff.write_text('stub handoff\n', encoding='utf-8')
            state.write_text('{}\n', encoding='utf-8')
            context.write_text(
                '# Implementation context\n\n'
                '## Target files\n- tracked.txt\n\n'
                '## Edit anchors\n- tracked.txt: beginning of file\n\n'
                '## Allowed search budget\n- No broad search.\n\n'
                '## Validation commands\n- python3 -m pytest -q\n\n'
                '## First progress deadline\n- 2 minutes.\n',
                encoding='utf-8',
            )
            hermes_stub = bin_dir / 'hermes'
            hermes_stub.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
            hermes_stub.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = f"{bin_dir}:{env['PATH']}"
            result = subprocess.run(
                [str(IMPL), '--supervised', '--foreground-supervised', str(handoff), str(state)],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 4)
            self.assertIn('## Service seams', result.stderr)
            self.assertIn('## Return shape', result.stderr)
            self.assertIn('## Render insertion point', result.stderr)
            self.assertIn('## Test assertions', result.stderr)
            self.assertIn('## Forbidden data exposure', result.stderr)

    def test_delivery_profiles_reject_invalid_control_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            handoff = tmp_path / 'handoff.md'
            state = tmp_path / 'state.json'
            handoff.write_text('handoff\n', encoding='utf-8')
            state.write_text('{}\n', encoding='utf-8')

            fast_qc = subprocess.run(
                [str(QC), '--delivery-profile', 'fast', str(handoff), str(state)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(fast_qc.returncode, 2)
            self.assertIn('fast profile has no dev-qc handoff', fast_qc.stderr)

            guarded_impl = subprocess.run(
                [str(IMPL), '--delivery-profile', 'guarded', str(handoff), str(state)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(guarded_impl.returncode, 4)
            self.assertIn('implementation-context artifact required', guarded_impl.stderr)

            fast_supervised_impl = subprocess.run(
                [str(IMPL), '--delivery-profile', 'fast', '--supervised', str(handoff), str(state)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(fast_supervised_impl.returncode, 2)
            self.assertIn('fast profile forbids --supervised', fast_supervised_impl.stderr)

    def test_fast_impl_uses_root_state_without_handoff_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = tmp_path / 'state.json'
            state.write_text('{"delivery_profile":"fast"}\n', encoding='utf-8')
            bin_dir = tmp_path / 'bin'
            bin_dir.mkdir()
            hermes_stub = bin_dir / 'hermes'
            hermes_stub.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
            hermes_stub.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = f"{bin_dir}:{env['PATH']}"
            result = subprocess.run(
                [str(IMPL), str(state)], cwd=tmp_path, env=env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('impl_handoff_artifact: (fast profile: root delivery state is the manifest)', result.stdout)
            self.assertFalse((tmp_path / '.stagepilot').exists())

    def test_qc_supervised_launcher_uses_harness_helper_and_target_worktree(self) -> None:
        observed = self.run_launcher(QC, 'qc-handoff.md')
        self.assert_common(observed, label='qc', profile='dev-qc', handoff_name='qc-handoff.md', expect_preset=False)

    def test_qc_supervised_launcher_includes_controller_verdict_contract(self) -> None:
        observed = self.run_launcher(QC, 'qc-handoff.md', with_verdict_output=True)
        prompt = observed['argv'][-1]
        self.assertIn(observed['verdict_output'], prompt)
        self.assertIn('bounded same-scope rework loop', prompt)
        self.assertIn('missing or', prompt)


if __name__ == '__main__':
    unittest.main()
