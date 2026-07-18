#!/usr/bin/env python3
"""Enforce declared co-change contracts between operating-model sources and skills."""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REQUIRED = {'id', 'owner', 'reviewer', 'sources', 'dependents'}


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def load_contracts(path: Path, root: Path | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        return None, [f'cannot load sync contract: {error}']
    if not isinstance(payload, dict) or payload.get('schema_version') != 1:
        return None, ['sync contract schema_version must be 1']
    contracts = payload.get('contracts')
    if not isinstance(contracts, list) or not contracts:
        return None, ['sync contract requires a non-empty contracts list']
    errors: list[str] = []
    root = (root or path.resolve().parent.parent).resolve()
    ids: set[str] = set()
    for item in contracts:
        if not isinstance(item, dict) or not REQUIRED <= set(item):
            errors.append('each contract requires id, owner, reviewer, sources, and dependents')
            continue
        contract_id = item['id']
        if not isinstance(contract_id, str) or not contract_id or contract_id in ids:
            errors.append(f'invalid or duplicate contract id: {contract_id!r}')
        ids.add(contract_id)
        for key in ('owner', 'reviewer'):
            if not isinstance(item[key], str) or not item[key].strip():
                errors.append(f'{contract_id}: {key} must be non-empty')
        for key in ('sources', 'dependents'):
            patterns = item[key]
            if not isinstance(patterns, list) or not patterns or not all(isinstance(p, str) and p for p in patterns):
                errors.append(f'{contract_id}: {key} must be a non-empty path pattern list')
                continue
            for pattern in patterns:
                candidate = Path(pattern)
                if candidate.is_absolute() or '..' in candidate.parts:
                    errors.append(f'{contract_id}: {key} path must stay inside repository: {pattern!r}')
                elif not any(root.glob(pattern)):
                    errors.append(f'{contract_id}: {key} pattern resolves to no repository path: {pattern!r}')
    exceptions = payload.get('exceptions', [])
    if not isinstance(exceptions, list):
        errors.append('exceptions must be a list')
        exceptions = []
    for exception in exceptions:
        if not isinstance(exception, dict):
            errors.append('exception must be an object')
            continue
        for key in ('contract', 'reason', 'approved_by', 'expires_on'):
            if not isinstance(exception.get(key), str) or not exception[key].strip():
                errors.append(f'exception requires non-empty {key}')
        if isinstance(exception.get('contract'), str) and exception['contract'] not in ids:
            errors.append(f"exception references unknown contract: {exception['contract']!r}")
        try:
            date.fromisoformat(exception.get('expires_on', ''))
        except ValueError:
            errors.append('exception expires_on must be ISO-8601')
    return payload, errors


def changed_paths(root: Path, base: str, head: str) -> list[str]:
    result = subprocess.run(['git', 'diff', '--name-only', '--diff-filter=ACMR', f'{base}...{head}'], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f'cannot diff {base}...{head}')
    return [line for line in result.stdout.splitlines() if line]


def active_exception(payload: dict[str, Any], contract_id: str, today: date) -> bool:
    for exception in payload.get('exceptions', []):
        if isinstance(exception, dict) and exception.get('contract') == contract_id:
            try:
                if date.fromisoformat(exception['expires_on']) >= today:
                    return True
            except (KeyError, ValueError):
                pass
    return False


def git_file(root: Path, revision: str, path: str) -> str | None:
    result = subprocess.run(['git', 'show', f'{revision}:{path}'], cwd=root, text=True, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def version_from_skill(content: str | None) -> str | None:
    if not content or not content.startswith('---\n'):
        return None
    closing = content.find('\n---\n', 4)
    if closing == -1:
        return None
    metadata = yaml.safe_load(content[4:closing])
    return metadata.get('version') if isinstance(metadata, dict) and isinstance(metadata.get('version'), str) else None


SEMVER = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')


def semver_incremented(old: str | None, new: str | None) -> bool:
    old_match = SEMVER.fullmatch(old or '')
    new_match = SEMVER.fullmatch(new or '')
    return bool(old_match and new_match and tuple(map(int, new_match.groups())) > tuple(map(int, old_match.groups())))


def version_errors(root: Path, base: str, head: str, paths: list[str]) -> list[str]:
    errors: list[str] = []
    skill_names = {path.split('/', 2)[1] for path in paths if path.startswith('skills/') and path.count('/') >= 2}
    for name in sorted(skill_names):
        path = f'skills/{name}/SKILL.md'
        old, new = version_from_skill(git_file(root, base, path)), version_from_skill(git_file(root, head, path))
        if old is not None and not semver_incremented(old, new):
            errors.append(f'{name}: skill content changed without a semantic version increment')
    if 'governance/sync-contract.yaml' in paths:
        catalog_path = 'governance/skill-catalog.json'
        old_catalog, new_catalog = git_file(root, base, catalog_path), git_file(root, head, catalog_path)
        try:
            old_version = json.loads(old_catalog or '{}')['catalog']['version']
            new_version = json.loads(new_catalog or '{}')['catalog']['version']
            if not semver_incremented(old_version, new_version):
                errors.append('sync contract changed without a semantic catalog version increment')
        except (KeyError, TypeError, json.JSONDecodeError):
            errors.append('cannot compare catalog version for sync contract change')
    return errors


def validate_changes(payload: dict[str, Any], paths: list[str], today: date | None = None) -> list[str]:
    today = today or date.today()
    errors: list[str] = []
    for contract in payload['contracts']:
        source_changed = any(matches(path, contract['sources']) for path in paths)
        dependent_changed = any(matches(path, contract['dependents']) for path in paths)
        contract_changed = 'governance/sync-contract.yaml' in paths
        if source_changed and not (dependent_changed or contract_changed or active_exception(payload, contract['id'], today)):
            errors.append(f"{contract['id']}: source changed without declared dependent, contract update, or active exception")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--base')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--changed', action='append', default=[])
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()
    root = args.root.resolve(); contract_path = (args.contract or root / 'governance/sync-contract.yaml').resolve()
    payload, errors = load_contracts(contract_path, root)
    if payload and not errors:
        try:
            paths = args.changed or changed_paths(root, args.base, args.head) if args.base else args.changed
            if not paths and not args.base:
                errors.append('provide --base or at least one --changed path')
            else:
                errors.extend(validate_changes(payload, paths))
                if args.base:
                    errors.extend(version_errors(root, args.base, args.head, paths))
        except ValueError as error:
            errors.append(str(error))
    result = {'valid': not errors, 'errors': errors}
    if args.format == 'json': print(json.dumps(result, sort_keys=True))
    else:
        print('OK: sync contracts satisfied' if not errors else '\n'.join(f'ERROR: {error}' for error in errors))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
