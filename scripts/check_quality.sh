#!/usr/bin/env bash
# Provider-independent structural, catalog, and regression gate.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

python3 -m compileall -q scripts
bash -n scripts/*.sh
python3 scripts/validate_skill_catalog.py --root . --format json
python3 scripts/verify_structure.py
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
