#!/usr/bin/env python3
"""Create a redacted failed-harness observation draft; publish only when requested."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPOSITORY = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
SAFE_IDENTIFIER = re.compile(r'^[A-Za-z0-9_.-]{1,128}$')


def load_result(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(result, dict) or result.get('valid') is not False or not isinstance(result.get('findings'), list):
        raise ValueError('only a failed verification result can be reported')
    return result


def finding_codes(result: dict[str, Any]) -> list[str]:
    codes: set[str] = set()
    for item in result['findings']:
        if isinstance(item, dict) and isinstance(item.get('class'), str):
            codes.add(item['class'])
    return sorted(codes) or ['unclassified-harness-failure']


def render_draft(result: dict[str, Any], delivery_id: str, revision: str) -> tuple[str, str]:
    if not SAFE_IDENTIFIER.fullmatch(delivery_id) or not SAFE_IDENTIFIER.fullmatch(revision):
        raise ValueError('delivery-id and harness-revision must be safe identifiers')
    codes = finding_codes(result)
    title = f'Harness observation: {delivery_id} ({", ".join(codes[:3])})'
    body = '\n'.join([
        '## Harness observation', '',
        'Generated from a failed local delivery health check.', '',
        f'- Delivery ID: `{delivery_id}`',
        f'- Delivery profile: `{result.get("delivery_profile") or "unknown"}`',
        f'- Checked transitions: `{result.get("checked_transitions", 0)}`',
        f'- Harness revision: `{revision}`', '',
        '### Finding codes', *[f'- `{code}`' for code in codes], '',
        '### Reproduction',
        'Run `verify_delivery_trace.py` against the affected evidence directory. Attach reviewed JSON only if it contains no project-sensitive data.', '',
        '_This draft intentionally excludes absolute paths, credentials, remote URLs, and raw worker logs._', '',
    ])
    return title, body


def publish(repo: str, title: str, draft: Path) -> str:
    if not REPOSITORY.fullmatch(repo):
        raise ValueError('repo must be owner/name')
    if subprocess.run(['gh', 'auth', 'status'], text=True, capture_output=True).returncode:
        raise RuntimeError('GitHub authentication is unavailable')
    created = subprocess.run(['gh', 'issue', 'create', '--repo', repo, '--title', title, '--body-file', str(draft)], text=True, capture_output=True)
    if created.returncode:
        raise RuntimeError('GitHub issue publication failed')
    return created.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--verification-result', required=True, type=Path)
    parser.add_argument('--delivery-id', required=True)
    parser.add_argument('--harness-revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--repo')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    try:
        result = load_result(args.verification_result)
        title, body = render_draft(result, args.delivery_id, args.harness_revision)
        output = args.output.expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(body, encoding='utf-8')
        url = None
        if args.publish:
            if not args.repo:
                raise ValueError('--repo is required with --publish')
            url = publish(args.repo, title, output)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f'ERROR: {error}')
        return 1
    print(json.dumps({'draft': str(output), 'publish_requested': args.publish, 'published_url': url}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
