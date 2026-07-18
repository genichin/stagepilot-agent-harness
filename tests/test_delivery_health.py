from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'scripts' / 'record_delivery_transition.py'
VERIFY = ROOT / 'scripts' / 'verify_delivery_trace.py'
REPORT = ROOT / 'scripts' / 'report_harness_observation.py'
CATALOG = ROOT / 'governance' / 'skill-catalog.json'
NOW = '2026-07-18T00:00:00Z'


class DeliveryHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(); self.evidence = Path(self.tmp.name) / 'evidence'; self.evidence.mkdir()

    def tearDown(self) -> None: self.tmp.cleanup()

    def command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['python3', *args], text=True, capture_output=True)

    def fixture(self, profile: str, state_extra: dict | None = None) -> None:
        state = {'status': 'done', 'updated_at': NOW, 'delivery_profile': profile, 'catalog_sha256': hashlib.sha256(CATALOG.read_bytes()).hexdigest()}; state.update(state_extra or {})
        self.evidence.joinpath('state.json').write_text(json.dumps(state), encoding='utf-8')
        result = self.evidence / 'result.json'; result.write_text('{}', encoding='utf-8')
        release = self.evidence / 'release-evidence.json'; release.write_text(json.dumps({'source_revision': 'fixture', 'catalog_version': '1.0.0', 'catalog_sha256': hashlib.sha256(CATALOG.read_bytes()).hexdigest(), 'export_manifest_sha256': 'fixture', 'verifier_version': 'fixture', 'recorded_at': NOW}), encoding='utf-8')
        self.evidence.joinpath('archive-manifest.json').write_text(json.dumps({'files': [{'path': 'result.json', 'sha256': hashlib.sha256(result.read_bytes()).hexdigest()}, {'path': 'release-evidence.json', 'sha256': hashlib.sha256(release.read_bytes()).hexdigest()}]}), encoding='utf-8')

    def record(self, stage: str) -> None:
        result = self.command(str(RECORD), '--evidence-dir', str(self.evidence), '--stage', stage, '--actor', 'runner', '--artifact', f'{stage}.md', '--timestamp', NOW)
        self.assertEqual(result.returncode, 0, result.stderr)

    def verify(self) -> subprocess.CompletedProcess[str]:
        return self.command(str(VERIFY), '--evidence-dir', str(self.evidence), '--catalog', str(CATALOG), '--now', NOW)

    def test_guarded_trace_records_and_verifies(self) -> None:
        self.fixture('guarded')
        for stage in ('kickoff', 'impl-running', 'qc-review', 'merge-ready'): self.record(stage)
        result = self.verify(); self.assertEqual(result.returncode, 0, result.stderr); self.assertTrue(json.loads(result.stdout)['valid'])

    def test_guarded_qc_skip_is_reportable_as_a_redacted_draft(self) -> None:
        self.fixture('guarded')
        for stage in ('kickoff', 'impl-running', 'merge-ready'): self.record(stage)
        result = self.verify(); self.assertEqual(result.returncode, 1)
        verification = self.evidence / 'verification.json'; verification.write_text(result.stdout, encoding='utf-8')
        draft = self.evidence / 'harness-observation.md'
        report = self.command(str(REPORT), '--verification-result', str(verification), '--delivery-id', 'fixture-123', '--harness-revision', 'fixture', '--output', str(draft))
        self.assertEqual(report.returncode, 0, report.stderr); self.assertIn('invalid-stage-order', draft.read_text(encoding='utf-8')); self.assertNotIn(str(self.evidence), draft.read_text(encoding='utf-8'))

    def test_fast_requires_waiver_validation_and_risk(self) -> None:
        self.fixture('fast')
        for stage in ('kickoff', 'impl-running', 'targeted-validation', 'merge-ready'): self.record(stage)
        result = self.verify(); codes = {item['class'] for item in json.loads(result.stdout)['findings']}
        self.assertEqual(result.returncode, 1); self.assertTrue({'fast-qc-waiver-missing', 'fast-validation-missing', 'fast-residual-risk-missing'} <= codes)

    def test_report_rejects_sensitive_identifier_input(self) -> None:
        failed = self.evidence / 'failed.json'; failed.write_text(json.dumps({'valid': False, 'findings': [{'class': 'fixture-failure'}]}), encoding='utf-8')
        result = self.command(str(REPORT), '--verification-result', str(failed), '--delivery-id', '/tmp/project-secret', '--harness-revision', 'fixture', '--output', str(self.evidence / 'draft.md'))
        self.assertEqual(result.returncode, 1); self.assertIn('safe identifiers', result.stdout)

    def test_publish_needs_explicit_repo(self) -> None:
        failed = self.evidence / 'failed.json'; failed.write_text(json.dumps({'valid': False, 'findings': [{'class': 'fixture-failure'}]}), encoding='utf-8')
        result = self.command(str(REPORT), '--verification-result', str(failed), '--delivery-id', 'fixture', '--harness-revision', 'fixture', '--output', str(self.evidence / 'draft.md'), '--publish')
        self.assertEqual(result.returncode, 1); self.assertIn('--repo is required', result.stdout)


if __name__ == '__main__': unittest.main()
