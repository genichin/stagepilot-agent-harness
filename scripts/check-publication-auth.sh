#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/check-publication-auth.sh [--branch NAME] [--json]

Checks whether the current delivery worktree appears ready for PR-bound publication.
`STAGEPILOT_GH_HOME`, when set, is the explicit GitHub CLI credential-home source;
otherwise the current process `HOME` is used. The helper never probes host-specific
credential locations and never emits raw auth command output.
This is a preflight helper for `delivery-runner` before impl/QC work burns time.

Checks performed:
  - git remote get-url origin
  - gh auth status
  - git ls-remote origin
  - git push --dry-run origin HEAD:refs/heads/<branch>

Exit codes:
  0 = publication preflight passed
  3 = publication auth/reachability preflight failed
  2 = usage or local prerequisite failure
EOF
}

BRANCH=""
JSON=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      BRANCH=${2:-}
      [[ -n "$BRANCH" ]] || { echo "error: --branch requires a value" >&2; exit 2; }
      shift 2
      ;;
    --json)
      JSON=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "error: git not found" >&2; exit 2; }
command -v gh >/dev/null 2>&1 || { echo "error: gh not found" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "error: python3 not found" >&2; exit 2; }

git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "error: not inside a git repository" >&2; exit 2; }
if git remote get-url origin >/dev/null 2>&1; then
  origin_configured=true
  classification="ok"
  reason="publication_preflight_ok"
else
  origin_configured=false
  classification="publication_auth_missing"
  reason="publication_auth_missing:no_origin_remote"
fi

if [[ -z "$BRANCH" ]]; then
  BRANCH=$(git branch --show-current 2>/dev/null || true)
fi
if [[ -z "$BRANCH" ]]; then
  BRANCH="HEAD"
fi

if [[ -n "${STAGEPILOT_GH_HOME:-}" ]]; then
  auth_home="$STAGEPILOT_GH_HOME"
  auth_source="STAGEPILOT_GH_HOME"
else
  auth_home="${HOME:-}"
  auth_source="HOME"
fi

# A missing origin is a local preflight failure. Do not invoke auth, remote, or
# push commands in that case, and never retain their potentially sensitive output.
gh_status_rc=-1
ls_remote_rc=-1
push_rc=-1
if [[ "$origin_configured" == true ]]; then
  set +e
  HOME="$auth_home" gh auth status >/dev/null 2>&1
  gh_status_rc=$?
  HOME="$auth_home" git ls-remote origin >/dev/null 2>&1
  ls_remote_rc=$?
  HOME="$auth_home" git push --dry-run origin "HEAD:refs/heads/$BRANCH" >/dev/null 2>&1
  push_rc=$?
  set -e
fi

if [[ "$classification" == "ok" && "$gh_status_rc" -ne 0 ]]; then
  classification="publication_auth_missing"
  reason="publication_auth_missing:gh_auth_status_failed"
fi
if [[ "$classification" == "ok" && "$ls_remote_rc" -ne 0 ]]; then
  classification="publication_auth_missing"
  reason="publication_auth_missing:origin_unreachable"
fi
if [[ "$classification" == "ok" && "$push_rc" -ne 0 ]]; then
  classification="publication_auth_missing"
  reason="publication_auth_missing:push_dry_run_failed"
fi

if [[ "$JSON" -eq 1 ]]; then
  export BRANCH_NAME="$BRANCH"
  export CLASSIFICATION="$classification"
  export REASON="$reason"
  export AUTH_SOURCE="$auth_source"
  export GH_STATUS_RC="$gh_status_rc"
  export LS_REMOTE_RC="$ls_remote_rc"
  export PUSH_RC="$push_rc"
  python3 - <<'PY'
import json
import os

payload = {
    'branch': os.environ['BRANCH_NAME'],
    'classification': os.environ['CLASSIFICATION'],
    'reason': os.environ['REASON'],
    'auth_source': os.environ['AUTH_SOURCE'],
    'checks': {
        'gh_auth_status': {'ok': int(os.environ['GH_STATUS_RC']) == 0, 'exit_code': int(os.environ['GH_STATUS_RC'])},
        'git_ls_remote_origin': {'ok': int(os.environ['LS_REMOTE_RC']) == 0, 'exit_code': int(os.environ['LS_REMOTE_RC'])},
        'git_push_dry_run': {'ok': int(os.environ['PUSH_RC']) == 0, 'exit_code': int(os.environ['PUSH_RC'])},
    },
}
print(json.dumps(payload, indent=2))
PY
else
  cat <<EOF
origin_configured: $([[ -n "$origin_url" ]] && printf true || printf false)
branch: $BRANCH
classification: $classification
reason: $reason
auth_source: $auth_source
gh_auth_status_exit: $gh_status_rc
git_ls_remote_exit: $ls_remote_rc
git_push_dry_run_exit: $push_rc
EOF
fi

if [[ "$classification" == "ok" ]]; then
  exit 0
fi
exit 3
