from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'bootstrap_profiles.py'


class BootstrapProfilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fixture = self.base / 'fixture.json'
        self.plan = self.base / 'plan.json'
        self.target = self.base / 'fixture-home'
        self.fixture.write_text(json.dumps({'schema_version': 1, 'profiles': [
            {'role': 'lead', 'name': 'fixture-dev-lead', 'soul': 'profiles/templates/lead.SOUL.md', 'model': 'test', 'cwd': '/fixture', 'toolsets': ['file']},
            {'role': 'qc', 'name': 'fixture-dev-qc', 'soul': 'profiles/templates/dev-qc.SOUL.md', 'model': 'test', 'cwd': '/fixture', 'toolsets': ['file']},
        ]}), encoding='utf-8')

    def tearDown(self) -> None: self.temp.cleanup()

    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['python3', str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False)

    def apply_cmd(self, plan: Path) -> subprocess.CompletedProcess[str]:
        return self.run_cmd('apply', '--plan', str(plan), '--target-home', str(self.target), '--target-profile', 'fixture-dev-lead', '--target-profile', 'fixture-dev-qc')

    def test_plan_apply_verify_report_are_idempotent(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        first = self.apply_cmd(self.plan)
        self.assertEqual(first.returncode, 0, first.stderr)
        snapshot = sorted((p.relative_to(self.target), p.read_bytes()) for p in self.target.rglob('*') if p.is_file())
        self.assertEqual(self.apply_cmd(self.plan).returncode, 0)
        self.assertEqual(snapshot, sorted((p.relative_to(self.target), p.read_bytes()) for p in self.target.rglob('*') if p.is_file()))
        verified = self.run_cmd('verify', '--plan', str(self.plan), '--target-home', str(self.target))
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertTrue(json.loads(verified.stdout)['valid'])

    def test_verify_detects_soul_drift(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        self.assertEqual(self.apply_cmd(self.plan).returncode, 0)
        (self.target / 'profiles/fixture-dev-lead/SOUL.md').write_text('drift', encoding='utf-8')
        result = self.run_cmd('verify', '--plan', str(self.plan), '--target-home', str(self.target))
        self.assertEqual(result.returncode, 1)
        self.assertIn('SOUL drift', result.stdout)

    def test_verify_detects_source_soul_drift(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        self.assertEqual(self.apply_cmd(self.plan).returncode, 0)
        source = ROOT / 'profiles/templates/lead.SOUL.md'; original = source.read_bytes()
        try:
            source.write_bytes(original + b'\nsource drift\n')
            result = self.run_cmd('verify', '--plan', str(self.plan), '--target-home', str(self.target))
            self.assertEqual(result.returncode, 1)
            self.assertIn('source SOUL drift', result.stdout)
        finally:
            source.write_bytes(original)

    def test_partial_apply_failure_preserves_prior_target(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        self.assertEqual(self.apply_cmd(self.plan).returncode, 0)
        prior = json.loads((self.target / '.stagepilot-bootstrap-state.json').read_text())['plan_id']
        invalid = json.loads(self.plan.read_text(encoding='utf-8')); invalid['profiles'][0]['model'] = 'changed'; invalid['profiles'][0]['soul_sha256'] = '0' * 64; invalid['plan_id'] = 'invalid-plan'
        broken = self.base / 'broken-plan.json'; broken.write_text(json.dumps(invalid), encoding='utf-8')
        result = self.run_cmd('apply', '--plan', str(broken), '--target-home', str(self.target))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads((self.target / '.stagepilot-bootstrap-state.json').read_text())['plan_id'], prior)

    def test_verify_is_read_only_and_detects_skill_drift(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        self.assertEqual(self.apply_cmd(self.plan).returncode, 0)
        before = sorted((p.relative_to(self.target), p.read_bytes()) for p in self.target.rglob('*') if p.is_file())
        result = self.run_cmd('verify', '--plan', str(self.plan), '--target-home', str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, sorted((p.relative_to(self.target), p.read_bytes()) for p in self.target.rglob('*') if p.is_file()))
        skill = next((self.target / 'skills').glob('*/SKILL.md'))
        skill.write_text('drift', encoding='utf-8')
        result = self.run_cmd('verify', '--plan', str(self.plan), '--target-home', str(self.target))
        self.assertEqual(result.returncode, 1)
        self.assertIn('skill catalog parity drift', result.stdout)

    def test_rollback_restores_prior_managed_tree(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        self.assertEqual(self.apply_cmd(self.plan).returncode, 0)
        prior_id = json.loads(self.plan.read_text(encoding='utf-8'))['plan_id']
        data = json.loads(self.fixture.read_text(encoding='utf-8')); data['profiles'][0]['model'] = 'changed'
        self.fixture.write_text(json.dumps(data), encoding='utf-8')
        changed_plan = self.base / 'changed-plan.json'
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(changed_plan)).returncode, 0)
        applied = self.apply_cmd(changed_plan)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        rollback = json.loads(applied.stdout)['rollback_path']
        restored = self.run_cmd('rollback', '--target-home', str(self.target), '--rollback-dir', rollback)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(json.loads((self.target / '.stagepilot-bootstrap-state.json').read_text())['plan_id'], prior_id)

    def test_rejects_profile_set_mismatch(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        result = self.run_cmd('apply', '--plan', str(self.plan), '--target-home', str(self.target), '--target-profile', 'fixture-dev-lead')
        self.assertEqual(result.returncode, 2)
        self.assertIn('exactly match', result.stderr)

    def test_rejects_active_hermes_home(self) -> None:
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        result = self.run_cmd('apply', '--plan', str(self.plan), '--target-home', str(Path.home() / '.hermes'), '--target-profile', 'fixture-dev-lead', '--target-profile', 'fixture-dev-qc')
        self.assertEqual(result.returncode, 2)
        self.assertIn('outside ~/.hermes', result.stderr)

    def test_rejects_unmanaged_target(self) -> None:
        self.target.mkdir(); (self.target / 'foreign').write_text('x', encoding='utf-8')
        self.assertEqual(self.run_cmd('plan', '--fixture', str(self.fixture), '--output', str(self.plan)).returncode, 0)
        result = self.apply_cmd(self.plan)
        self.assertEqual(result.returncode, 2)
        self.assertIn('empty or managed', result.stderr)


if __name__ == '__main__': unittest.main()
