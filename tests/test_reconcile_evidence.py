from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'reconcile_evidence.py'
CATALOG = ROOT / 'governance' / 'skill-catalog.json'
NOW = '2026-07-18T00:00:00Z'


class ReconcileEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(); self.evidence = Path(self.tmp.name) / 'evidence'; self.evidence.mkdir()
        self.write_state('done', '2026-07-18T00:00:00Z')

    def tearDown(self) -> None: self.tmp.cleanup()

    def write_state(self, status: str, updated_at: str) -> None:
        self.evidence.joinpath('state.json').write_text(json.dumps({'status': status, 'updated_at': updated_at, 'catalog_sha256': hashlib.sha256(CATALOG.read_bytes()).hexdigest()}))

    def archive(self, contents: bytes = b'evidence') -> None:
        artifact = self.evidence / 'result.json'; artifact.write_bytes(contents)
        release = self.evidence / 'release-evidence.json'
        release.write_text(json.dumps({
            'source_revision': 'fixture', 'catalog_version': '1.0.0',
            'catalog_sha256': hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
            'export_manifest_sha256': 'fixture', 'verifier_version': 'fixture', 'recorded_at': NOW,
        }), encoding='utf-8')
        self.evidence.joinpath('archive-manifest.json').write_text(json.dumps({'files': [
            {'path': 'result.json', 'sha256': hashlib.sha256(contents).hexdigest()},
            {'path': 'release-evidence.json', 'sha256': hashlib.sha256(release.read_bytes()).hexdigest()},
        ]}))

    def reconcile_cmd(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['python3', str(SCRIPT), '--evidence-dir', str(self.evidence), '--catalog', str(CATALOG), '--now', NOW], text=True, capture_output=True)

    def test_valid_manifest_is_quiet_and_read_only(self) -> None:
        self.archive(); before = {p.name: p.read_bytes() for p in self.evidence.iterdir()}
        result = self.reconcile_cmd(); self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid']); self.assertEqual(before, {p.name: p.read_bytes() for p in self.evidence.iterdir()})

    def test_detects_stale_state_lock_and_missing_supervisor(self) -> None:
        self.write_state('running', '2026-07-17T20:00:00Z'); self.archive()
        locks = self.evidence / 'locks'; locks.mkdir(); (locks / 'job.lock').write_text(json.dumps({'updated_at': '2026-07-17T20:00:00Z'}))
        worktrees = self.evidence / 'worktrees'; worktrees.mkdir(); (worktrees / 'job.orphan').write_text('fixture')
        result = self.reconcile_cmd(); classes = {f['class'] for f in json.loads(result.stdout)['findings']}
        self.assertEqual(result.returncode, 1); self.assertTrue({'stale-state', 'stale-lock', 'orphan-worktree', 'missing-supervisor-result'} <= classes)

    def test_detects_manifest_and_catalog_drift(self) -> None:
        self.archive(b'original'); (self.evidence / 'result.json').write_text('changed')
        state = json.loads((self.evidence / 'state.json').read_text()); state['catalog_sha256'] = '0' * 64; (self.evidence / 'state.json').write_text(json.dumps(state))
        result = self.reconcile_cmd(); classes = {f['class'] for f in json.loads(result.stdout)['findings']}
        self.assertEqual(result.returncode, 1); self.assertTrue({'archive-checksum-mismatch', 'obsolete-runtime-catalog'} <= classes)

    def test_detects_missing_release_evidence(self) -> None:
        self.archive(); (self.evidence / 'release-evidence.json').unlink()
        result = self.reconcile_cmd(); classes = {f['class'] for f in json.loads(result.stdout)['findings']}
        self.assertEqual(result.returncode, 1); self.assertIn('missing-release-evidence', classes)


if __name__ == '__main__': unittest.main()
