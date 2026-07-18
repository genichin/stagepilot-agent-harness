#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
EXPORTER = SCRIPTS / 'export_skills.py'
PARITY = SCRIPTS / 'verify_runtime_skill_sync.py'
sys.path.insert(0, str(SCRIPTS))
import export_skills as exporter  # noqa: E402


class ExportSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / 'source'
        (self.root / 'skills' / 'alpha').mkdir(parents=True)
        (self.root / 'governance').mkdir()
        (self.root / 'skills' / 'alpha' / 'SKILL.md').write_text(
            '''---
name: alpha
description: Alpha test skill
version: 1.0.0
author: Test
license: private
metadata:
  hermes:
    tags: [test]
    related_skills: []
---
''',
            encoding='utf-8',
        )
        (self.root / 'governance' / 'skill-catalog.json').write_text(
            json.dumps({
                'schema_version': 1,
                'catalog': {'version': '1.0.0', 'owner': 'test', 'reviewer': 'test'},
                'skills': {
                    'alpha': {'version': '1.0.0', 'lifecycle': 'active', 'owner': 'test', 'reviewer': 'test'},
                },
            }),
            encoding='utf-8',
        )
        self.dest = Path(self.tempdir.name) / 'destination'

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_export(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['python3', str(EXPORTER), '--root', str(self.root), '--dest', str(self.dest), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def run_parity(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['python3', str(PARITY), '--source', str(self.root), '--dest', str(self.dest), '--format', 'json'],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_dry_run_does_not_create_destination(self) -> None:
        result = self.run_export('--dry-run')

        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertFalse(self.dest.exists())
        payload = json.loads(result.stdout)
        self.assertTrue(payload['dry_run'])
        self.assertEqual(payload['manifest']['skills'][0]['name'], 'alpha')

    def test_export_manifest_and_parity(self) -> None:
        result = self.run_export()

        self.assertEqual(result.returncode, 0, msg=result.stdout)
        manifest = json.loads((self.dest / 'catalog-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['schema_version'], 2)
        self.assertEqual(len(manifest['catalog_sha256']), 64)
        self.assertEqual(manifest['skills'][0]['name'], 'alpha')
        self.assertTrue((self.dest / 'alpha' / 'SKILL.md').is_file())

        parity = self.run_parity()
        self.assertEqual(parity.returncode, 0, msg=parity.stdout)
        self.assertTrue(json.loads(parity.stdout)['valid'])

        manifest['catalog_sha256'] = '0' * 64
        (self.dest / 'catalog-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        parity = self.run_parity()
        self.assertEqual(parity.returncode, 1)
        self.assertIn('manifest provenance mismatch for catalog_sha256', json.loads(parity.stdout)['errors'])

        self.assertEqual(self.run_export().returncode, 0)
        (self.dest / 'alpha' / 'SKILL.md').write_text('tampered', encoding='utf-8')
        parity = self.run_parity()
        self.assertEqual(parity.returncode, 1)
        self.assertEqual(json.loads(parity.stdout)['modified'], ['alpha'])

    def test_prune_and_no_prune(self) -> None:
        stale = self.dest / 'stale'
        stale.mkdir(parents=True)
        (stale / 'SKILL.md').write_text('stale', encoding='utf-8')

        self.assertEqual(self.run_export('--no-prune').returncode, 0)
        self.assertTrue(stale.is_dir())
        self.assertEqual(self.run_export('--prune').returncode, 0)
        self.assertFalse(stale.exists())

    def test_post_promote_verification_failure_restores_existing_destination(self) -> None:
        self.dest.mkdir()
        marker = self.dest / 'keep.txt'
        marker.write_text('preserved', encoding='utf-8')
        original_verify = exporter.verify_export_tree

        def fail_only_after_promote(tree: Path, manifest: dict[str, object]) -> None:
            if tree == self.dest:
                raise ValueError('injected post-promote verification failure')
            original_verify(tree, manifest)

        with patch.object(exporter, 'verify_export_tree', side_effect=fail_only_after_promote):
            with self.assertRaises(ValueError):
                exporter.export_skills(self.root, self.dest)

        self.assertEqual(marker.read_text(encoding='utf-8'), 'preserved')
        self.assertFalse((self.dest / 'alpha').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
