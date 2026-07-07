#!/usr/bin/env python3
"""Export in-repo StagePilot harness skills into a Hermes skills directory."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REQUIRED_FRONTMATTER_KEYS = ('name:', 'description:')


def validate_skill(skill_dir: Path) -> None:
    skill_path = skill_dir / 'SKILL.md'
    if not skill_path.exists():
        raise FileNotFoundError(f'Missing {skill_path}')
    content = skill_path.read_text(encoding='utf-8')
    if not content.startswith('---\n'):
        raise ValueError(f'{skill_path} must start with frontmatter')
    if '\n---\n' not in content[4:]:
        raise ValueError(f'{skill_path} missing frontmatter terminator')
    for key in REQUIRED_FRONTMATTER_KEYS:
        if key not in content:
            raise ValueError(f'{skill_path} missing required frontmatter key: {key}')


def export_skills(root: Path, dest: Path) -> list[str]:
    skills_root = root / 'skills'
    exported: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        validate_skill(skill_dir)
        target = dest / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        exported.append(skill_dir.name)
    return exported


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', required=True, help='Destination directory for exported skills')
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    dest = Path(args.dest).expanduser().resolve()
    exported = export_skills(root, dest)
    for name in exported:
        print(f'EXPORTED: {name}')
    print(f'TOTAL: {len(exported)} skill(s) -> {dest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
