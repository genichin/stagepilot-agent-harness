#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/lead-launch-runner.sh [options] <kickoff_artifact> <delivery_state>

Starts Hermes `delivery-runner` in a detached tmux session.
By default this script first prepares an isolated git worktree + delivery branch for the kickoff,
then launches the runner inside that worktree so lead/human discovery edits in the main checkout
cannot leak into the delivery PR branch.
After the runner process exits, the wrapper records both `exit_file` and `status_file` so leads can inspect
whether the root delivery state actually reached "done", explicit "blocked", or remained incomplete.
Core harness fixes the isolation rule plus a repo-local `.worktrees/` default, but project adoption may
choose a different parent-folder layout (for example `repos/` or an external worktree root) through overlay
conventions or explicit `--worktree-path` / `--workdir` overrides.

Options:
  --profile NAME           Hermes profile to launch (default: delivery-runner)
  --session-name NAME      tmux session name (default: runner-<kickoff-base>-<timestamp>)
  --log-dir PATH           Log directory (default: ./.stagepilot/runner-logs)
  --workdir PATH           Explicit working directory for the Hermes process; skips auto worktree prep
  --base-ref REF           Base ref for auto-prepared delivery branch/worktree (default: main)
  --branch-name NAME       Explicit delivery branch name for auto-prepared worktree
  --worktree-path PATH     Explicit path for auto-prepared worktree
  --skip-worktree          Do not auto-prepare isolated runner worktree
  --dry-run                Print derived launch values without starting tmux
  -h, --help               Show this help
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

PROFILE="delivery-runner"
SESSION_NAME=""
LOG_DIR=""
WORKDIR=""
BASE_REF="main"
BRANCH_NAME=""
WORKTREE_PATH=""
SKIP_WORKTREE=0
DRY_RUN=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --session-name)
      SESSION_NAME="$2"
      shift 2
      ;;
    --log-dir)
      LOG_DIR="$2"
      shift 2
      ;;
    --workdir)
      WORKDIR="$2"
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
    --skip-worktree)
      SKIP_WORKTREE=1
      shift
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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PREPARE_WORKTREE_SCRIPT="$SCRIPT_DIR/prepare-runner-worktree.sh"
DEFAULT_ROOT_WORKDIR="$REPO_ROOT"
LOG_DIR="${LOG_DIR:-$REPO_ROOT/.stagepilot/runner-logs}"

KICKOFF_ARTIFACT="$(abspath "${POSITIONAL[0]}")"
DELIVERY_STATE="$(abspath "${POSITIONAL[1]}")"
LOG_DIR="$(abspath "$LOG_DIR")"

if [[ ! -f "$KICKOFF_ARTIFACT" ]]; then
  echo "error: kickoff artifact not found: $KICKOFF_ARTIFACT" >&2
  exit 1
fi
if [[ ! -f "$DELIVERY_STATE" ]]; then
  echo "error: delivery state not found: $DELIVERY_STATE" >&2
  exit 1
fi

require_cmd hermes
require_cmd tmux
require_cmd python3
mkdir -p "$LOG_DIR"

PREPARED_WORKTREE_PATH=""
PREPARED_BRANCH_NAME=""
if [[ -n "$WORKDIR" ]]; then
  WORKDIR="$(abspath "$WORKDIR")"
elif [[ "$SKIP_WORKTREE" -eq 1 ]]; then
  WORKDIR="$DEFAULT_ROOT_WORKDIR"
else
  require_cmd git
  if [[ ! -x "$PREPARE_WORKTREE_SCRIPT" ]]; then
    echo "error: helper script not executable: $PREPARE_WORKTREE_SCRIPT" >&2
    exit 1
  fi
  prep_args=("$KICKOFF_ARTIFACT" "$DELIVERY_STATE" --base-ref "$BASE_REF")
  if [[ -n "$BRANCH_NAME" ]]; then prep_args+=(--branch-name "$BRANCH_NAME"); fi
  if [[ -n "$WORKTREE_PATH" ]]; then prep_args+=(--worktree-path "$WORKTREE_PATH"); fi
  if [[ "$DRY_RUN" -eq 1 ]]; then prep_args+=(--dry-run); fi
  prep_output="$($PREPARE_WORKTREE_SCRIPT "${prep_args[@]}")"
  PREPARED_WORKTREE_PATH="$(printf '%s
' "$prep_output" | awk -F': ' '/^worktree_path:/ {print $2}')"
  PREPARED_BRANCH_NAME="$(printf '%s
' "$prep_output" | awk -F': ' '/^branch_name:/ {print $2}')"
  if [[ -z "$PREPARED_WORKTREE_PATH" ]]; then
    echo "error: failed to derive worktree path from prepare-runner-worktree output" >&2
    echo "$prep_output" >&2
    exit 1
  fi
  WORKDIR="$PREPARED_WORKTREE_PATH"
