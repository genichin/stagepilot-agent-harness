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
        for command in ('bash', 'python3', 'mkdir', 'mktemp', 'basename', 'dirname', 'tr', 'date', 'chmod', 'cat'):
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
        self,
        profile: str,
        *options: str,
        doctor_mode: str | None = None,
        skip_worktree: bool = True,
        env_updates: dict[str, str] | None = None,
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
        if env_updates:
            env.update(env_updates)
        args = [str(SCRIPT), '--dry-run']
        if skip_worktree:
            args.append('--skip-worktree')
        args.extend([*options, str(self.kickoff), str(state)])
        result = subprocess.run(
            args,
            cwd=self.tmp,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return result, json.loads(state.read_text(encoding='utf-8'))

    def test_fast_explicit_degraded_mode_uses_foreground_and_persists_choice(self) -> None:
        result, state = self.run_launcher(
            'fast', '--allow-fast-degraded', '--ack-fast-shared-workdir-risk'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('launch_mode: foreground', result.stdout)
        self.assertEqual(state['capability_status'], 'degraded')
        self.assertIn('foreground_runner_without_tmux', state['fallbacks_selected'])
        self.assertIn('current_workdir_without_worktree', state['fallbacks_selected'])
        self.assertIn('tmux', state['degraded_capabilities'])
        self.assertIn('worktree', state['degraded_capabilities'])
        self.assertTrue(state['fast_shared_workdir_risk_acknowledged'])
        self.assertIn('shares the lead checkout', state['residual_risk'])

    def test_standard_missing_tmux_becomes_structured_blocker(self) -> None:
        result, state = self.run_launcher('standard')
        self.assertEqual(result.returncode, 1)
        self.assertIn('required command not found: tmux', result.stderr)
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['state'], 'blocked')
        self.assertEqual(state['reason_class'], 'tooling_or_access_blocker')
        self.assertEqual(state['blocker_code'], 'tmux_unavailable')
        self.assertEqual(state['blocker_detail'], 'tmux_unavailable')
        self.assertEqual(state['launcher_status']['phase'], 'prelaunch')
        status = json.loads(Path(state['launcher_status_file']).read_text(encoding='utf-8'))
        self.assertEqual(status['classification'], state['blocker_code'])
        self.assertEqual(status['detail'], state['blocker_detail'])

    def test_missing_hermes_uses_specific_profile_blocker(self) -> None:
        (self.bin_dir / 'hermes').unlink()
        result, state = self.run_launcher('standard')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_detail'], 'hermes_not_found')
        self.assertEqual(state['blocker_code'], 'hermes_profile_unavailable')
        self.assertEqual(state['launcher_status']['classification'], 'hermes_profile_unavailable')

    def test_missing_python_explains_that_json_blocker_persistence_is_impossible(self) -> None:
        (self.bin_dir / 'python3').unlink()
        result, _ = self.run_launcher('fast', '--allow-fast-degraded')
        self.assertEqual(result.returncode, 1)
        self.assertIn('cannot persist a JSON delivery blocker state', result.stderr)

    def test_guarded_missing_git_is_a_specific_worktree_blocker(self) -> None:
        tmux = self.bin_dir / 'tmux'
        tmux.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
        tmux.chmod(0o755)
        result, state = self.run_launcher('guarded', skip_worktree=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_detail'], 'git_not_found')
        self.assertEqual(state['blocker_code'], 'git_worktree_prepare_failed')

    def test_guarded_rejects_worktree_bypass_even_when_tmux_is_available(self) -> None:
        tmux = self.bin_dir / 'tmux'
        tmux.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
        tmux.chmod(0o755)
        result, state = self.run_launcher('guarded')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_detail'], 'worktree_isolation_bypassed')
        self.assertEqual(state['blocker_code'], 'worktree_isolation_bypassed')

    def test_guarded_rejects_explicit_workdir_bypass_even_when_tmux_is_available(self) -> None:
        tmux = self.bin_dir / 'tmux'
        tmux.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
        tmux.chmod(0o755)
        workdir = self.tmp / 'manual-workdir'
        workdir.mkdir()
        result, state = self.run_launcher('guarded', '--workdir', str(workdir))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_code'], 'worktree_isolation_bypassed')

    def test_fast_explicit_workdir_requires_shared_checkout_acknowledgment(self) -> None:
        workdir = self.tmp / 'manual-workdir'
        workdir.mkdir()
        result, state = self.run_launcher('fast', '--allow-fast-degraded', '--workdir', str(workdir))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_code'], 'fast_shared_workdir_risk_unacknowledged')

    def test_standard_rejects_shared_workdir_bypass(self) -> None:
        tmux = self.bin_dir / 'tmux'
        tmux.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
        tmux.chmod(0o755)
        result, state = self.run_launcher('standard')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_code'], 'worktree_isolation_bypassed')

    def test_required_doctor_becomes_structured_blocker_before_tty_check(self) -> None:
        result, state = self.run_launcher('guarded', doctor_mode='required')
        self.assertEqual(result.returncode, 1)
        self.assertIn('required doctor command not found', result.stderr)
        self.assertEqual(state['blocker_detail'], 'doctor_unavailable')
        self.assertEqual(state['blocker_code'], 'stagepilot_doctor_required_missing')

    def test_fast_skip_worktree_rejects_dirty_checkout_even_with_acknowledgment(self) -> None:
        git = self.bin_dir / 'git'
        git.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "$*" == *"rev-parse --is-inside-work-tree"* ]]; then exit 0; fi\n'
            'if [[ "$*" == *"status --porcelain"* ]]; then printf " M tracked-file\\n"; exit 0; fi\n'
            'exit 1\n',
            encoding='utf-8',
        )
        git.chmod(0o755)
        result, state = self.run_launcher(
            'fast', '--allow-fast-degraded', '--ack-fast-shared-workdir-risk'
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_code'], 'fast_shared_workdir_not_clean')

    def test_optional_doctor_records_degraded_fallback(self) -> None:
        result, state = self.run_launcher(
            'fast', '--allow-fast-degraded', '--ack-fast-shared-workdir-risk', doctor_mode='optional'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('stagepilot_doctor', state['degraded_capabilities'])
        self.assertIn('runner_validation_without_doctor', state['fallbacks_selected'])
        self.assertIn(
            {'code': 'stagepilot_doctor_optional_missing', 'fallback_validation': 'runner_validation_without_doctor'},
            state['tooling_debts'],
        )

    def test_fast_skip_worktree_requires_explicit_shared_checkout_acknowledgment(self) -> None:
        result, state = self.run_launcher('fast', '--allow-fast-degraded')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['blocker_detail'], 'fast_shared_workdir_risk_unacknowledged')
        self.assertEqual(state['blocker_code'], 'fast_shared_workdir_risk_unacknowledged')


if __name__ == '__main__':
    unittest.main(verbosity=2)
