#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/lead-launch-runner.sh [options] <kickoff_artifact> <delivery_state>

Starts Hermes `delivery-runner` in a detached tmux session.

Options:
  --profile NAME        Hermes profile to launch (default: delivery-runner)
  --session-name NAME   tmux session name (default: runner-<kickoff-base>-<timestamp>)
  --log-dir PATH        Log directory (default: ./.stagepilot/runner-logs)
  --workdir PATH        Working directory for the Hermes process (default: repo root)
  --dry-run             Print derived launch values without starting tmux
  -h, --help            Show this help
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
WORKDIR="${WORKDIR:-$REPO_ROOT}"
LOG_DIR="${LOG_DIR:-$REPO_ROOT/.stagepilot/runner-logs}"

KICKOFF_ARTIFACT="$(abspath "${POSITIONAL[0]}")"
DELIVERY_STATE="$(abspath "${POSITIONAL[1]}")"
WORKDIR="$(abspath "$WORKDIR")"
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

if [[ -z "$SESSION_NAME" ]]; then
  kickoff_base="$(basename "$KICKOFF_ARTIFACT")"
  kickoff_base="${kickoff_base%.*}"
  kickoff_base="$(printf '%s' "$kickoff_base" | tr -cs 'A-Za-z0-9._-' '-')"
  timestamp="$(date +%Y%m%d-%H%M%S)"
  SESSION_NAME="runner-${kickoff_base}-${timestamp}"
fi

LOG_FILE="$LOG_DIR/${SESSION_NAME}.log"
EXIT_FILE="$LOG_DIR/${SESSION_NAME}.exit"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stagepilot-runner-${SESSION_NAME}.XXXXXX")"
PROMPT_FILE="$TMP_DIR/prompt.txt"
RUNNER_SCRIPT="$TMP_DIR/run-runner.sh"

cat > "$PROMPT_FILE" <<EOF
Claim and execute this kickoff.

kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE

Instructions:
- Read both files first.
- If the delivery owner target is $PROFILE and the delivery state is ready, claim it by updating the state to claimed or in_progress.
- Write the required acknowledgment with current stage, next artifact, likely blockers, and first execution step.
- Continue orchestration only within approved scope.
- Do not use kanban.
- Keep the artifact/state trail as the source of truth.
EOF

cat > "$RUNNER_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$WORKDIR"
status=0
cleanup() {
  printf '%s\n' "\$status" > "$EXIT_FILE"
}
trap cleanup EXIT
{
  echo "[stagepilot] session=$SESSION_NAME"
  echo "[stagepilot] profile=$PROFILE"
  echo "[stagepilot] kickoff_artifact=$KICKOFF_ARTIFACT"
  echo "[stagepilot] delivery_state=$DELIVERY_STATE"
  echo "[stagepilot] workdir=$WORKDIR"
  echo "[stagepilot] launched_at=\$(date --iso-8601=seconds)"
  echo
} | tee -a "$LOG_FILE"
hermes --profile "$PROFILE" chat -q "\$(cat "$PROMPT_FILE")" 2>&1 | tee -a "$LOG_FILE"
status=\${PIPESTATUS[0]}
exit "\$status"
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
log_file: $LOG_FILE
exit_file: $EXIT_FILE
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
log_file: $LOG_FILE
exit_file: $EXIT_FILE
inspect: tmux capture-pane -pt $SESSION_NAME
attach: tmux attach -t $SESSION_NAME
EOF