fi
WORKDIR="$(abspath "$WORKDIR")"

if [[ -z "$SESSION_NAME" ]]; then
  kickoff_base="$(basename "$KICKOFF_ARTIFACT")"
  kickoff_base="${kickoff_base%.*}"
  kickoff_base="$(printf '%s' "$kickoff_base" | tr -cs 'A-Za-z0-9._-' '-')"
  timestamp="$(date +%Y%m%d-%H%M%S)"
  SESSION_NAME="runner-${kickoff_base}-${timestamp}"
fi

LOG_FILE="$LOG_DIR/${SESSION_NAME}.log"
EXIT_FILE="$LOG_DIR/${SESSION_NAME}.exit"
STATUS_FILE="$LOG_DIR/${SESSION_NAME}.status"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stagepilot-runner-${SESSION_NAME}.XXXXXX")"
PROMPT_FILE="$TMP_DIR/prompt.txt"
RUNNER_SCRIPT="$TMP_DIR/run-runner.sh"
IMPL_LAUNCHER="$SCRIPT_DIR/runner-launch-impl.sh"
QC_LAUNCHER="$SCRIPT_DIR/runner-launch-qc.sh"
PUBLICATION_PREFLIGHT="$SCRIPT_DIR/check-publication-auth.sh"

cat > "$PROMPT_FILE" <<EOF
Claim and execute this kickoff.

kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE

Instructions:
- Read both files first.
- Operate inside the current working directory; it is the delivery-isolated repo checkout for this kickoff unless the lead explicitly overrode it.
- If the delivery owner target is $PROFILE and the delivery state is ready, claim it by updating the state to canonical running. If you encounter legacy claimed or in_progress values, normalize them to running on the next write.
- Write the required acknowledgment with current stage, next artifact, likely blockers, and first execution step.
- Keep all delivery-branch code, tests, commits, and PR work inside the current isolated worktree.
- Do not pull unapproved live Discovery/REQ edits from the lead checkout into the delivery branch automatically; require explicit lead re-handoff or sync direction.
- Continue orchestration only within approved scope.
- Before spending substantial impl/QC effort on PR-bound delivery, run publication auth preflight from the delivery worktree and record the outcome in the delivery trail:
  - publication_preflight: $PUBLICATION_PREFLIGHT --json
  - minimum checks: git remote get-url origin, gh auth status, git ls-remote origin, git push --dry-run origin HEAD:refs/heads/<current-branch>
  - if preflight fails, stop early, reflect a blocked/escalation trail entry, and classify it with reason code publication_auth_missing (or a more specific suffix from the helper output).
- Use the canonical child launchers by default:
  - impl_launcher: $IMPL_LAUNCHER
  - qc_launcher: $QC_LAUNCHER
- Do not use generic delegation as a substitute for the canonical impl/QC wrappers unless the kickoff explicitly grants an override.
- Before exiting, the root delivery state must be in a terminal state visible to the lead: "done", explicit "blocked", or terminal historical "archived" closure. Exiting while the root state remains "ready" or canonical/legacy running values is incomplete.
- Do not use kanban.
- Keep the artifact/state trail as the source of truth.
EOF

cat > "$RUNNER_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$WORKDIR"
status=0
state_summary="unknown"
resume_command="$(printf '%q ' "$SCRIPT_DIR/lead-launch-runner.sh" --workdir "$WORKDIR" "$KICKOFF_ARTIFACT" "$DELIVERY_STATE")"
cleanup() {
  printf '%s\n' "\$status" > "$EXIT_FILE"
  cat > "$STATUS_FILE" <<STATUS
exit_code=\$status
state_summary=\$state_summary
session_name=$SESSION_NAME
profile=$PROFILE
delivery_state=$DELIVERY_STATE
log_file=$LOG_FILE
resume_command=\$resume_command
STATUS
}
trap cleanup EXIT
{
  echo "[stagepilot] session=$SESSION_NAME"
  echo "[stagepilot] profile=$PROFILE"
  echo "[stagepilot] kickoff_artifact=$KICKOFF_ARTIFACT"
  echo "[stagepilot] delivery_state=$DELIVERY_STATE"
  echo "[stagepilot] workdir=$WORKDIR"
  if [[ -n "$PREPARED_BRANCH_NAME" ]]; then echo "[stagepilot] delivery_branch=$PREPARED_BRANCH_NAME"; fi
  echo "[stagepilot] impl_launcher=$IMPL_LAUNCHER"
  echo "[stagepilot] qc_launcher=$QC_LAUNCHER"
  echo "[stagepilot] publication_preflight=$PUBLICATION_PREFLIGHT"
  echo "[stagepilot] launched_at=\$(date --iso-8601=seconds)"
  echo
} | tee -a "$LOG_FILE"
hermes --profile "$PROFILE" chat -q "\$(cat "$PROMPT_FILE")" 2>&1 | tee -a "$LOG_FILE"
status=\${PIPESTATUS[0]}
if [[ "\$status" -ne 0 ]]; then
  state_summary="hermes_exit_nonzero"
  exit "\$status"
