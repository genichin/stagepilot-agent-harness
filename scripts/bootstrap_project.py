#!/usr/bin/env python3
"""Bootstrap a new project overlay directory inside the harness."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('project_name')
    parser.add_argument('--root', default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = Path(args.root)
    project_dir = root / 'projects' / args.project_name
    (project_dir / 'examples').mkdir(parents=True, exist_ok=True)
    readme = project_dir / 'README.md'
    if not readme.exists():
        readme.write_text(f'# {args.project_name}

Project-specific overlay for {args.project_name}.
')
    print(project_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
