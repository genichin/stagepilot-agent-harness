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
SCRIPT = ROOT / 'scripts' / 'check-delivery-capabilities.sh'


class DeliveryCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tempdir.name)
        self.repo = self.tmp / 'repo'
        self.bin_dir = self.tmp / 'bin'
        self.repo.mkdir()
        self.bin_dir.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True)
        self._link('python3')
        self._link('bash')
        self._link('git')
        self._stub('hermes', '#!/usr/bin/env bash\nexit 0\n')

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _link(self, name: str) -> None:
        source = shutil.which(name)
        if source is None:
            self.fail(f'required test command not found: {name}')
        (self.bin_dir / name).symlink_to(source)

    def _stub(self, name: str, content: str) -> None:
        path = self.bin_dir / name
        path.write_text(content, encoding='utf-8')
        path.chmod(0o755)

    def run_check(self, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        env = os.environ.copy()
        # This controlled PATH makes missing capability cases deterministic while
        # keeping only bash/core tools available from /bin.
        env['PATH'] = f'{self.bin_dir}:/bin'
        env['STAGEPILOT_CAPABILITY_PATH'] = str(self.bin_dir)
        result = subprocess.run(
            [str(SCRIPT), '--json', *args],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertTrue(result.stdout, msg=result.stderr)
        return result, json.loads(result.stdout)

    def test_fast_reports_degraded_when_detached_tty_is_missing_but_fallback_is_approved(self) -> None:
        result, payload = self.run_check(
            '--delivery-profile', 'fast', '--allow-fast-degraded',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload['status'], 'degraded')
        self.assertEqual(payload['required_missing'], [])
        self.assertIn('tmux', payload['optional_missing'])
        self.assertIn('foreground_runner_without_tmux', payload['available_fallbacks'])

    def test_guarded_blocks_when_detached_tty_is_missing(self) -> None:
        result, payload = self.run_check('--delivery-profile', 'guarded')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(payload['status'], 'blocked')
        self.assertIn('tmux', payload['required_missing'])

    def test_required_doctor_blocks_and_optional_doctor_degrades(self) -> None:
        blocked, blocked_payload = self.run_check(
            '--delivery-profile', 'fast', '--allow-fast-degraded',
            '--doctor-mode', 'required',
        )
        self.assertEqual(blocked.returncode, 1, blocked.stderr)
        self.assertEqual(blocked_payload['status'], 'blocked')
        self.assertIn('stagepilot_doctor', blocked_payload['required_missing'])

        degraded, degraded_payload = self.run_check(
            '--delivery-profile', 'fast', '--allow-fast-degraded',
            '--doctor-mode', 'optional',
        )
        self.assertEqual(degraded.returncode, 0, degraded.stderr)
        self.assertEqual(degraded_payload['status'], 'degraded')
        self.assertIn('stagepilot_doctor', degraded_payload['optional_missing'])
        self.assertIn('runner_validation_without_doctor', degraded_payload['available_fallbacks'])

    def test_delivery_state_is_authoritative_doctor_mode_source_when_not_overridden(self) -> None:
        state = self.repo / 'delivery-state.json'
        state.write_text(json.dumps({'doctor_adoption_mode': 'required'}), encoding='utf-8')
        result, payload = self.run_check(
            '--delivery-profile', 'fast', '--allow-fast-degraded',
            '--delivery-state', str(state),
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(payload['doctor_mode'], 'required')
        self.assertEqual(payload['doctor_mode_source'], 'delivery_state')
        self.assertIn('stagepilot_doctor', payload['required_missing'])

    def test_missing_python_fails_before_contract_emission_with_actionable_error(self) -> None:
        (self.bin_dir / 'python3').unlink()
        env = os.environ.copy()
        env['PATH'] = str(self.bin_dir)
        result = subprocess.run(
            [str(SCRIPT), '--json'],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn('python3 is required to emit the capability JSON contract', result.stderr)

    def test_publication_is_checked_only_when_requested(self) -> None:
        default, default_payload = self.run_check(
            '--delivery-profile', 'fast', '--allow-fast-degraded',
        )
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertNotIn('gh', default_payload['required_missing'])

        required, required_payload = self.run_check(
            '--delivery-profile', 'guarded', '--publication-mode', 'required',
        )
        self.assertEqual(required.returncode, 1, required.stderr)
        self.assertIn('gh', required_payload['required_missing'])
        self.assertIn('publication_origin', required_payload['required_missing'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
