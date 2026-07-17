#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'lead-launch-runner.sh'


class LeadLauncherCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tempdir.name)
        self.bin_dir = self.tmp / 'bin'
        self.bin_dir.mkdir()
        for command in ('bash', 'python3', 'mkdir', 'mktemp', 'basename', 'tr', 'date', 'chmod', 'cat'):
            source = shutil.which(command)
            if source is None:
                self.fail(f'required test command not found: {command}')
            (self.bin_dir / command).symlink_to(source)
        hermes = self.bin_dir / 'hermes'
        hermes.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
        hermes.chmod(0o755)
        self.kickoff = self.tmp / 'kickoff.md'
        self.kickoff.write_text('# kickoff\n', encoding='utf-8')

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_launcher(
        self, profile: str, *options: str, doctor_mode: str | None = None
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        state = self.tmp / f'{profile}.json'
        payload = {'delivery_profile': profile, 'status': 'ready'}
        if doctor_mode is not None:
            payload['doctor_adoption_mode'] = doctor_mode
        state.write_text(json.dumps(payload), encoding='utf-8')
        env = os.environ.copy()
        # No tmux is made visible. All commands used before --dry-run remain
        # available so the capability behavior is isolated.
        env['PATH'] = str(self.bin_dir)
        result = subprocess.run(
            [str(SCRIPT), '--skip-worktree', '--dry-run', *options, self.kickoff, state],
            cwd=self.tmp,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return result, json.loads(state.read_text(encoding='utf-8'))

    def test_fast_explicit_degraded_mode_uses_foreground_and_persists_choice(self) -> None:
        result, state = self.run_launcher('fast', '--allow-fast-degraded')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('launch_mode: foreground', result.stdout)
        self.assertEqual(state['capability_status'], 'degraded')
        self.assertEqual(state['fallback_selected'], 'foreground_runner_without_tmux')
        self.assertEqual(state['degraded_capabilities'], ['tmux'])

    def test_standard_missing_tmux_becomes_structured_blocker(self) -> None:
        result, state = self.run_launcher('standard')
        self.assertEqual(result.returncode, 1)
        self.assertIn('required command not found: tmux', result.stderr)
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['state'], 'blocked')
        self.assertEqual(state['reason_class'], 'tooling_or_access_blocker')
        self.assertEqual(state['blocker_code'], 'launcher_prerequisite_missing')
        self.assertEqual(state['blocker_detail'], 'tmux_unavailable')

    def test_required_doctor_becomes_structured_blocker_before_tty_check(self) -> None:
        result, state = self.run_launcher('guarded', doctor_mode='required')
        self.assertEqual(result.returncode, 1)
        self.assertIn('required doctor command not found', result.stderr)
        self.assertEqual(state['blocker_detail'], 'doctor_unavailable')
        self.assertEqual(state['blocker_code'], 'stagepilot_doctor_required_missing')

    def test_optional_doctor_records_degraded_fallback(self) -> None:
        result, state = self.run_launcher(
            'fast', '--allow-fast-degraded', doctor_mode='optional'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('stagepilot_doctor', state['degraded_capabilities'])
        self.assertIn('runner_validation_without_doctor', state['fallbacks_selected'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
