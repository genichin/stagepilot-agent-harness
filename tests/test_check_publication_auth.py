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
SCRIPT = ROOT / 'scripts' / 'check-publication-auth.sh'


class PublicationPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tempdir.name)
        self.repo = self.tmp / 'repo'
        self.remote = self.tmp / 'remote.git'
        self.bin_dir = self.tmp / 'bin'
        self.capture_dir = self.tmp / 'captures'
        self.repo.mkdir()
        self.bin_dir.mkdir()
        self.capture_dir.mkdir()

        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(['git', 'init'], cwd=self.repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo, check=True)
        (self.repo / 'README.md').write_text('hello\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=self.repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(['git', 'branch', '-M', 'delivery/test'], cwd=self.repo, check=True)
        subprocess.run(['git', 'remote', 'add', 'origin', str(self.remote)], cwd=self.repo, check=True)

        gh_stub = self.bin_dir / 'gh'
        gh_stub.write_text(
            '#!/usr/bin/env bash\n'
            'status_file="${GH_STATUS_FILE:?}"\n'
            'if [[ -f "$status_file" ]]; then\n'
            '  cat "$status_file"\n'
            'fi\n'
            'exit "${GH_EXIT_CODE:-0}"\n',
            encoding='utf-8',
        )
        gh_stub.chmod(0o755)
        self.git = shutil.which('git')
        if self.git is None:
            self.fail('git is required for publication preflight tests')
        git_stub = self.bin_dir / 'git'
        git_stub.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "${FAIL_GIT_PUSH:-0}" == 1 && "${1:-}" == push ]]; then exit 23; fi\n'
            'exec "$REAL_GIT" "$@"\n',
            encoding='utf-8',
        )
        git_stub.chmod(0o755)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_preflight(
        self,
        *,
        gh_exit_code: int = 0,
        gh_status_text: str = 'logged in',
        branch: str | None = None,
        gh_home: str | None = None,
        fail_git_push: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        status_file = self.capture_dir / 'gh-status.txt'
        status_file.write_text(gh_status_text, encoding='utf-8')
        env = os.environ.copy()
        env['PATH'] = f"{self.bin_dir}:{env['PATH']}"
        env['GH_EXIT_CODE'] = str(gh_exit_code)
        env['GH_STATUS_FILE'] = str(status_file)
        env['REAL_GIT'] = self.git or ''
        env['FAIL_GIT_PUSH'] = '1' if fail_git_push else '0'
        if gh_home is not None:
            env['STAGEPILOT_GH_HOME'] = gh_home
        args = [str(SCRIPT), '--json']
        if branch is not None:
            args.extend(['--branch', branch])
        return subprocess.run(args, cwd=self.repo, env=env, text=True, capture_output=True, check=False)

    def test_preflight_passes_when_auth_and_remote_checks_pass(self) -> None:
        result = self.run_preflight()
        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['classification'], 'ok')
        self.assertEqual(payload['reason'], 'publication_preflight_ok')
        self.assertTrue(payload['checks']['gh_auth_status']['ok'])
        self.assertTrue(payload['checks']['git_ls_remote_origin']['ok'])
        self.assertTrue(payload['checks']['git_push_dry_run']['ok'])
        self.assertEqual(payload['auth_source'], 'HOME')
        self.assertNotIn('output', payload['checks']['gh_auth_status'])

    def test_preflight_uses_only_explicit_gh_home_override(self) -> None:
        result = self.run_preflight(gh_home='/explicit/managed-gh-home')
        self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['auth_source'], 'STAGEPILOT_GH_HOME')
        self.assertNotIn('auth_home_used', payload)

    def test_preflight_reports_missing_origin_without_exposing_remote_url(self) -> None:
        subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=self.repo, check=True)
        result = self.run_preflight(gh_exit_code=1, gh_status_text='not logged in')
        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['reason'], 'publication_auth_missing:no_origin_remote')
        self.assertEqual(payload['checks']['gh_auth_status']['exit_code'], -1)
        self.assertEqual(payload['checks']['git_ls_remote_origin']['exit_code'], -1)
        self.assertEqual(payload['checks']['git_push_dry_run']['exit_code'], -1)
        self.assertNotIn('origin_url', payload)
        self.assertNotIn('repo_root', payload)

    def test_preflight_reports_unreachable_origin(self) -> None:
        subprocess.run(
            ['git', 'remote', 'set-url', 'origin', str(self.tmp / 'missing-remote.git')],
            cwd=self.repo,
            check=True,
        )
        result = self.run_preflight()
        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['reason'], 'publication_auth_missing:origin_unreachable')
        self.assertFalse(payload['checks']['git_ls_remote_origin']['ok'])

    def test_preflight_reports_push_dry_run_failure(self) -> None:
        result = self.run_preflight(fail_git_push=True)
        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['reason'], 'publication_auth_missing:push_dry_run_failed')
        self.assertFalse(payload['checks']['git_push_dry_run']['ok'])

    def test_preflight_fails_fast_when_gh_auth_is_missing(self) -> None:
        result = self.run_preflight(gh_exit_code=1, gh_status_text='not logged in')
        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['classification'], 'publication_auth_missing')
        self.assertEqual(payload['reason'], 'publication_auth_missing:gh_auth_status_failed')
        self.assertFalse(payload['checks']['gh_auth_status']['ok'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
