#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHER = ROOT / 'scripts' / 'watch_runner_terminal.py'


class RunnerTerminalWatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tempdir.name)
        self.bin_dir = self.tmp / 'bin'
        self.bin_dir.mkdir()
        tmux = self.bin_dir / 'tmux'
        tmux.write_text('#!/usr/bin/env bash\nexit 1\n', encoding='utf-8')
        tmux.chmod(0o755)
        self.state = self.tmp / 'state.json'
        self.exit_file = self.tmp / 'runner.exit'
        self.status_file = self.tmp / 'runner.status'
        self.log_file = self.tmp / 'runner.log'
        self.event_file = self.tmp / 'events.jsonl'
        self.cursor_file = self.tmp / 'cursor.json'
        self.manifest = self.tmp / 'watcher.json'
        self.log_file.write_text('runner output\n', encoding='utf-8')

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_manifest(self, *, targets: list[dict] | None = None) -> None:
        self.manifest.write_text(json.dumps({
            'schema_version': 2,
            'launch_id': 'runner-test-01',
            'path_root': str(self.tmp),
            'delivery_state': self.state.name,
            'tmux_session': 'runner-test-01',
            'exit_file': self.exit_file.name,
            'status_file': self.status_file.name,
            'log_file': self.log_file.name,
            'event_file': self.event_file.name,
            'dispatch_cursor_file': self.cursor_file.name,
            'missing_artifact_deadline_epoch': 0,
            'notification_targets': targets or [],
        }), encoding='utf-8')

    def write_state(self, state: str = 'done') -> None:
        self.state.write_text(json.dumps({
            'status': state,
            'state': state,
            'current_stage': 'closed' if state == 'done' else 'kickoff',
            'owner_target': 'lead' if state == 'done' else 'delivery-runner',
        }), encoding='utf-8')

    def write_artifacts(self, *, exit_code: int = 0, summary: str = 'done:stage=closed') -> None:
        self.exit_file.write_text(f'{exit_code}\n', encoding='utf-8')
        self.status_file.write_text(f'exit_code={exit_code}\nstate_summary={summary}\n', encoding='utf-8')

    def run_watcher(self, *, ready_file: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env['PATH'] = f'{self.bin_dir}:{env["PATH"]}'
        command = [sys.executable, str(WATCHER), '--manifest', str(self.manifest), '--once']
        if ready_file:
            command.extend(['--ready-file', str(ready_file)])
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def events(self) -> list[dict]:
        return [json.loads(line) for line in self.event_file.read_text(encoding='utf-8').splitlines() if line]

    def test_done_dispatches_structured_payload_once(self) -> None:
        capture = self.tmp / 'notification.json'
        receiver = self.tmp / 'receiver.py'
        receiver.write_text(
            'import pathlib, sys\n'
            'pathlib.Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")\n',
            encoding='utf-8',
        )
        self.write_state('done')
        self.write_artifacts()
        self.write_manifest(targets=[{
            'id': 'lead-session',
            'kind': 'lead-session',
            'events': ['done'],
            'argv': [sys.executable, str(receiver), str(capture)],
        }])

        first = self.run_watcher()
        self.assertEqual(first.returncode, 0, first.stderr)
        payload = json.loads(capture.read_text(encoding='utf-8'))
        self.assertEqual(payload['event'], 'done')
        self.assertEqual(payload['delivery_state'], str(self.state))
        self.assertEqual(payload['exit_code'], '0')
        event = self.events()[0]
        self.assertEqual(event['notifications'][0]['status'], 'sent')
        self.assertEqual(event['sequence'], 1)
        self.assertEqual(len(self.events()), 1)

        second = self.run_watcher()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(len(self.events()), 1)
        self.assertFalse(json.loads(second.stdout)['dispatched'])

    def test_manifest_rejects_absolute_artifact_paths(self) -> None:
        self.write_state('done')
        self.write_artifacts()
        self.write_manifest()
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        manifest['delivery_state'] = str(self.state)
        self.manifest.write_text(json.dumps(manifest), encoding='utf-8')

        result = self.run_watcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be a safe relative path', result.stderr)

    def test_ready_file_is_created_after_manifest_validation(self) -> None:
        ready_file = self.tmp / 'watcher-ready.json'
        self.write_state('done')
        self.write_artifacts()
        self.write_manifest()

        result = self.run_watcher(ready_file=ready_file)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsInstance(json.loads(ready_file.read_text(encoding='utf-8'))['pid'], int)

    def test_missing_terminal_artifacts_becomes_integrity_failure_and_notifies(self) -> None:
        capture = self.tmp / 'integrity.json'
        receiver = self.tmp / 'receiver.py'
        receiver.write_text(
            'import pathlib, sys\n'
            'pathlib.Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")\n',
            encoding='utf-8',
        )
        self.write_state('running')
        self.write_manifest(targets=[{
            'id': 'ops-webhook',
            'kind': 'command',
            'events': ['supervisor_integrity_failure'],
            'argv': [sys.executable, str(receiver), str(capture)],
        }])

        result = self.run_watcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text(encoding='utf-8'))
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['blocker_code'], 'supervisor_integrity_failure')
        self.assertEqual(state['blocker_detail'], 'root_runner_exit_or_status_artifact_missing')
        payload = json.loads(capture.read_text(encoding='utf-8'))
        self.assertEqual(payload['event'], 'supervisor_integrity_failure')
        self.assertEqual(self.events()[0]['notifications'][0]['status'], 'sent')

    def test_mismatched_exit_and_status_artifacts_becomes_integrity_failure(self) -> None:
        self.write_state('done')
        self.write_artifacts(exit_code=0, summary='done:stage=closed')
        self.status_file.write_text('exit_code=7\nstate_summary=blocked:lead-escalation\n', encoding='utf-8')
        self.write_manifest()

        result = self.run_watcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text(encoding='utf-8'))
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['blocker_code'], 'supervisor_integrity_failure')
        self.assertEqual(self.events()[-1]['event'], 'supervisor_integrity_failure')

    def test_preclaimed_event_is_not_dispatched_again_after_restart(self) -> None:
        capture = self.tmp / 'notification.json'
        receiver = self.tmp / 'receiver.py'
        receiver.write_text('import pathlib, sys\npathlib.Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")\n', encoding='utf-8')
        self.write_state('done')
        self.write_artifacts()
        self.write_manifest(targets=[{
            'id': 'lead-session', 'kind': 'lead-session', 'events': ['done'],
            'argv': [sys.executable, str(receiver), str(capture)],
        }])
        event_id = hashlib.sha256(json.dumps({'launch_id': 'runner-test-01', 'event': 'done'}, sort_keys=True).encode('utf-8')).hexdigest()
        self.cursor_file.write_text(json.dumps({'schema_version': 1, 'claimed_event_ids': [event_id]}), encoding='utf-8')

        result = self.run_watcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(capture.exists())
        self.assertFalse(json.loads(result.stdout)['dispatched'])

    def test_blocked_terminal_state_emits_blocked_event(self) -> None:
        self.write_state('blocked')
        self.write_artifacts(exit_code=1, summary='blocked:lead-escalation')
        self.write_manifest()

        result = self.run_watcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        event = self.events()[0]
        self.assertEqual(event['event'], 'blocked')
        self.assertEqual(event['root_state'], 'blocked')
        self.assertEqual(event['exit_code'], '1')

    def test_notification_failure_is_durable_but_preserves_done_state(self) -> None:
        failing_receiver = self.tmp / 'failing-receiver.py'
        failing_receiver.write_text('raise SystemExit(9)\n', encoding='utf-8')
        self.write_state('done')
        self.write_artifacts()
        self.write_manifest(targets=[{
            'id': 'unavailable-lead-session',
            'kind': 'lead-session',
            'events': ['done'],
            'argv': [sys.executable, str(failing_receiver)],
        }])

        result = self.run_watcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text(encoding='utf-8'))['status'], 'done')
        notification = self.events()[0]['notifications'][0]
        self.assertEqual(notification['status'], 'delivery_failed')
        self.assertEqual(notification['returncode'], 9)

    def test_nonterminal_root_state_after_runner_exit_becomes_incomplete_then_blocked(self) -> None:
        self.write_state('running')
        self.write_artifacts(exit_code=3, summary='incomplete:running:stage=kickoff')
        self.write_manifest()

        result = self.run_watcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text(encoding='utf-8'))
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['blocker_code'], 'runner_incomplete')
        self.assertEqual(self.events()[0]['event'], 'incomplete')
        self.assertEqual(self.events()[0]['notifications'], [{'status': 'not_configured'}])


if __name__ == '__main__':
    unittest.main()
