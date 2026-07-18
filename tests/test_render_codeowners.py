from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'render_codeowners.py'
CONTRACT = ROOT / 'governance' / 'sync-contract.yaml'


class RenderCodeownersTests(unittest.TestCase):
    def run_renderer(self, identities: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        identity_path = root / 'identities.yaml'
        output = root / 'CODEOWNERS'
        identity_path.write_text(identities, encoding='utf-8')
        result = subprocess.run(
            ['python3', str(SCRIPT), '--contract', str(CONTRACT), '--identities', str(identity_path), '--output', str(output)],
            text=True,
            capture_output=True,
        )
        return result, output

    def test_renders_explicit_role_mapping(self) -> None:
        result, output = self.run_renderer(
            'roles:\n  stagepilot-governance-reviewer: "@example/governance"\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = output.read_text(encoding='utf-8')
        self.assertIn('/governance/** @example/governance', rendered)
        self.assertIn('/roles/** @example/governance', rendered)
        self.assertIn('/skills/stagepilot-role-topology/** @example/governance', rendered)

    def test_rejects_non_github_identity(self) -> None:
        result, output = self.run_renderer(
            'roles:\n  stagepilot-governance-reviewer: stagepilot-governance-reviewer\n'
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())
        self.assertIn('explicit GitHub', result.stderr)


if __name__ == '__main__':
    unittest.main()
