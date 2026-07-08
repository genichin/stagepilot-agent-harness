#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/runner-launch-qc.sh [--supervised] [--checkpoint-minutes N] [--max-minutes N] [--progress-artifact PATH] [--background] [--session-name NAME] <qc_handoff_artifact> <delivery_state>

Default:
  Foreground bounded worker call using Hermes profile `dev-qc`.

Options:
  --supervised             Run under evidence-based checkpoint supervision.
  --checkpoint-minutes N   Supervised checkpoint interval in minutes (default: 10).
  --max-minutes N          Supervised hard runtime cap in minutes (default: 60).
  --progress-artifact PATH Override the progress artifact path used in prompts/supervision.
  --background             Run in detached tmux instead of foreground.
  --session-name NAME      Override tmux session name for background mode.
  -h, --help               Show this help.
EOF
}

background=0
supervised=0
session_name=""
checkpoint_minutes="10"
max_minutes="60"
progress_artifact_override=""
args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --background)
      background=1
      shift
      ;;
    --supervised)
      supervised=1
      shift
      ;;
    --checkpoint-minutes)
      checkpoint_minutes=${2:-}
      [[ -n "$checkpoint_minutes" ]] || { echo "error: --checkpoint-minutes requires a value" >&2; exit 2; }
      shift 2
      ;;
    --max-minutes)
      max_minutes=${2:-}
      [[ -n "$max_minutes" ]] || { echo "error: --max-minutes requires a value" >&2; exit 2; }
      shift 2
      ;;
    --progress-artifact)
      progress_artifact_override=${2:-}
      [[ -n "$progress_artifact_override" ]] || { echo "error: --progress-artifact requires a value" >&2; exit 2; }
      shift 2
      ;;
    --session-name)
      session_name=${2:-}
      [[ -n "$session_name" ]] || { echo "error: --session-name requires a value" >&2; exit 2; }
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

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
qc_handoff=$(realpath "${args[0]}")
delivery_state=$(realpath "${args[1]}")

[[ -f "$qc_handoff" ]] || { echo "error: qc handoff artifact not found: $qc_handoff" >&2; exit 1; }
[[ -f "$delivery_state" ]] || { echo "error: delivery state not found: $delivery_state" >&2; exit 1; }
command -v hermes >/dev/null 2>&1 || { echo "error: hermes not found in PATH" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "error: python3 not found in PATH" >&2; exit 1; }

handoff_id=$(basename "$qc_handoff")
handoff_id=${handoff_id%.*}
progress_artifact=${progress_artifact_override:-"$repo_root/.stagepilot/worker-progress/${handoff_id}.md"}
mkdir -p "$(dirname "$progress_artifact")"

prompt=$(cat <<EOF
Execute the QC handoff as dev-qc.

qc_handoff_artifact: $qc_handoff
delivery_state: $delivery_state
progress_artifact: $progress_artifact

Read both files first.
Return:
1) verdict
2) evidence reviewed
3) uncovered gaps
4) required follow-up
5) verdict count for the same acceptance scope if repeated
If the issue is governance ambiguity, say it requires lead escalation.
If you cannot complete within the first checkpoint window, update the progress artifact at:
$progress_artifact
Required progress fields:
- current step
- files inspected
- files modified
- design/implementation decisions made
- commands/checks run
- current blocker, if any
- next concrete step
Heartbeat-only messages do not count as progress.
Do not use kanban.
EOF
)

run_supervised() {
  local -a supervisor_cmd=(
    python3 "$repo_root/scripts/supervise_worker.py"
    --label qc
    --workdir "$repo_root"
    --profile dev-qc
    --handoff-artifact "$qc_handoff"
    --delivery-state "$delivery_state"
    --progress-artifact "$progress_artifact"
    --checkpoint-minutes "$checkpoint_minutes"
    --max-minutes "$max_minutes"
    --
    hermes --profile dev-qc chat -q "$prompt"
  )

  if [[ $background -eq 0 ]]; then
    echo "mode: foreground-supervised"
    echo "profile: dev-qc"
    echo "qc_handoff_artifact: $qc_handoff"
    echo "delivery_state: $delivery_state"
    echo "progress_artifact: $progress_artifact"
    exec "${supervisor_cmd[@]}"
  fi

  command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found in PATH" >&2; exit 1; }
  mkdir -p "$repo_root/.stagepilot/worker-logs"
  if [[ -z "$session_name" ]]; then
    session_name="qc-supervised-$(date +%Y%m%d-%H%M%S)"
  fi
  log_file="$repo_root/.stagepilot/worker-logs/${session_name}.log"
  exit_file="$repo_root/.stagepilot/worker-logs/${session_name}.exit"
  run_script=$(printf '%q ' "${supervisor_cmd[@]}")
  tmux new-session -d -s "$session_name" "bash -lc $(printf '%q' "$run_script > $(printf '%q' "$log_file") 2>&1; status=$?; printf \"%s\\n\" \"$status\" > $(printf '%q' "$exit_file")")"

  echo "started: true"
  echo "background: true"
  echo "supervised: true"
  echo "session_name: $session_name"
  echo "profile: dev-qc"
  echo "qc_handoff_artifact: $qc_handoff"
  echo "delivery_state: $delivery_state"
  echo "progress_artifact: $progress_artifact"
  echo "log_file: $log_file"
  echo "exit_file: $exit_file"
}

if [[ $supervised -eq 1 ]]; then
  run_supervised
fi

if [[ $background -eq 0 ]]; then
  echo "mode: foreground"
  echo "profile: dev-qc"
  echo "qc_handoff_artifact: $qc_handoff"
  echo "delivery_state: $delivery_state"
  echo "progress_artifact: $progress_artifact"
  exec hermes --profile dev-qc chat -q "$prompt"
fi

command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found in PATH" >&2; exit 1; }
mkdir -p "$repo_root/.stagepilot/worker-logs"
if [[ -z "$session_name" ]]; then
  session_name="qc-$(date +%Y%m%d-%H%M%S)"
fi
log_file="$repo_root/.stagepilot/worker-logs/${session_name}.log"
exit_file="$repo_root/.stagepilot/worker-logs/${session_name}.exit"
run_script=$(printf 'hermes --profile dev-qc chat -q %q > %q 2>&1; status=$?; printf "%%s\\n" "$status" > %q' "$prompt" "$log_file" "$exit_file")
tmux new-session -d -s "$session_name" "bash -lc $(printf '%q' "$run_script")"

echo "started: true"
echo "background: true"
echo "supervised: false"
echo "session_name: $session_name"
echo "profile: dev-qc"
echo "qc_handoff_artifact: $qc_handoff"
echo "delivery_state: $delivery_state"
echo "progress_artifact: $progress_artifact"
echo "log_file: $log_file"
echo "exit_file: $exit_file"
