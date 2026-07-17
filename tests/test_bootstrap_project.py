#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'bootstrap_project.py'


class BootstrapProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_bootstrap(self, project_name: str) -> subprocess.CompletedProcess[str]:
        command = ['python3', str(SCRIPT), '--root', str(self.root)]
        if project_name.startswith('-'):
            command.append('--')
        command.append(project_name)
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_creates_minimal_project_overlay(self) -> None:
        result = self.run_bootstrap('sample-project')

        project_dir = self.root / 'projects' / 'sample-project'
        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
        self.assertEqual(result.stdout.strip(), str(project_dir))
        self.assertTrue((project_dir / 'examples').is_dir())
        self.assertEqual(
            (project_dir / 'README.md').read_text(encoding='utf-8'),
            '# sample-project\n\nProject-specific overlay for sample-project.\n',
        )

    def test_rerun_is_idempotent_and_preserves_existing_readme(self) -> None:
        self.assertEqual(self.run_bootstrap('sample-project').returncode, 0)
        readme = self.root / 'projects' / 'sample-project' / 'README.md'
        readme.write_text('# Maintained overlay\n', encoding='utf-8')

        result = self.run_bootstrap('sample-project')

        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
        self.assertEqual(readme.read_text(encoding='utf-8'), '# Maintained overlay\n')

    def test_accepts_maximum_length_project_name(self) -> None:
        project_name = 'a' + ('b' * 62)
        result = self.run_bootstrap(project_name)

        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
        self.assertTrue((self.root / 'projects' / project_name).is_dir())

    def test_rejects_unsafe_project_names_without_creating_paths(self) -> None:
        for project_name in ('../escape', '/tmp/escape', 'nested/name', '', 'Uppercase', '1project', '-project', 'a' * 64):
            with self.subTest(project_name=project_name):
                result = self.run_bootstrap(project_name)
                self.assertEqual(result.returncode, 2)
                self.assertIn('invalid project name', result.stderr)

        self.assertFalse((self.root / 'escape').exists())
        self.assertFalse((self.root / 'projects').exists())

    def test_refuses_symlinked_project_paths(self) -> None:
        outside = self.root / 'outside'
        outside.mkdir()
        projects_dir = self.root / 'projects'
        projects_dir.symlink_to(outside, target_is_directory=True)

        result = self.run_bootstrap('sample-project')

        self.assertEqual(result.returncode, 2)
        self.assertIn('refusing symlinked bootstrap path', result.stderr)
        self.assertFalse((outside / 'sample-project').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
