#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/runner-launch-impl.sh [--supervised] [--preset NAME] [--checkpoint-minutes N] [--max-minutes N] [--progress-artifact PATH] [--background] [--session-name NAME] <impl_handoff_artifact> <delivery_state>

Default:
  Foreground bounded worker call using Hermes profile `dev-impl`.

Presets:
  default    checkpoint=10, max=60   Normal supervised bounded work.
  stretched  checkpoint=15, max=90   Slightly longer supervised exception.
  long-run   checkpoint=20, max=120  Explicit long-run supervised exception.

Options:
  --supervised             Run under evidence-based checkpoint supervision.
  --preset NAME            Runtime budget preset: default | stretched | long-run.
  --checkpoint-minutes N   Supervised checkpoint interval in minutes (preset-aware; explicit value overrides preset).
  --max-minutes N          Supervised hard runtime cap in minutes (preset-aware; explicit value overrides preset).
  --progress-artifact PATH Override the progress artifact path used in prompts/supervision.
  --background             Run in detached tmux instead of foreground.
  --session-name NAME      Override tmux session name for background mode.
  -h, --help               Show this help.
EOF
}

background=0
supervised=0
session_name=""
preset_name="default"
checkpoint_minutes=""
max_minutes=""
progress_artifact_override=""
checkpoint_explicit=0
max_explicit=0
args=()

apply_preset() {
  case "$1" in
    default)
      [[ $checkpoint_explicit -eq 1 ]] || checkpoint_minutes="10"
      [[ $max_explicit -eq 1 ]] || max_minutes="60"
      ;;
    stretched)
      [[ $checkpoint_explicit -eq 1 ]] || checkpoint_minutes="15"
      [[ $max_explicit -eq 1 ]] || max_minutes="90"
      ;;
    long-run)
      [[ $checkpoint_explicit -eq 1 ]] || checkpoint_minutes="20"
      [[ $max_explicit -eq 1 ]] || max_minutes="120"
      ;;
    *)
      echo "error: unknown --preset '$1' (expected: default, stretched, long-run)" >&2
      exit 2
      ;;
  esac
}

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
    --preset)
      preset_name=${2:-}
      [[ -n "$preset_name" ]] || { echo "error: --preset requires a value" >&2; exit 2; }
      shift 2
      ;;
    --checkpoint-minutes)
      checkpoint_minutes=${2:-}
      [[ -n "$checkpoint_minutes" ]] || { echo "error: --checkpoint-minutes requires a value" >&2; exit 2; }
      checkpoint_explicit=1
      shift 2
      ;;
    --max-minutes)
      max_minutes=${2:-}
      [[ -n "$max_minutes" ]] || { echo "error: --max-minutes requires a value" >&2; exit 2; }
      max_explicit=1
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

apply_preset "$preset_name"
[[ -n "$checkpoint_minutes" ]] || { echo "error: checkpoint budget unresolved" >&2; exit 2; }
[[ -n "$max_minutes" ]] || { echo "error: max runtime budget unresolved" >&2; exit 2; }

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
worktree_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
impl_handoff=$(realpath "${args[0]}")
delivery_state=$(realpath "${args[1]}")

[[ -f "$impl_handoff" ]] || { echo "error: impl handoff artifact not found: $impl_handoff" >&2; exit 1; }
[[ -f "$delivery_state" ]] || { echo "error: delivery state not found: $delivery_state" >&2; exit 1; }
command -v hermes >/dev/null 2>&1 || { echo "error: hermes not found in PATH" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "error: python3 not found in PATH" >&2; exit 1; }

handoff_id=$(basename "$impl_handoff")
handoff_id=${handoff_id%.*}
supervise_worker="$script_dir/supervise_worker.py"
[[ -f "$supervise_worker" ]] || { echo "error: supervise_worker.py not found next to launcher: $supervise_worker" >&2; exit 1; }
progress_artifact=${progress_artifact_override:-"$worktree_root/.stagepilot/worker-progress/${handoff_id}.md"}
mkdir -p "$(dirname "$progress_artifact")"

