#!/usr/bin/env python3
"""Fixture-only, explicit-target StagePilot profile bootstrap lifecycle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from export_skills import export_skills
from verify_runtime_skill_sync import verify_runtime_skill_sync

MARKER = '.stagepilot-bootstrap-state.json'
CONTRACT = 'stagepilot-profile-contract.json'


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def safe_target(value: str) -> Path:
    target = Path(value)
    home = Path.home() / '.hermes'
    if not target.is_absolute() or target == home or target.is_symlink():
        raise ValueError('target home must be an absolute, non-symlink fixture path outside ~/.hermes')
    return target.resolve()


def build_plan(root: Path, fixture: Path) -> dict[str, Any]:
    data = read_json(fixture)
    if data.get('schema_version') != 1 or not isinstance(data.get('profiles'), list) or not data['profiles']:
        raise ValueError('fixture must contain schema_version=1 and non-empty profiles')
    profiles = []
    names: set[str] = set()
    for entry in data['profiles']:
        name, soul = entry.get('name'), entry.get('soul')
        if not isinstance(name, str) or not name or name in names or not isinstance(soul, str):
            raise ValueError('each profile requires a unique name and soul path')
        source = (root / soul).resolve()
        if root not in source.parents or not source.is_file() or source.is_symlink():
            raise ValueError(f'unsafe or missing SOUL template: {soul}')
        names.add(name)
        profiles.append({
            'role': entry.get('role', name), 'name': name, 'soul': soul,
            'soul_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'model': entry.get('model'), 'cwd': entry.get('cwd'), 'toolsets': entry.get('toolsets', []),
        })
    catalog = root / 'governance' / 'skill-catalog.json'
    plan = {'schema_version': 1, 'fixture_sha256': digest(data), 'catalog_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest(), 'profiles': profiles}
    plan['plan_id'] = digest(plan)
    return plan


def write_plan(plan: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def verify(root: Path, plan: dict[str, Any], target: Path) -> dict[str, Any]:
    drift: list[str] = []
    state = target / MARKER
    if not state.is_file(): drift.append('missing bootstrap state')
    elif read_json(state).get('plan_id') != plan['plan_id']: drift.append('plan id mismatch')
    catalog = root / 'governance' / 'skill-catalog.json'
    if not catalog.is_file() or hashlib.sha256(catalog.read_bytes()).hexdigest() != plan['catalog_sha256']:
        drift.append('source catalog revision drift')
    for profile in plan['profiles']:
        source = root / profile['soul']
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != profile['soul_sha256']:
            drift.append(f"source SOUL drift: {profile['name']}")
        base = target / 'profiles' / profile['name']
        soul, contract = base / 'SOUL.md', base / CONTRACT
        if not soul.is_file() or hashlib.sha256(soul.read_bytes()).hexdigest() != profile['soul_sha256']:
            drift.append(f"SOUL drift: {profile['name']}")
        if not contract.is_file() or read_json(contract) != profile:
            drift.append(f"contract drift: {profile['name']}")
    parity = verify_runtime_skill_sync(root, target / 'skills')
    if not parity['valid']: drift.append('skill catalog parity drift')
    return {'valid': not drift, 'drift': drift, 'plan_id': plan['plan_id'], 'target_home': str(target)}


def apply(root: Path, plan: dict[str, Any], target: Path) -> dict[str, Any]:
    if target.exists() and target.is_symlink(): raise ValueError('refusing symlink target')
    if target.exists() and any(target.iterdir()) and not (target / MARKER).is_file():
        raise ValueError('target home must be empty or managed by this bootstrap')
    if target.exists() and (target / MARKER).is_file() and read_json(target / MARKER).get('plan_id') == plan['plan_id']:
        result = verify(root, plan, target)
        result['rollback_path'] = None
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f'.{target.name}.stage-', dir=target.parent))
    try:
        for profile in plan['profiles']:
            source = root / profile['soul']
            base = staging / 'profiles' / profile['name']; base.mkdir(parents=True)
            shutil.copyfile(source, base / 'SOUL.md')
            write_plan(profile, base / CONTRACT)
        export_skills(root, staging / 'skills', prune=True)
        write_plan({'schema_version': 1, 'plan_id': plan['plan_id']}, staging / MARKER)
        staged = verify(root, plan, staging)
        if not staged['valid']: raise ValueError('; '.join(staged['drift']))
        rollback = None
        if target.exists():
            rollback = target.parent / f'.{target.name}.rollback-{plan["plan_id"][:12]}'
            if rollback.exists(): shutil.rmtree(rollback)
            os.replace(target, rollback)
        try:
            os.replace(staging, target)
            result = verify(root, plan, target)
            if not result['valid']: raise ValueError('; '.join(result['drift']))
        except Exception:
            if target.exists(): shutil.rmtree(target)
            if rollback: os.replace(rollback, target)
            raise
        result['rollback_path'] = str(rollback) if rollback else None
        return result
    finally:
        if staging.exists(): shutil.rmtree(staging)


def rollback(target: Path, rollback_dir: Path) -> dict[str, Any]:
    if rollback_dir.parent != target.parent or rollback_dir.is_symlink() or not (rollback_dir / MARKER).is_file():
        raise ValueError('rollback dir must be a managed direct sibling of target home')
    displaced = target.parent / f'.{target.name}.rollback-displaced'
    if displaced.exists():
        raise ValueError('rollback displacement path already exists')
    try:
        if target.exists(): os.replace(target, displaced)
        os.replace(rollback_dir, target)
    except Exception:
        if displaced.exists() and not target.exists(): os.replace(displaced, target)
        raise
    return {'valid': True, 'target_home': str(target), 'restored_from': str(rollback_dir), 'rollback_path': str(displaced) if displaced.exists() else None}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'apply', 'verify', 'report'):
        command = sub.add_parser(name); command.add_argument('--plan', type=Path); command.add_argument('--fixture', type=Path); command.add_argument('--target-home'); command.add_argument('--target-profile', action='append', default=[])
        if name == 'plan': command.add_argument('--output', type=Path, required=True)
    rollback_command = sub.add_parser('rollback')
    rollback_command.add_argument('--target-home', required=True)
    rollback_command.add_argument('--rollback-dir', type=Path, required=True)
    args = parser.parse_args(); root = args.root.resolve()
    try:
        if args.command == 'rollback':
            result = rollback(safe_target(args.target_home), safe_target(str(args.rollback_dir)))
            print(json.dumps(result, sort_keys=True)); return 0
        if args.command == 'plan':
            if not args.fixture: raise ValueError('--fixture is required')
            write_plan(build_plan(root, args.fixture), args.output); return 0
        if not args.plan or not args.target_home: raise ValueError('--plan and --target-home are required')
        plan, target = read_json(args.plan), safe_target(args.target_home)
        if args.command == 'apply' and sorted(args.target_profile) != sorted(profile['name'] for profile in plan.get('profiles', [])):
            raise ValueError('--target-profile set must exactly match the plan profiles')
        result = apply(root, plan, target) if args.command == 'apply' else verify(root, plan, target)
        print(json.dumps(result, sort_keys=True)); return 0 if result['valid'] else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 2

if __name__ == '__main__': raise SystemExit(main())
