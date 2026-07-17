#!/usr/bin/env python3
"""Compare a validated source skill catalog with an explicit exported destination."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from export_skills import MANIFEST_NAME, build_manifest, skill_sha256
from validate_skill_catalog import validate_catalog


def verify_runtime_skill_sync(source: Path, dest: Path) -> dict[str, Any]:
    source_errors, _ = validate_catalog(source)
    if source_errors:
        return {
            'valid': False,
            'errors': source_errors,
            'missing': [],
            'modified': [],
            'stale': [],
            'next_action': 'repair source catalog before export',
        }

    expected_manifest = build_manifest(source)
    expected = {item['name']: item for item in expected_manifest['skills']}
    errors: list[str] = []
    missing: list[str] = []
    modified: list[str] = []
    stale: list[str] = []
    manifest_path = dest / MANIFEST_NAME
    actual_manifest: dict[str, Any] | None = None
    if not dest.is_dir() or dest.is_symlink():
        errors.append(f'destination must be a non-symlink directory: {dest}')
    elif not manifest_path.is_file():
        errors.append(f'missing export manifest: {manifest_path}')
    else:
        try:
            loaded = json.loads(manifest_path.read_text(encoding='utf-8'))
            if not isinstance(loaded, dict) or not isinstance(loaded.get('skills'), list):
                raise ValueError('manifest must be an object with a skills list')
            actual_manifest = loaded
        except (json.JSONDecodeError, ValueError) as error:
            errors.append(f'invalid export manifest: {error}')

    if dest.is_dir() and not dest.is_symlink():
        actual_dirs = {path.name for path in dest.iterdir() if path.is_dir() and not path.is_symlink()}
        stale.extend(sorted(actual_dirs - set(expected)))
        for name, item in expected.items():
            skill_dir = dest / name
            if not skill_dir.is_dir() or skill_dir.is_symlink():
                missing.append(name)
                continue
            try:
                if skill_sha256(skill_dir) != item['sha256']:
                    modified.append(name)
            except ValueError as error:
                errors.append(str(error))
                modified.append(name)

    if actual_manifest is not None:
        manifest_skills = {item.get('name'): item for item in actual_manifest['skills'] if isinstance(item, dict)}
        for name, item in expected.items():
            if manifest_skills.get(name) != item:
                modified.append(name)
        stale.extend(name for name in manifest_skills if isinstance(name, str) and name not in expected)

    missing = sorted(set(missing))
    modified = sorted(set(modified))
    stale = sorted(set(stale))
    valid = not errors and not missing and not modified and not stale
    return {
        'valid': valid,
        'errors': errors,
        'source_revision': expected_manifest['source_revision'],
        'destination': str(dest),
        'missing': missing,
        'modified': modified,
        'stale': stale,
        'next_action': 'none' if valid else 'run export_skills.py with an explicit destination after reviewing drift',
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--dest', required=True, type=Path)
    parser.add_argument('--format', choices=('json', 'text'), default='text')
    args = parser.parse_args()

    result = verify_runtime_skill_sync(args.source.expanduser().resolve(), args.dest.expanduser().resolve())
    if args.format == 'json':
        print(json.dumps(result, sort_keys=True))
    else:
        print('OK' if result['valid'] else 'DRIFT')
        for key in ('errors', 'missing', 'modified', 'stale'):
            for item in result[key]:
                print(f'{key}: {item}')
        print(f"next_action: {result['next_action']}")
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