prompt=$(cat <<EOF
Execute the implementation handoff as dev-impl.

impl_handoff_artifact: $impl_handoff
delivery_state: $delivery_state
progress_artifact: $progress_artifact

Read both files first.
Stay within the approved scope in the handoff.
Return:
1) changed files
2) commands/checks run
3) evidence paths or evidence summary
4) residual risks or blockers
If blocked, say so explicitly.
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
    python3 "$supervise_worker"
    --label impl
    --workdir "$worktree_root"
    --profile dev-impl
    --handoff-artifact "$impl_handoff"
    --delivery-state "$delivery_state"
    --progress-artifact "$progress_artifact"
    --checkpoint-minutes "$checkpoint_minutes"
    --max-minutes "$max_minutes"
    --
    hermes --profile dev-impl chat -q "$prompt"
  )

  if [[ $background -eq 0 ]]; then
    echo "mode: foreground-supervised"
    echo "profile: dev-impl"
    echo "preset: $preset_name"
    echo "checkpoint_minutes: $checkpoint_minutes"
    echo "max_minutes: $max_minutes"
    echo "impl_handoff_artifact: $impl_handoff"
    echo "delivery_state: $delivery_state"
    echo "progress_artifact: $progress_artifact"
    exec "${supervisor_cmd[@]}"
  fi

  command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found in PATH" >&2; exit 1; }
  mkdir -p "$worktree_root/.stagepilot/worker-logs"
  if [[ -z "$session_name" ]]; then
    session_name="impl-supervised-$(date +%Y%m%d-%H%M%S)"
  fi
  log_file="$worktree_root/.stagepilot/worker-logs/${session_name}.log"
  exit_file="$worktree_root/.stagepilot/worker-logs/${session_name}.exit"
  run_script=$(printf '%q ' "${supervisor_cmd[@]}")
  tmux new-session -d -s "$session_name" "bash -lc $(printf '%q' "$run_script > $(printf '%q' "$log_file") 2>&1; status=$?; printf \"%s\\n\" \"$status\" > $(printf '%q' "$exit_file")")"

  echo "started: true"
  echo "background: true"
  echo "supervised: true"
  echo "session_name: $session_name"
  echo "profile: dev-impl"
  echo "preset: $preset_name"
  echo "checkpoint_minutes: $checkpoint_minutes"
  echo "max_minutes: $max_minutes"
  echo "impl_handoff_artifact: $impl_handoff"
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
  echo "profile: dev-impl"
  echo "preset: $preset_name"
  echo "checkpoint_minutes: $checkpoint_minutes"
  echo "max_minutes: $max_minutes"
  echo "impl_handoff_artifact: $impl_handoff"
  echo "delivery_state: $delivery_state"
  echo "progress_artifact: $progress_artifact"
  exec hermes --profile dev-impl chat -q "$prompt"
fi

command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found in PATH" >&2; exit 1; }
mkdir -p "$worktree_root/.stagepilot/worker-logs"
if [[ -z "$session_name" ]]; then
  session_name="impl-$(date +%Y%m%d-%H%M%S)"
fi
log_file="$worktree_root/.stagepilot/worker-logs/${session_name}.log"
exit_file="$worktree_root/.stagepilot/worker-logs/${session_name}.exit"
run_script=$(printf 'hermes --profile dev-impl chat -q %q > %q 2>&1; status=$?; printf "%%s\\n" "$status" > %q' "$prompt" "$log_file" "$exit_file")
tmux new-session -d -s "$session_name" "bash -lc $(printf '%q' "$run_script")"

echo "started: true"
echo "background: true"
echo "supervised: false"
echo "session_name: $session_name"
echo "profile: dev-impl"
echo "preset: $preset_name"
echo "checkpoint_minutes: $checkpoint_minutes"
echo "max_minutes: $max_minutes"
echo "impl_handoff_artifact: $impl_handoff"
echo "delivery_state: $delivery_state"
echo "progress_artifact: $progress_artifact"
echo "log_file: $log_file"
echo "exit_file: $exit_file"
