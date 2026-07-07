#!/usr/bin/env python3
"""Simple structure verifier for the harness scaffold."""
from __future__ import annotations

from pathlib import Path

REQUIRED = [
    'README.md',
    'docs/architecture.md',
    'roles/lead.md',
    'handoffs/lead-to-runner.md',
    'templates/kickoff.md',
    'profiles/templates/lead.SOUL.md',
    'projects/trex/README.md',
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [p for p in REQUIRED if not (root / p).exists()]
    if missing:
        for item in missing:
            print(f'MISSING: {item}')
        return 1
    print('OK: required scaffold files present')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
