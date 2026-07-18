#!/usr/bin/env python3
"""Safely export the validated harness skill catalog to an explicit destination."""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from validate_skill_catalog import validate_catalog

MANIFEST_NAME = 'catalog-manifest.json'


def catalog_errors(root: Path) -> list[str]:
    errors, _ = validate_catalog(root)
    return errors


def skill_sha256(skill_dir: Path) -> str:
    """Hash every regular file in a skill directory in deterministic path order."""
    digest = hashlib.sha256()
    for path in sorted(skill_dir.rglob('*')):
        if path.is_dir():
            continue
        if path.is_symlink():
            raise ValueError(f'skill export refuses symlinked file: {path}')
        if not path.is_file():
            raise ValueError(f'skill export refuses non-regular file: {path}')
        digest.update(path.relative_to(skill_dir).as_posix().encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def source_revision(root: Path) -> str:
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else 'redacted-unavailable'


def catalog_sha256(root: Path) -> str:
    return hashlib.sha256((root / 'governance' / 'skill-catalog.json').read_bytes()).hexdigest()


def build_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / 'governance' / 'skill-catalog.json'
    catalog = json.loads(manifest_path.read_text(encoding='utf-8'))
    skills = []
    for name in sorted(catalog['skills']):
        skills.append({
            'name': name,
            'version': catalog['skills'][name]['version'],
            'sha256': skill_sha256(root / 'skills' / name),
        })
    return {
        'schema_version': 2,
        'catalog_version': catalog['catalog']['version'],
        'catalog_sha256': catalog_sha256(root),
        'hash_algorithm': 'sha256',
        'source_revision': source_revision(root),
        'generated_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'skills': skills,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def verify_export_tree(tree: Path, manifest: dict[str, Any]) -> None:
    for item in manifest['skills']:
        skill_dir = tree / item['name']
        if not skill_dir.is_dir() or skill_dir.is_symlink():
            raise ValueError(f'staged skill is missing or unsafe: {item["name"]}')
        if skill_sha256(skill_dir) != item['sha256']:
            raise ValueError(f'staged skill hash mismatch: {item["name"]}')
    if json.loads((tree / MANIFEST_NAME).read_text(encoding='utf-8')) != manifest:
        raise ValueError('staged export manifest mismatch')


def reject_unsafe_destination(root: Path, dest: Path) -> None:
    source_skills = root / 'skills'
    if dest == root or dest == source_skills or source_skills in dest.parents:
        raise ValueError(f'export destination must not overlap source catalog: {dest}')


def rename_exchange(first: Path, second: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        operation = libc.renameat2
    except AttributeError as error:
        raise OSError(errno.ENOSYS, 'renameat2 is unavailable; atomic replacement is unsupported') from error
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(-100, os.fsencode(first), -100, os.fsencode(second), 2) != 0:
        error_code = ctypes.get_errno()
        raise OSError(error_code, os.strerror(error_code), str(first), str(second))


def prepare_staging(root: Path, dest: Path, *, prune: bool, manifest: dict[str, Any]) -> Path:
    staging = Path(tempfile.mkdtemp(prefix=f'.{dest.name}.stage-', dir=dest.parent))
    try:
        if dest.exists():
            if not dest.is_dir() or dest.is_symlink():
                raise ValueError(f'export destination must be a non-symlink directory: {dest}')
            shutil.copytree(dest, staging, dirs_exist_ok=True)

        source_names = {item['name'] for item in manifest['skills']}
        if prune:
            for child in staging.iterdir():
                if child.name not in source_names and child.is_dir():
                    shutil.rmtree(child)

        for name in sorted(source_names):
            target = staging / name
            if target.exists():
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.copytree(root / 'skills' / name, target)
        write_json(staging / MANIFEST_NAME, manifest)
        return staging
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def promote(staging: Path, dest: Path, manifest: dict[str, Any]) -> None:
    if not dest.exists():
        try:
            os.replace(staging, dest)
            verify_export_tree(dest, manifest)
        except Exception:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            raise
        return

    exchanged = False
    try:
        rename_exchange(staging, dest)
        exchanged = True
        verify_export_tree(dest, manifest)
    except Exception:
        if exchanged:
            rename_exchange(staging, dest)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def export_skills(root: Path, dest: Path, *, prune: bool = False, dry_run: bool = False) -> dict[str, Any]:
    errors = catalog_errors(root)
    if errors:
        raise ValueError('skill catalog validation failed:\n' + '\n'.join(f'- {error}' for error in errors))
    manifest = build_manifest(root)
    if dry_run:
        return manifest
    reject_unsafe_destination(root, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = prepare_staging(root, dest, prune=prune, manifest=manifest)
    verify_export_tree(staging, manifest)
    promote(staging, dest, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=Path(__file__).resolve().parents[1], type=Path, help='Harness repository root')
    parser.add_argument('--dest', required=True, type=Path, help='Explicit destination skills directory')
    parser.add_argument('--dry-run', action='store_true', help='Validate and render the manifest without changing --dest')
    parser.add_argument('--prune', dest='prune', action='store_true', default=False, help='Remove stale skill directories explicitly')
    parser.add_argument('--no-prune', dest='prune', action='store_false', help='Preserve stale skill directories (default)')
    parser.add_argument('--output-manifest', type=Path, help='Copy the generated manifest to this explicit path after promotion')
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    dest = args.dest.expanduser().resolve()
    try:
        manifest = export_skills(root, dest, prune=args.prune, dry_run=args.dry_run)
        if args.output_manifest and not args.dry_run:
            write_json(args.output_manifest.expanduser().resolve(), manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f'ERROR: {error}')
        return 1

    print(json.dumps({
        'dry_run': args.dry_run,
        'manifest': manifest,
        'prune': args.prune,
        'destination': str(dest),
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
