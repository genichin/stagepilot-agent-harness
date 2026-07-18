from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_governance_sync import load_contracts, validate_changes, version_errors  # noqa: E402


class GovernanceSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload, errors = load_contracts(ROOT / 'governance/sync-contract.yaml')
        assert payload is not None, errors
        cls.payload = payload

    def test_repository_contract_is_valid(self) -> None:
        payload, errors = load_contracts(ROOT / 'governance/sync-contract.yaml')
        self.assertIsNotNone(payload)
        self.assertEqual(errors, [])

    def test_unresolved_contract_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            contract_path = root / 'governance' / 'sync-contract.yaml'
            contract_path.parent.mkdir()
            contract_path.write_text(
                'schema_version: 1\ncontracts:\n  - id: invalid\n    owner: owner\n    reviewer: reviewer\n    sources: [missing/**]\n    dependents: [also-missing/**]\n',
                encoding='utf-8',
            )
            payload, errors = load_contracts(contract_path)
            self.assertIsNotNone(payload)
            self.assertTrue(any('resolves to no repository path' in error for error in errors))

    def test_unknown_exception_contract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'roles').mkdir(); (root / 'skills' / 'alpha').mkdir(parents=True)
            (root / 'roles' / 'lead.md').write_text('role', encoding='utf-8')
            (root / 'skills' / 'alpha' / 'SKILL.md').write_text('skill', encoding='utf-8')
            contract_path = root / 'external.yaml'
            contract_path.write_text(
                'schema_version: 1\ncontracts:\n  - id: known\n    owner: owner\n    reviewer: reviewer\n    sources: [roles/**]\n    dependents: [skills/alpha/**]\nexceptions:\n  - contract: unknown\n    reason: temporary\n    approved_by: reviewer\n    expires_on: "2099-01-01"\n',
                encoding='utf-8',
            )
            _, errors = load_contracts(contract_path, root)
            self.assertIn("exception references unknown contract: 'unknown'", errors)

    def test_source_only_change_fails(self) -> None:
        errors = validate_changes(self.payload, ['roles/lead.md'], date(2026, 7, 18))
        self.assertEqual(len(errors), 1)
        self.assertIn('role-topology', errors[0])

    def test_source_and_declared_dependent_passes(self) -> None:
        errors = validate_changes(self.payload, ['roles/lead.md', 'skills/stagepilot-role-topology/SKILL.md'])
        self.assertEqual(errors, [])

    def test_version_change_requires_skill_increment(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / 'skills' / 'alpha' / 'SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('---\nname: alpha\nversion: 1.0.0\n---\nfirst\n', encoding='utf-8')
            def git(*args: str) -> str:
                return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            git('init', '-q')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            skill.write_text('---\nname: alpha\nversion: 1.0.0\n---\nchanged\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'unchanged version')
            head = git('rev-parse', 'HEAD')
            self.assertIn('alpha: skill content changed without a semantic version increment', version_errors(root, base, head, ['skills/alpha/SKILL.md']))
            skill.write_text('---\nname: alpha\nversion: 0.9.0\n---\ndecreased\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'decrease version')
            decreased = git('rev-parse', 'HEAD')
            self.assertIn('alpha: skill content changed without a semantic version increment', version_errors(root, head, decreased, ['skills/alpha/SKILL.md']))
            skill.write_text('---\nname: alpha\nversion: 1.0.1\n---\nchanged again\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'bump version')
            bumped = git('rev-parse', 'HEAD')
            self.assertEqual(version_errors(root, head, bumped, ['skills/alpha/SKILL.md']), [])

    def test_contract_update_or_active_exception_permits_source_change(self) -> None:
        self.assertEqual(validate_changes(self.payload, ['roles/lead.md', 'governance/sync-contract.yaml']), [])
        payload = copy.deepcopy(self.payload)
        payload['exceptions'] = [{'contract': 'role-topology', 'reason': 'approved migration', 'approved_by': 'reviewer', 'expires_on': '2026-07-19'}]
        self.assertEqual(validate_changes(payload, ['roles/lead.md'], date(2026, 7, 18)), [])
        self.assertEqual(len(validate_changes(payload, ['roles/lead.md'], date(2026, 7, 20))), 1)


if __name__ == '__main__':
    unittest.main()
