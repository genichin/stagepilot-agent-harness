#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'supervise_worker.py'


class SuperviseWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(['git', 'init'], cwd=self.repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo, check=True)
        (self.repo / 'tracked.txt').write_text('base\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'tracked.txt'], cwd=self.repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=self.repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        (self.repo / '.stagepilot' / 'worker-progress').mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_supervisor(self, name: str, command: str, *, checkpoint: float = 0.02, max_minutes: float = 0.08) -> tuple[subprocess.CompletedProcess[str], dict]:
        progress = self.repo / '.stagepilot' / 'worker-progress' / f'{name}.md'
        proc = subprocess.run(
            [
                'python3', str(SCRIPT),
                '--label', name,
                '--workdir', str(self.repo),
                '--progress-artifact', str(progress),
                '--checkpoint-minutes', str(checkpoint),
                '--max-minutes', str(max_minutes),
                '--', 'bash', '-lc', command,
            ],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        result_file = None
        for line in proc.stdout.splitlines():
            if line.startswith('final_result_file: '):
                result_file = Path(line.split(': ', 1)[1].strip())
                break
        self.assertIsNotNone(result_file, msg=proc.stdout + '\nSTDERR:\n' + proc.stderr)
        assert result_file is not None
        payload = json.loads(result_file.read_text(encoding='utf-8'))
        return proc, payload

    def test_worker_success_before_checkpoint(self) -> None:
        proc, payload = self.run_supervisor('fast-success', 'sleep 0.5; printf "ok\\n"')
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(payload['result_class'], 'done')
        self.assertEqual(payload['checkpoints_taken'], 0)

    def test_no_progress_timeout(self) -> None:
        proc, payload = self.run_supervisor('no-progress', 'sleep 3')
        self.assertEqual(proc.returncode, 124)
        self.assertEqual(payload['result_class'], 'timeout_no_progress')
        self.assertGreaterEqual(payload['checkpoints_taken'], 1)

    def test_progress_artifact_extension(self) -> None:
        progress_path = self.repo / '.stagepilot' / 'worker-progress' / 'artifact-progress.md'
        command = textwrap.dedent(f'''\
            sleep 0.5
            cat > {progress_path} <<'EOF'
            - current step: implementing
            - files inspected: tracked.txt
            - files modified: none yet
            - design/implementation decisions made: use artifact checkpoint
            - commands/checks run: none
            - current blocker, if any: none
            - next concrete step: finish work
            EOF
            sleep 1.6
            printf "done\\n"
        ''')
        proc, payload = self.run_supervisor('artifact-progress', command)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(payload['result_class'], 'done')
        self.assertGreaterEqual(payload['extensions_granted'], 1)

    def test_diff_based_extension(self) -> None:
        command = textwrap.dedent('''\
            sleep 0.5
            printf "changed\\n" >> tracked.txt
            sleep 1.6
            printf "done\\n"
        ''')
        proc, payload = self.run_supervisor('diff-progress', command)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(payload['result_class'], 'done')
        self.assertGreaterEqual(payload['extensions_granted'], 1)

    def test_max_runtime_stop(self) -> None:
        progress_path = self.repo / '.stagepilot' / 'worker-progress' / 'max-runtime.md'
        command = textwrap.dedent(f'''\
            i=0
            while true; do
              i=$((i+1))
              cat > {progress_path} <<EOF
            - current step: loop $i
            - files inspected: tracked.txt
            - files modified: none
            - design/implementation decisions made: keep running
            - commands/checks run: none
            - current blocker, if any: none
            - next concrete step: continue
            EOF
              sleep 0.8
            done
        ''')
        proc, payload = self.run_supervisor('max-runtime', command, checkpoint=0.02, max_minutes=0.05)
        self.assertEqual(proc.returncode, 126)
        self.assertEqual(payload['result_class'], 'max_runtime_exceeded')
        self.assertGreaterEqual(payload['extensions_granted'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
