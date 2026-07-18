from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'record_release_evidence.py'


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = self.root / 'catalog-manifest.json'
        self.parity = self.root / 'parity.json'
        self.evidence = self.root / 'evidence'
        self.manifest.write_text(json.dumps({
            'source_revision': 'fixture-revision',
            'catalog_version': '1.2.3',
            'catalog_sha256': 'a' * 64,
        }), encoding='utf-8')
        self.parity.write_text(json.dumps({'valid': True}), encoding='utf-8')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def record(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([
            'python3', str(SCRIPT), '--manifest', str(self.manifest), '--parity-result', str(self.parity),
            '--evidence-dir', str(self.evidence), '--verifier-version', 'fixture-v1',
            '--timestamp', '2026-07-18T00:00:00Z',
        ], text=True, capture_output=True, check=False)

    def test_records_complete_provenance(self) -> None:
        result = self.record()
        self.assertEqual(result.returncode, 0, result.stdout)
        record = json.loads((self.evidence / 'release-evidence.json').read_text(encoding='utf-8'))
        self.assertEqual(record['source_revision'], 'fixture-revision')
        self.assertEqual(record['catalog_version'], '1.2.3')
        self.assertEqual(record['verifier_version'], 'fixture-v1')
        self.assertEqual(record['export_manifest_sha256'], hashlib.sha256(self.manifest.read_bytes()).hexdigest())

    def test_rejects_failed_parity(self) -> None:
        self.parity.write_text(json.dumps({'valid': False}), encoding='utf-8')
        result = self.record()
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.evidence / 'release-evidence.json').exists())


if __name__ == '__main__':
    unittest.main()
