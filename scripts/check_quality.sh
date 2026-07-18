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

if [[ -n "${GIT_BASE:-}" && -n "${GIT_HEAD:-}" ]]; then
  git cat-file -e "${GIT_BASE}^{commit}"
  git cat-file -e "${GIT_HEAD}^{commit}"
  python3 scripts/validate_governance_sync.py --root . --base "$GIT_BASE" --head "$GIT_HEAD" --format json
  git diff --check "$GIT_BASE...$GIT_HEAD"
else
  git diff --check
fi
