#!/usr/bin/env python3
from __future__ import annotations

import json
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
        (self.repo / '.stagepilot' / 'worker-progress' / '.gitkeep').write_text('', encoding='utf-8')
        subprocess.run(['git', 'add', '.stagepilot/worker-progress/.gitkeep'], cwd=self.repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'track progress dir'], cwd=self.repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_supervisor(self, name: str, command: str, *, checkpoint: float = 0.02, max_minutes: float = 0.08, extra_args: list[str] | None = None) -> tuple[subprocess.CompletedProcess[str], dict]:
        progress = self.repo / '.stagepilot' / 'worker-progress' / f'{name}.md'
        proc = subprocess.run(
            [
                'python3', str(SCRIPT),
                '--label', name,
                '--workdir', str(self.repo),
                '--progress-artifact', str(progress),
                '--checkpoint-minutes', str(checkpoint),
                '--max-minutes', str(max_minutes),
                *(extra_args or []),
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
        (self.repo / '.stagepilot' / 'worker-progress' / 'no-progress.md').write_text('placeholder\n', encoding='utf-8')
        proc, payload = self.run_supervisor('no-progress', 'sleep 3')
        self.assertEqual(proc.returncode, 124)
        self.assertEqual(payload['result_class'], 'timeout_no_progress')
        self.assertIsNone(payload['stall_subtype'])
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

    def test_read_loop_no_diff_is_classified(self) -> None:
        command = textwrap.dedent('''\
            for i in 1 2 3 4; do
              printf "📖 read tracked.txt\\n"
              printf "🔎 search tracked\\n"
              sleep 0.5
            done
            sleep 2
        ''')
        proc, payload = self.run_supervisor('read-loop', command)
        self.assertEqual(proc.returncode, 124)
        self.assertEqual(payload['result_class'], 'timeout_no_progress_read_loop')
        self.assertEqual(payload['stall_subtype'], 'read_loop_no_diff')
        self.assertIn('read_markers=', ' '.join(payload['stall_classification_reasons']))

    def test_context_compaction_loop_is_classified(self) -> None:
        command = textwrap.dedent('''\
            for i in 1 2 3; do
              printf "context compaction triggered\\n"
              printf "compacting conversation due to context budget\\n"
              sleep 0.5
            done
            sleep 2
        ''')
        proc, payload = self.run_supervisor('compaction-loop', command)
        self.assertEqual(proc.returncode, 128)
        self.assertEqual(payload['result_class'], 'early_context_compaction_loop')
        self.assertEqual(payload['stall_subtype'], 'context_compaction_loop')
        self.assertIn('context_compaction_markers=', ' '.join(payload['stall_classification_reasons']))

    def test_missing_progress_artifact_is_classified(self) -> None:
        proc, payload = self.run_supervisor('missing-artifact', 'sleep 3')
        self.assertEqual(proc.returncode, 124)
        self.assertEqual(payload['result_class'], 'timeout_no_progress_progress_artifact_missing')
        self.assertEqual(payload['stall_subtype'], 'progress_artifact_missing')
        self.assertIn('progress_artifact_missing', payload['stall_classification_reasons'])

    def test_first_progress_deadline_stops_before_checkpoint(self) -> None:
        proc, payload = self.run_supervisor(
            'first-progress',
            'sleep 3',
            checkpoint=0.08,
            max_minutes=0.2,
            extra_args=['--first-progress-minutes', '0.01'],
        )
        self.assertEqual(proc.returncode, 127)
        self.assertEqual(payload['result_class'], 'first_progress_deadline_exceeded')
        self.assertEqual(payload['stall_subtype'], 'progress_artifact_missing')
        self.assertEqual(payload['checkpoints_taken'], 0)

    def test_early_read_loop_stops_before_checkpoint(self) -> None:
        command = textwrap.dedent('''\
            for i in 1 2 3 4 5 6; do
              printf "📖 read tracked.txt\\n"
              printf "🔎 grep tracked\\n"
              sleep 0.2
            done
            sleep 3
        ''')
        proc, payload = self.run_supervisor(
            'early-read-loop',
            command,
            checkpoint=0.08,
            max_minutes=0.2,
            extra_args=['--early-read-search-threshold', '6'],
        )
        self.assertEqual(proc.returncode, 129)
        self.assertEqual(payload['result_class'], 'early_read_loop_no_diff')
        self.assertEqual(payload['stall_subtype'], 'read_loop_no_diff')
        self.assertEqual(payload['checkpoints_taken'], 0)

    def test_sigterm_writes_interrupted_final_result(self) -> None:
        progress = self.repo / '.stagepilot' / 'worker-progress' / 'interrupted.md'
        proc = subprocess.Popen(
            [
                'python3', str(SCRIPT),
                '--label', 'interrupted',
                '--workdir', str(self.repo),
                '--progress-artifact', str(progress),
                '--checkpoint-minutes', '0.1',
                '--max-minutes', '2',
                '--', 'bash', '-lc', 'sleep 30',
            ],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        import signal, time
        time.sleep(0.8)
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 130, msg=stdout + '\nSTDERR:\n' + stderr)
        result_file = None
        for line in stdout.splitlines():
            if line.startswith('final_result_file: '):
                result_file = Path(line.split(': ', 1)[1].strip())
                break
        self.assertIsNotNone(result_file, msg=stdout + '\nSTDERR:\n' + stderr)
        assert result_file is not None
        payload = json.loads(result_file.read_text(encoding='utf-8'))
        self.assertEqual(payload['result_class'], 'supervisor_interrupted')
        self.assertIn('SIGTERM', payload['result_reason'])
        self.assertIsNotNone(payload['child_pid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
