#!/usr/bin/env python3
"""Validate the StagePilot in-repository skill catalog and governance manifest."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - dependency failure is environment-specific
    print('ERROR: PyYAML is required; install dependencies from requirements.txt', file=sys.stderr)
    raise SystemExit(2)

SEMVER_PATTERN = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')
MARKDOWN_LINK_PATTERN = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)')
LIFECYCLES = {'active', 'deprecated'}


def is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def extract_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    content = path.read_text(encoding='utf-8')
    if not content.startswith('---\n'):
        return None, 'missing opening frontmatter marker'
    closing = content.find('\n---\n', 4)
    if closing == -1:
        return None, 'missing closing frontmatter marker'
    try:
        frontmatter = yaml.safe_load(content[4:closing])
    except yaml.YAMLError as error:
        return None, f'invalid YAML frontmatter: {error}'
    if not isinstance(frontmatter, dict):
        return None, 'frontmatter must be a mapping'
    return frontmatter, None


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f'missing governance manifest: {path}']
    try:
        manifest = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        return None, [f'invalid governance manifest JSON: {error.msg}']
    if not isinstance(manifest, dict):
        return None, ['governance manifest must be an object']
    errors: list[str] = []
    if manifest.get('schema_version') != 1:
        errors.append('governance manifest schema_version must be 1')
    catalog = manifest.get('catalog')
    if not isinstance(catalog, dict):
        errors.append('governance manifest catalog must be an object')
    else:
        catalog_version = catalog.get('version')
        if not isinstance(catalog_version, str) or not SEMVER_PATTERN.fullmatch(catalog_version):
            errors.append('governance manifest catalog.version must be semantic version X.Y.Z')
        for field in ('owner', 'reviewer'):
            if not is_non_empty_string(catalog.get(field)):
                errors.append(f'governance manifest catalog requires non-empty {field}')
    if not isinstance(manifest.get('skills'), dict):
        errors.append('governance manifest skills must be an object')
    return manifest, errors


def validate_skill_metadata(skill_name: str, metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ('name', 'description', 'version', 'author', 'license'):
        if not is_non_empty_string(metadata.get(key)):
            errors.append(f'{skill_name}: required frontmatter key must be a non-empty string: {key}')
    version = metadata.get('version')
    if isinstance(version, str) and version and not SEMVER_PATTERN.fullmatch(version):
        errors.append(f'{skill_name}: version must be semantic version X.Y.Z')

    hermes = metadata.get('metadata', {}).get('hermes') if isinstance(metadata.get('metadata'), dict) else None
    if not isinstance(hermes, dict):
        errors.append(f'{skill_name}: metadata.hermes must be an object')
        return errors
    tags = hermes.get('tags')
    if not isinstance(tags, list) or not tags or not all(is_non_empty_string(tag) for tag in tags):
        errors.append(f'{skill_name}: metadata.hermes.tags must be a non-empty string list')
    related = hermes.get('related_skills')
    if not isinstance(related, list) or not all(is_non_empty_string(item) for item in related):
        errors.append(f'{skill_name}: metadata.hermes.related_skills must be a string list')
    return errors


def local_link_errors(root: Path, skill_path: Path) -> list[str]:
    errors: list[str] = []
    root_path = root.resolve()
    for raw_target in MARKDOWN_LINK_PATTERN.findall(skill_path.read_text(encoding='utf-8')):
        target = raw_target.strip('<>').split('#', 1)[0]
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            continue
        resolved = (skill_path.parent / target).resolve()
        try:
            resolved.relative_to(root_path)
        except ValueError:
            errors.append(f'{skill_path.parent.name}: local markdown link escapes repository: {raw_target}')
            continue
        if not resolved.is_file():
            errors.append(f'{skill_path.parent.name}: local markdown link target does not exist: {raw_target}')
    return errors


def validate_manifest_entry(skill_name: str, entry: object, catalog_names: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return [f'{skill_name}: governance manifest entry must be an object']
    for field in ('version', 'owner', 'reviewer'):
        if not is_non_empty_string(entry.get(field)):
            errors.append(f'{skill_name}: governance manifest requires non-empty {field}')
    lifecycle = entry.get('lifecycle')
    if lifecycle not in LIFECYCLES:
        errors.append(f'{skill_name}: lifecycle must be one of {sorted(LIFECYCLES)}')
    if lifecycle == 'deprecated':
        replacement = entry.get('replacement')
        if not is_non_empty_string(replacement):
            errors.append('deprecated skill requires non-empty replacement')
        elif replacement not in catalog_names:
            errors.append(f'deprecated replacement does not exist: {skill_name} -> {replacement}')
        if not is_non_empty_string(entry.get('migration_note')):
            errors.append('deprecated skill requires non-empty migration_note')
        sunset = entry.get('sunset')
        try:
            if not isinstance(sunset, str) or not sunset.strip():
                raise ValueError
            date.fromisoformat(sunset)
        except ValueError:
            errors.append('deprecated skill requires ISO-8601 sunset date')
    return errors


def validate_catalog(root: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    skills_root = root / 'skills'
    if not skills_root.is_dir():
        return [f'missing skills directory: {skills_root}'], 0

    stray_files = sorted(path.name for path in skills_root.iterdir() if not path.is_dir())
    for name in stray_files:
        errors.append(f'skills root contains stray file: {name}')

    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir())
    metadata_by_name: dict[str, dict[str, Any]] = {}
    related_by_name: dict[str, list[str]] = {}
    for skill_dir in skill_dirs:
        if skill_dir.is_symlink():
            errors.append(f'skill directory must not be a symlink: {skill_dir.name}')
            continue
        skill_path = skill_dir / 'SKILL.md'
        if not skill_path.is_file():
            errors.append(f'{skill_dir.name}: missing SKILL.md')
            continue
        metadata, parse_error = extract_frontmatter(skill_path)
        if parse_error:
            errors.append(f'{skill_dir.name}: {parse_error}')
            continue
        assert metadata is not None
        name = metadata.get('name')
        if not isinstance(name, str) or not name.strip():
            errors.append(f'{skill_dir.name}: required frontmatter key must be a non-empty string: name')
            continue
        if name != skill_dir.name:
            errors.append('directory name must match frontmatter name')
        if name in metadata_by_name:
            errors.append(f'duplicate frontmatter name: {name}')
            continue
        metadata_by_name[name] = metadata
        errors.extend(validate_skill_metadata(name, metadata))
        errors.extend(local_link_errors(root, skill_path))
        hermes = metadata.get('metadata', {}).get('hermes') if isinstance(metadata.get('metadata'), dict) else {}
        related_by_name[name] = hermes.get('related_skills', []) if isinstance(hermes, dict) else []

    catalog_names = set(metadata_by_name)
    for skill_name, related_skills in sorted(related_by_name.items()):
        for related in related_skills:
            if related == skill_name:
                errors.append(f'related skill must not self-reference: {skill_name}')
            elif related not in catalog_names:
                errors.append(f'related skill does not exist: {skill_name} -> {related}')

    manifest, manifest_errors = load_manifest(root / 'governance' / 'skill-catalog.json')
    errors.extend(manifest_errors)
    if manifest is not None and isinstance(manifest.get('skills'), dict):
        entries = manifest['skills']
        entry_names = set(entries)
        for name in sorted(catalog_names - entry_names):
            errors.append(f'governance manifest missing skill: {name}')
        for name in sorted(entry_names - catalog_names):
            errors.append(f'governance manifest references unknown skill: {name}')
        for name in sorted(catalog_names & entry_names):
            entry = entries[name]
            errors.extend(validate_manifest_entry(name, entry, catalog_names))
            if isinstance(entry, dict) and entry.get('version') != metadata_by_name[name].get('version'):
                errors.append(f'{name}: governance manifest version must match frontmatter version')
    return errors, len(skill_dirs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()

    errors, skill_count = validate_catalog(args.root.resolve())
    if args.format == 'json':
        print(json.dumps({'valid': not errors, 'errors': errors, 'skill_count': skill_count}, sort_keys=True))
    elif errors:
        for error in errors:
            print(f'ERROR: {error}')
    else:
        print(f'OK: validated {skill_count} skill(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