fi
state_json="\$(python3 - "$DELIVERY_STATE" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
state = str(data.get('state', data.get('status', 'missing')))
stage = str(data.get('current_stage', 'missing'))
print(json.dumps({'state': state, 'current_stage': stage}, ensure_ascii=False))
PY
)" || {
  status=4
  state_summary="invalid_delivery_state"
  {
    echo
    echo "[stagepilot] terminal_state_check=invalid_delivery_state"
    echo "[stagepilot] delivery_state_path=$DELIVERY_STATE"
    echo "[stagepilot] resume_command=\$resume_command"
  } | tee -a "$LOG_FILE"
  exit "\$status"
}
state="\$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["state"])' "\$state_json")"
stage="\$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["current_stage"])' "\$state_json")"
case "\$state" in
  done)
    state_summary="done:stage=\$stage"
    {
      echo
      echo "[stagepilot] terminal_state_check=done"
      echo "[stagepilot] current_stage=\$stage"
      echo "[stagepilot] delivery_state_path=$DELIVERY_STATE"
    } | tee -a "$LOG_FILE"
    exit 0
    ;;
  blocked)
    state_summary="blocked:stage=\$stage"
    {
      echo
      echo "[stagepilot] terminal_state_check=blocked"
      echo "[stagepilot] current_stage=\$stage"
      echo "[stagepilot] delivery_state_path=$DELIVERY_STATE"
      echo "[stagepilot] attention=runner returned blocked state; lead review required"
    } | tee -a "$LOG_FILE"
    exit 0
    ;;
  archived)
    state_summary="archived:stage=\$stage"
    {
      echo
      echo "[stagepilot] terminal_state_check=archived"
      echo "[stagepilot] current_stage=\$stage"
      echo "[stagepilot] delivery_state_path=$DELIVERY_STATE"
      echo "[stagepilot] attention=root kickoff archived; lead should inspect closure reason"
    } | tee -a "$LOG_FILE"
    exit 0
    ;;
  ready|running|claimed|in_progress)
    status=3
    state_summary="incomplete:\$state:stage=\$stage"
    {
      echo
      echo "[stagepilot] terminal_state_check=incomplete"
      echo "[stagepilot] current_state=\$state"
      echo "[stagepilot] current_stage=\$stage"
      echo "[stagepilot] delivery_state_path=$DELIVERY_STATE"
      echo "[stagepilot] log_file=$LOG_FILE"
      echo "[stagepilot] resume_command=\$resume_command"
    } | tee -a "$LOG_FILE"
    exit "\$status"
    ;;
  *)
    status=4
    state_summary="unknown_state:\$state:stage=\$stage"
    {
      echo
      echo "[stagepilot] terminal_state_check=unknown_state"
      echo "[stagepilot] current_state=\$state"
      echo "[stagepilot] current_stage=\$stage"
      echo "[stagepilot] delivery_state_path=$DELIVERY_STATE"
      echo "[stagepilot] resume_command=\$resume_command"
    } | tee -a "$LOG_FILE"
    exit "\$status"
    ;;
esac
EOF
chmod +x "$RUNNER_SCRIPT"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "error: tmux session already exists: $SESSION_NAME" >&2
  exit 1
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  cat <<EOF
DRY RUN
session_name: $SESSION_NAME
profile: $PROFILE
kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE
workdir: $WORKDIR
prepared_branch_name: ${PREPARED_BRANCH_NAME:-}
log_file: $LOG_FILE
exit_file: $EXIT_FILE
status_file: $STATUS_FILE
tmux_command: tmux new-session -d -s $SESSION_NAME bash $RUNNER_SCRIPT
EOF
  exit 0
fi

tmux new-session -d -s "$SESSION_NAME" bash "$RUNNER_SCRIPT"

cat <<EOF
started: true
background: true
session_name: $SESSION_NAME
profile: $PROFILE
kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE
workdir: $WORKDIR
prepared_branch_name: ${PREPARED_BRANCH_NAME:-}
log_file: $LOG_FILE
exit_file: $EXIT_FILE
status_file: $STATUS_FILE
inspect: tmux capture-pane -pt $SESSION_NAME
attach: tmux attach -t $SESSION_NAME
EOF
