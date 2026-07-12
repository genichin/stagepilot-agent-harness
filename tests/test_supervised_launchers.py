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
    def run_launcher(self, launcher: Path, handoff_name: str, extra_args: list[str] | None = None) -> dict:
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

            launch_args = [str(launcher), '--supervised', *(extra_args or []), str(handoff), str(state)]
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
        if profile == 'dev-impl':
            self.assertIn('first_progress_minutes: 2', observed['stdout'])
            self.assertIn('readiness_gate: 1', observed['stdout'])
            self.assertIn('implementation_context:', observed['stdout'])
        if profile == 'dev-qc':
            self.assertIn('first_progress_minutes: 5', observed['stdout'])
        self.assertIn(f'progress_artifact: {progress_path}', observed['stdout'])
        self.assertNotIn(f'{project}/scripts/supervise_worker.py', observed['stdout'])

    def test_impl_supervised_launcher_uses_harness_helper_and_target_worktree(self) -> None:
        observed = self.run_launcher(IMPL, 'impl-handoff.md', extra_args=['--preset', 'default'])
        self.assert_common(observed, label='impl', profile='dev-impl', handoff_name='impl-handoff.md', expect_preset=True)


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
                [str(IMPL), str(handoff), str(state)],
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
                [str(IMPL), '--supervised', str(handoff), str(state)],
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

    def test_qc_supervised_launcher_uses_harness_helper_and_target_worktree(self) -> None:
        observed = self.run_launcher(QC, 'qc-handoff.md')
        self.assert_common(observed, label='qc', profile='dev-qc', handoff_name='qc-handoff.md', expect_preset=False)


if __name__ == '__main__':
    unittest.main()
