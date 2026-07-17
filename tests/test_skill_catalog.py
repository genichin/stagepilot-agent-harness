#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / 'scripts' / 'validate_skill_catalog.py'


class SkillCatalogValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / 'skills').mkdir()
        (self.root / 'governance').mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def add_skill(
        self,
        name: str,
        *,
        directory_name: str | None = None,
        related_skills: list[str] | None = None,
        version: str = '1.0.0',
        content: str | None = None,
    ) -> None:
        skill_dir = self.root / 'skills' / (directory_name or name)
        skill_dir.mkdir()
        if content is None:
            content = f'''---
name: {name}
description: Test skill {name}
version: {version}
author: Test
license: private
metadata:
  hermes:
    tags: [test]
    related_skills: {related_skills or []}
---

# {name}
'''
        (skill_dir / 'SKILL.md').write_text(content, encoding='utf-8')

    def write_manifest(self, skills: dict[str, dict[str, object]]) -> None:
        payload = {
            'schema_version': 1,
            'catalog': {
                'version': '1.0.0',
                'owner': 'catalog-maintainer',
                'reviewer': 'governance-reviewer',
            },
            'skills': skills,
        }
        (self.root / 'governance' / 'skill-catalog.json').write_text(
            json.dumps(payload),
            encoding='utf-8',
        )

    def active_entry(self, version: str = '1.0.0') -> dict[str, object]:
        return {
            'version': version,
            'lifecycle': 'active',
            'owner': 'catalog-maintainer',
            'reviewer': 'governance-reviewer',
        }

    def validate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['python3', str(VALIDATOR), '--root', str(self.root), '--format', 'json'],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_complete_catalog(self) -> None:
        self.add_skill('alpha')
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(json.loads(result.stdout), {'valid': True, 'errors': [], 'skill_count': 1})

    def test_rejects_duplicate_frontmatter_name(self) -> None:
        self.add_skill('alpha')
        self.add_skill('alpha', directory_name='beta')
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn('duplicate frontmatter name: alpha', json.loads(result.stdout)['errors'])

    def test_rejects_missing_local_markdown_link(self) -> None:
        self.add_skill('alpha', content='''---
name: alpha
description: Test skill alpha
version: 1.0.0
author: Test
license: private
metadata:
  hermes:
    tags: [test]
    related_skills: []
---

[missing template](references/missing.md)
''')
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            'alpha: local markdown link target does not exist: references/missing.md',
            json.loads(result.stdout)['errors'],
        )

    def test_rejects_non_semantic_catalog_version(self) -> None:
        self.add_skill('alpha')
        self.write_manifest({'alpha': self.active_entry()})
        manifest_path = self.root / 'governance' / 'skill-catalog.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['catalog']['version'] = 'not-a-version'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            'governance manifest catalog.version must be semantic version X.Y.Z',
            json.loads(result.stdout)['errors'],
        )

    def test_rejects_malformed_frontmatter(self) -> None:
        self.add_skill('alpha', content='---\nname: [unterminated\n---\n')
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn('invalid YAML frontmatter', json.loads(result.stdout)['errors'][0])

    def test_rejects_directory_and_frontmatter_name_mismatch(self) -> None:
        self.add_skill('alpha', directory_name='wrong-name')
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn('directory name must match frontmatter name', json.loads(result.stdout)['errors'])

    def test_rejects_dangling_related_skill(self) -> None:
        self.add_skill('alpha', related_skills=['missing'])
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn('related skill does not exist: alpha -> missing', json.loads(result.stdout)['errors'])

    def test_rejects_manifest_version_mismatch(self) -> None:
        self.add_skill('alpha', version='1.2.3')
        self.write_manifest({'alpha': self.active_entry('1.2.4')})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            'alpha: governance manifest version must match frontmatter version',
            json.loads(result.stdout)['errors'],
        )

    def test_rejects_symlinked_skill_directory(self) -> None:
        external = self.root / 'external-alpha'
        external.mkdir()
        (external / 'SKILL.md').write_text(
            '''---
name: alpha
description: Test skill alpha
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
        (self.root / 'skills' / 'alpha').symlink_to(external, target_is_directory=True)
        self.write_manifest({'alpha': self.active_entry()})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn('skill directory must not be a symlink: alpha', json.loads(result.stdout)['errors'])

    def test_rejects_deprecated_skill_without_complete_replacement_contract(self) -> None:
        self.add_skill('alpha')
        deprecated = self.active_entry()
        deprecated['lifecycle'] = 'deprecated'
        self.write_manifest({'alpha': deprecated})

        result = self.validate()

        self.assertEqual(result.returncode, 1)
        errors = json.loads(result.stdout)['errors']
        self.assertIn('deprecated skill requires non-empty replacement', errors)
        self.assertIn('deprecated skill requires ISO-8601 sunset date', errors)
        self.assertIn('deprecated skill requires non-empty migration_note', errors)

    def test_invalid_catalog_does_not_modify_export_destination(self) -> None:
        self.add_skill('alpha')
        self.write_manifest({'alpha': self.active_entry('1.0.1')})
        destination = self.root / 'exported'
        destination.mkdir()
        marker = destination / 'keep.txt'
        marker.write_text('unchanged', encoding='utf-8')

        result = subprocess.run(
            [
                'python3', str(ROOT / 'scripts' / 'export_skills.py'),
                '--root', str(self.root),
                '--dest', str(destination),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'unchanged')
        self.assertFalse((destination / 'alpha').exists())

    def test_repository_catalog_is_valid_and_exports(self) -> None:
        result = subprocess.run(
            ['python3', str(VALIDATOR), '--root', str(ROOT), '--format', 'json'],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        validation = json.loads(result.stdout)
        self.assertTrue(validation['valid'])
        with tempfile.TemporaryDirectory() as destination:
            destination_path = Path(destination)
            export_result = subprocess.run(
                ['python3', str(ROOT / 'scripts' / 'export_skills.py'), '--dest', destination],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(export_result.returncode, 0, msg=export_result.stderr)
            export_payload = json.loads(export_result.stdout)
            self.assertFalse(export_payload['dry_run'])
            self.assertEqual(len(export_payload['manifest']['skills']), validation['skill_count'])
            exported_skills = sorted(path.name for path in destination_path.iterdir() if path.is_dir())
            self.assertEqual(len(exported_skills), validation['skill_count'])
            self.assertTrue((destination_path / 'stagepilot-skill-catalog-governance' / 'SKILL.md').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
