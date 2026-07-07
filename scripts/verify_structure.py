#!/usr/bin/env python3
"""Structure and skill verifier for the harness scaffold."""
from __future__ import annotations

from pathlib import Path

REQUIRED = [
    'README.md',
    'docs/architecture.md',
    'docs/skills.md',
    'roles/lead.md',
    'handoffs/lead-to-runner.md',
    'templates/kickoff.md',
    'profiles/templates/lead.SOUL.md',
    'projects/trex/README.md',
    'skills/stagepilot-agent-harness/SKILL.md',
    'skills/stagepilot-role-topology/SKILL.md',
    'skills/stagepilot-handoffs/SKILL.md',
    'scripts/export_skills.py',
]
REQUIRED_FRONTMATTER_KEYS = ('name:', 'description:')


def verify_skill(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding='utf-8')
    if not content.startswith('---\n'):
        errors.append(f'{path}: missing opening frontmatter marker')
        return errors
    if '\n---\n' not in content[4:]:
        errors.append(f'{path}: missing closing frontmatter marker')
        return errors
    for key in REQUIRED_FRONTMATTER_KEYS:
        if key not in content:
            errors.append(f'{path}: missing frontmatter key {key}')
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [p for p in REQUIRED if not (root / p).exists()]
    if missing:
        for item in missing:
            print(f'MISSING: {item}')
        return 1

    errors: list[str] = []
    skills_root = root / 'skills'
    for skill_path in sorted(skills_root.glob('*/SKILL.md')):
        errors.extend(verify_skill(skill_path))

    if errors:
        for error in errors:
            print(f'ERROR: {error}')
        return 1

    print('OK: required scaffold files and skill frontmatter present')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
