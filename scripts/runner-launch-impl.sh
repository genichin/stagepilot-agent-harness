#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/runner-launch-impl.sh [--background] [--session-name NAME] <impl_handoff_artifact> <delivery_state>

Default:
  Foreground bounded worker call using Hermes profile `dev-impl`.

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

impl_handoff=$(realpath "${args[0]}")
delivery_state=$(realpath "${args[1]}")

[[ -f "$impl_handoff" ]] || { echo "error: impl handoff artifact not found: $impl_handoff" >&2; exit 1; }
[[ -f "$delivery_state" ]] || { echo "error: delivery state not found: $delivery_state" >&2; exit 1; }
command -v hermes >/dev/null 2>&1 || { echo "error: hermes not found in PATH" >&2; exit 1; }

prompt=$(cat <<EOF
Execute the implementation handoff as dev-impl.

impl_handoff_artifact: $impl_handoff
delivery_state: $delivery_state

Read both files first.
Stay within the approved scope in the handoff.
Return:
1) changed files
2) commands/checks run
3) evidence paths or evidence summary
4) residual risks or blockers
If blocked, say so explicitly.
Do not use kanban.
EOF
)

if [[ $background -eq 0 ]]; then
  echo "mode: foreground"
  echo "profile: dev-impl"
  echo "impl_handoff_artifact: $impl_handoff"
  echo "delivery_state: $delivery_state"
  exec hermes --profile dev-impl chat -q "$prompt"
fi

command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found in PATH" >&2; exit 1; }
mkdir -p .stagepilot/worker-logs
if [[ -z "$session_name" ]]; then
  session_name="impl-$(date +%Y%m%d-%H%M%S)"
fi
log_file="$(pwd)/.stagepilot/worker-logs/${session_name}.log"
exit_file="$(pwd)/.stagepilot/worker-logs/${session_name}.exit"
run_script=$(printf 'hermes --profile dev-impl chat -q %q > %q 2>&1; status=$?; printf "%%s\\n" "$status" > %q' "$prompt" "$log_file" "$exit_file")
tmux new-session -d -s "$session_name" "bash -lc $(printf '%q' "$run_script")"

echo "started: true"
echo "background: true"
echo "session_name: $session_name"
echo "profile: dev-impl"
echo "impl_handoff_artifact: $impl_handoff"
echo "delivery_state: $delivery_state"
echo "log_file: $log_file"
echo "exit_file: $exit_file"
