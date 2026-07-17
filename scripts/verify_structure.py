#!/usr/bin/env python3
"""Structure and skill verifier for the harness scaffold."""
from __future__ import annotations

from pathlib import Path

from validate_skill_catalog import validate_catalog

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
    'scripts/validate_skill_catalog.py',
    'governance/skill-catalog.json',
    'requirements.txt',
    'skills/stagepilot-skill-catalog-governance/SKILL.md',
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [p for p in REQUIRED if not (root / p).exists()]
    if missing:
        for item in missing:
            print(f'MISSING: {item}')
        return 1

    errors, skill_count = validate_catalog(root)
    if errors:
        for error in errors:
            print(f'ERROR: {error}')
        return 1

    print(f'OK: required scaffold files and validated skill catalog present ({skill_count} skill(s))')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
