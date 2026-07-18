#!/usr/bin/env python3
"""Read-only reconciliation for fixture runtime evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE = {'ready', 'running', 'blocked'}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def when(value: str) -> datetime:
    value = value.replace('Z', '+00:00')
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def reconcile(evidence: Path, catalog_sha256: str, now: datetime, stale_seconds: int) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    state_path = evidence / 'state.json'
    state: dict[str, Any] = {}
    if not state_path.is_file():
        findings.append({'class': 'missing-state', 'path': str(state_path), 'action': 'escalate'})
    else:
        state = load(state_path)
        if state.get('status') in ACTIVE:
            try:
                if (now - when(state['updated_at'])).total_seconds() > stale_seconds:
                    findings.append({'class': 'stale-state', 'path': str(state_path), 'action': 'escalate'})
            except (KeyError, ValueError):
                findings.append({'class': 'invalid-state-timestamp', 'path': str(state_path), 'action': 'escalate'})
        if state.get('status') == 'running' and not (evidence / 'supervisor-result.json').is_file():
            findings.append({'class': 'missing-supervisor-result', 'path': str(evidence), 'action': 'escalate'})
        if state.get('catalog_sha256') and state['catalog_sha256'] != catalog_sha256:
            findings.append({'class': 'obsolete-runtime-catalog', 'path': str(state_path), 'action': 'refresh'})
    release = evidence / 'release-evidence.json'
    if not release.is_file():
        findings.append({'class': 'missing-release-evidence', 'path': str(release), 'action': 'record'})
    else:
        try:
            record = load(release)
            required = ('source_revision', 'catalog_version', 'catalog_sha256', 'export_manifest_sha256', 'verifier_version', 'recorded_at')
            if any(not isinstance(record.get(field), str) or not record[field] for field in required):
                findings.append({'class': 'invalid-release-provenance', 'path': str(release), 'action': 'escalate'})
            elif record['catalog_sha256'] != catalog_sha256:
                findings.append({'class': 'obsolete-release-provenance', 'path': str(release), 'action': 'refresh'})
        except (OSError, ValueError, json.JSONDecodeError):
            findings.append({'class': 'invalid-release-provenance', 'path': str(release), 'action': 'escalate'})
    for lock in sorted((evidence / 'locks').glob('*.lock')) if (evidence / 'locks').is_dir() else []:
        try:
            age = (now - when(load(lock)['updated_at'])).total_seconds()
            if age > stale_seconds:
                findings.append({'class': 'stale-lock', 'path': str(lock), 'action': 'manual-reclaim'})
        except (KeyError, ValueError, json.JSONDecodeError):
            findings.append({'class': 'invalid-lock', 'path': str(lock), 'action': 'manual-reclaim'})
    for worktree in sorted((evidence / 'worktrees').glob('*.orphan')) if (evidence / 'worktrees').is_dir() else []:
        findings.append({'class': 'orphan-worktree', 'path': str(worktree), 'action': 'manual-reclaim'})
    manifest = evidence / 'archive-manifest.json'
    if not manifest.is_file():
        findings.append({'class': 'missing-archive-manifest', 'path': str(manifest), 'action': 'archive'})
    else:
        try:
            for item in load(manifest).get('files', []):
                artifact = evidence / item['path']
                if not artifact.is_file() or digest(artifact) != item.get('sha256'):
                    findings.append({'class': 'archive-checksum-mismatch', 'path': str(artifact), 'action': 'restore-or-escalate'})
        except (KeyError, ValueError, json.JSONDecodeError):
            findings.append({'class': 'invalid-archive-manifest', 'path': str(manifest), 'action': 'escalate'})
    return {'valid': not findings, 'evidence': str(evidence), 'findings': findings, 'purge_performed': False, 'retention_authority_required': True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--now', default=None)
    parser.add_argument('--stale-seconds', type=int, default=3600)
    args = parser.parse_args()
    now = when(args.now) if args.now else datetime.now(timezone.utc)
    result = reconcile(args.evidence_dir.resolve(), digest(args.catalog), now, args.stale_seconds)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['valid'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
