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
        self.assertIn(f'progress_artifact: {progress_path}', observed['stdout'])
        self.assertNotIn(f'{project}/scripts/supervise_worker.py', observed['stdout'])

    def test_impl_supervised_launcher_uses_harness_helper_and_target_worktree(self) -> None:
        observed = self.run_launcher(IMPL, 'impl-handoff.md', extra_args=['--preset', 'default'])
        self.assert_common(observed, label='impl', profile='dev-impl', handoff_name='impl-handoff.md', expect_preset=True)

    def test_qc_supervised_launcher_uses_harness_helper_and_target_worktree(self) -> None:
        observed = self.run_launcher(QC, 'qc-handoff.md')
        self.assert_common(observed, label='qc', profile='dev-qc', handoff_name='qc-handoff.md', expect_preset=False)


if __name__ == '__main__':
    unittest.main()
