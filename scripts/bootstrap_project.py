#!/usr/bin/env python3
"""Bootstrap a new project overlay directory inside the harness."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]{0,62}$')


def project_name(value: str) -> str:
    if not PROJECT_NAME_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            'invalid project name: use lowercase letters, digits, and hyphens; start with a letter'
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('project_name', type=project_name)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = args.root.resolve()
    projects_dir = root / 'projects'
    project_dir = projects_dir / args.project_name
    readme = project_dir / 'README.md'
    for path in (projects_dir, project_dir, readme):
        if path.is_symlink():
            parser.error(f'refusing symlinked bootstrap path: {path}')

    (project_dir / 'examples').mkdir(parents=True, exist_ok=True)
    if not readme.exists():
        readme.write_text(
            f'# {args.project_name}\n\nProject-specific overlay for {args.project_name}.\n',
            encoding='utf-8',
        )
    print(project_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
