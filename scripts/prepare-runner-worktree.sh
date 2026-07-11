#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/prepare-runner-worktree.sh [options] <kickoff_artifact> <delivery_state>

Create or reuse an isolated git worktree + delivery branch for one root kickoff item.

Core rule: isolate runner delivery work from the lead/human primary checkout.
Default local convention is repo-local `.worktrees/`, but project adoption may override the parent-folder layout
(for example a top-level `repos/` workspace or an external shared worktree root) via overlay guidance or explicit flags.

Options:
  --repo-root PATH       Target delivery repository root (default: repo field from delivery_state, then cwd)
  --base-ref REF         Base ref for new branch/worktree (default: main)
  --branch-name NAME     Explicit branch name (default: sp/<kickoff-base>-delivery)
  --worktree-path PATH   Explicit worktree path (default: <repo>/.worktrees/<kickoff-base>)
  --meta-dir PATH        Metadata dir (default: <repo>/.stagepilot/worktree-map)
  --dry-run              Print derived values without creating worktree
  -h, --help             Show this help
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

abspath() {
  python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$1"
}

slugify() {
  python3 - "$1" <<'PY'
import re, sys
value = sys.argv[1]
value = re.sub(r'[^A-Za-z0-9._-]+', '-', value).strip('-')
print(value or 'kickoff')
PY
}

REPO_ROOT_ARG=""
BASE_REF="main"
BRANCH_NAME=""
WORKTREE_PATH=""
META_DIR=""
DRY_RUN=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT_ARG="$2"
      shift 2
      ;;
    --base-ref)
      BASE_REF="$2"
      shift 2
      ;;
    --branch-name)
      BRANCH_NAME="$2"
      shift 2
      ;;
    --worktree-path)
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --meta-dir)
      META_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do POSITIONAL+=("$1"); shift; done
      ;;
    -*)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -ne 2 ]]; then
  usage >&2
  exit 1
fi

require_cmd git
require_cmd python3

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
KICKOFF_ARTIFACT="$(abspath "${POSITIONAL[0]}")"
DELIVERY_STATE="$(abspath "${POSITIONAL[1]}")"

if [[ ! -f "$KICKOFF_ARTIFACT" ]]; then
  echo "error: kickoff artifact not found: $KICKOFF_ARTIFACT" >&2
  exit 1
fi
if [[ ! -f "$DELIVERY_STATE" ]]; then
  echo "error: delivery state not found: $DELIVERY_STATE" >&2
  exit 1
fi

if [[ -n "$REPO_ROOT_ARG" ]]; then
  REPO_ROOT="$(abspath "$REPO_ROOT_ARG")"
else
  state_repo="$(python3 - "$DELIVERY_STATE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('repo') or '')
except Exception:
    print('')
PY
)"
  if [[ -n "$state_repo" ]]; then
    REPO_ROOT="$(abspath "$state_repo")"
  else
    REPO_ROOT="$(pwd)"
  fi
fi
if [[ ! -d "$REPO_ROOT/.git" && ! -f "$REPO_ROOT/.git" ]]; then
  echo "error: repo root is not a git checkout: $REPO_ROOT" >&2
  exit 1
fi

kickoff_base="$(basename "$KICKOFF_ARTIFACT")"
kickoff_base="${kickoff_base%.*}"
kickoff_base="$(slugify "$kickoff_base")"

BRANCH_NAME="${BRANCH_NAME:-sp/${kickoff_base}-delivery}"
WORKTREE_PATH="${WORKTREE_PATH:-$REPO_ROOT/.worktrees/$kickoff_base}"
META_DIR="${META_DIR:-$REPO_ROOT/.stagepilot/worktree-map}"
WORKTREE_PATH="$(abspath "$WORKTREE_PATH")"
META_DIR="$(abspath "$META_DIR")"
META_FILE="$META_DIR/${kickoff_base}.env"

branch_exists=0
if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  branch_exists=1
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  cat <<EOF
DRY RUN
repo_root: $REPO_ROOT
kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE
base_ref: $BASE_REF
branch_name: $BRANCH_NAME
branch_exists: $branch_exists
worktree_path: $WORKTREE_PATH
meta_file: $META_FILE
EOF
  exit 0
fi

mkdir -p "$META_DIR"
mkdir -p "$(dirname "$WORKTREE_PATH")"

if [[ -d "$WORKTREE_PATH/.git" || -f "$WORKTREE_PATH/.git" ]]; then
  :
elif [[ -e "$WORKTREE_PATH" && -n "$(find "$WORKTREE_PATH" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]]; then
  echo "error: worktree path exists and is not empty: $WORKTREE_PATH" >&2
  exit 1
else
  if [[ "$branch_exists" -eq 1 ]]; then
    git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
  else
    git -C "$REPO_ROOT" worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" "$BASE_REF"
  fi
fi

cat > "$META_FILE" <<EOF
repo_root=$REPO_ROOT
kickoff_artifact=$KICKOFF_ARTIFACT
delivery_state=$DELIVERY_STATE
base_ref=$BASE_REF
branch_name=$BRANCH_NAME
worktree_path=$WORKTREE_PATH
prepared_at=$(date --iso-8601=seconds)
EOF

cat <<EOF
prepared: true
repo_root: $REPO_ROOT
branch_name: $BRANCH_NAME
worktree_path: $WORKTREE_PATH
meta_file: $META_FILE
EOF
