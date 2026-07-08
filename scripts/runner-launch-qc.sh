#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/runner-launch-qc.sh [--background] [--session-name NAME] <qc_handoff_artifact> <delivery_state>

Default:
  Foreground bounded worker call using Hermes profile `dev-qc`.

Options:
  --background          Run in detached tmux instead of foreground.
  --session-name NAME   Override tmux session name for background mode.
  -h, --help            Show this help.
EOF
}

background=0
session_name=""
args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --background)
      background=1
      shift
      ;;
    --session-name)
      session_name=${2:-}
      if [[ -z "$session_name" ]]; then
        echo "error: --session-name requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do args+=("$1"); shift; done
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

if [[ ${#args[@]} -ne 2 ]]; then
  usage >&2
  exit 2
fi

qc_handoff=$(realpath "${args[0]}")
delivery_state=$(realpath "${args[1]}")

[[ -f "$qc_handoff" ]] || { echo "error: qc handoff artifact not found: $qc_handoff" >&2; exit 1; }
[[ -f "$delivery_state" ]] || { echo "error: delivery state not found: $delivery_state" >&2; exit 1; }
command -v hermes >/dev/null 2>&1 || { echo "error: hermes not found in PATH" >&2; exit 1; }

prompt=$(cat <<EOF
Execute the QC handoff as dev-qc.

qc_handoff_artifact: $qc_handoff
delivery_state: $delivery_state

Read both files first.
Return:
1) verdict
2) evidence reviewed
3) uncovered gaps
4) required follow-up
5) verdict count for the same acceptance scope if repeated
If the issue is governance ambiguity, say it requires lead escalation.
Do not use kanban.
EOF
)

if [[ $background -eq 0 ]]; then
  echo "mode: foreground"
  echo "profile: dev-qc"
  echo "qc_handoff_artifact: $qc_handoff"
  echo "delivery_state: $delivery_state"
  exec hermes --profile dev-qc chat -q "$prompt"
fi

command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found in PATH" >&2; exit 1; }
mkdir -p .stagepilot/worker-logs
if [[ -z "$session_name" ]]; then
  session_name="qc-$(date +%Y%m%d-%H%M%S)"
fi
log_file="$(pwd)/.stagepilot/worker-logs/${session_name}.log"
exit_file="$(pwd)/.stagepilot/worker-logs/${session_name}.exit"
run_script=$(printf 'hermes --profile dev-qc chat -q %q > %q 2>&1; status=$?; printf "%%s\\n" "$status" > %q' "$prompt" "$log_file" "$exit_file")
tmux new-session -d -s "$session_name" "bash -lc $(printf '%q' "$run_script")"

echo "started: true"
echo "background: true"
echo "session_name: $session_name"
echo "profile: dev-qc"
echo "qc_handoff_artifact: $qc_handoff"
echo "delivery_state: $delivery_state"
echo "log_file: $log_file"
echo "exit_file: $exit_file"
