#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: check-delivery-capabilities.sh [options]

Options:
  --delivery-profile fast|standard|guarded  Delivery control profile (default: standard)
  --doctor-mode required|optional|not-adopted
                                           Doctor adoption mode (default: not-adopted)
  --worktree-mode auto|required|skip       Worktree intent (default: auto)
  --launch-mode detached|foreground        Runner launch mode (default: detached)
  --publication-mode auto|required|not-required
                                           Publication capability intent (default: auto)
  --allow-fast-degraded                    Permit only documented fast fallbacks
  --json                                   Emit the machine-readable payload (default)
  -h, --help                               Show this help
EOF
}

DELIVERY_PROFILE="standard"
DOCTOR_MODE="not-adopted"
WORKTREE_MODE="auto"
LAUNCH_MODE="detached"
PUBLICATION_MODE="auto"
ALLOW_FAST_DEGRADED=0
CAPABILITY_PATH="${STAGEPILOT_CAPABILITY_PATH:-$PATH}"

capability_command() {
  PATH="$CAPABILITY_PATH" command -v "$1" >/dev/null 2>&1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --delivery-profile) DELIVERY_PROFILE="${2:-}"; shift 2 ;;
    --doctor-mode) DOCTOR_MODE="${2:-}"; shift 2 ;;
    --worktree-mode) WORKTREE_MODE="${2:-}"; shift 2 ;;
    --launch-mode) LAUNCH_MODE="${2:-}"; shift 2 ;;
    --publication-mode) PUBLICATION_MODE="${2:-}"; shift 2 ;;
    --allow-fast-degraded) ALLOW_FAST_DEGRADED=1; shift ;;
    --json) shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

case "$DELIVERY_PROFILE" in fast|standard|guarded) ;; *) echo "error: invalid delivery profile: $DELIVERY_PROFILE" >&2; exit 2 ;; esac
case "$DOCTOR_MODE" in required|optional|not-adopted) ;; *) echo "error: invalid doctor mode: $DOCTOR_MODE" >&2; exit 2 ;; esac
case "$WORKTREE_MODE" in auto|required|skip) ;; *) echo "error: invalid worktree mode: $WORKTREE_MODE" >&2; exit 2 ;; esac
case "$LAUNCH_MODE" in detached|foreground) ;; *) echo "error: invalid launch mode: $LAUNCH_MODE" >&2; exit 2 ;; esac
case "$PUBLICATION_MODE" in auto|required|not-required) ;; *) echo "error: invalid publication mode: $PUBLICATION_MODE" >&2; exit 2 ;; esac

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' '{"status":"blocked","delivery_profile":"'"$DELIVERY_PROFILE"'","required_missing":["python3"],"optional_missing":[],"available_fallbacks":[],"recommended_next_action":"restore_required_capabilities"}'
  exit 2
fi

required_missing=()
optional_missing=()
available_fallbacks=()
notes=()

require_command() {
  local command_name="$1" capability="$2"
  if ! capability_command "$command_name"; then
    required_missing+=("$capability")
  fi
}

optional_command() {
  local command_name="$1" capability="$2" fallback="$3"
  if ! capability_command "$command_name"; then
    optional_missing+=("$capability")
    [[ -n "$fallback" ]] && available_fallbacks+=("$fallback")
  fi
}

require_command hermes hermes
require_command python3 python3

if [[ "$LAUNCH_MODE" == detached ]]; then
  if [[ "$DELIVERY_PROFILE" == fast && "$ALLOW_FAST_DEGRADED" -eq 1 ]]; then
    optional_command tmux tmux foreground_runner_without_tmux
  else
    require_command tmux tmux
  fi
fi

worktree_required=0
case "$WORKTREE_MODE" in
  required) worktree_required=1 ;;
  auto)
    if [[ ! ( "$DELIVERY_PROFILE" == fast && "$ALLOW_FAST_DEGRADED" -eq 1 ) ]]; then
      worktree_required=1
    fi
    ;;
esac

if [[ "$WORKTREE_MODE" != skip ]]; then
  if [[ "$worktree_required" -eq 1 ]]; then
    require_command git git
  else
    optional_command git git current_workdir_without_worktree
  fi
  if capability_command git && ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ "$worktree_required" -eq 1 ]]; then
      required_missing+=(git_repository)
    else
      optional_missing+=(git_repository)
      available_fallbacks+=(current_workdir_without_worktree)
    fi
  fi
fi

case "$DOCTOR_MODE" in
  required) require_command stagepilot-doctor stagepilot_doctor ;;
  optional) optional_command stagepilot-doctor stagepilot_doctor runner_validation_without_doctor ;;
esac

publication_required=0
if [[ "$PUBLICATION_MODE" == required ]]; then
  publication_required=1
fi
if [[ "$publication_required" -eq 1 ]]; then
  require_command gh gh
  require_command git git
  if command -v git >/dev/null 2>&1 && ! git remote get-url origin >/dev/null 2>&1; then
    required_missing+=(publication_origin)
  fi
elif [[ "$PUBLICATION_MODE" == auto ]]; then
  notes+=(publication_preflight_not_requested)
fi

status="ready"
recommended_next_action="continue"
if [[ ${#required_missing[@]} -gt 0 ]]; then
  status="blocked"
  recommended_next_action="restore_required_capabilities"
elif [[ ${#optional_missing[@]} -gt 0 ]]; then
  status="degraded"
  recommended_next_action="select_explicit_fallback_or_restore_capability"
fi

python3 - "$status" "$DELIVERY_PROFILE" "$DOCTOR_MODE" "$WORKTREE_MODE" "$LAUNCH_MODE" "$PUBLICATION_MODE" "$recommended_next_action" "${required_missing[*]:-}" "${optional_missing[*]:-}" "${available_fallbacks[*]:-}" "${notes[*]:-}" <<'PY'
import json
import sys

(
    status,
    profile,
    doctor_mode,
    worktree_mode,
    launch_mode,
    publication_mode,
    next_action,
    required,
    optional,
    fallbacks,
    notes,
) = sys.argv[1:]

split = lambda value: value.split() if value else []
payload = {
    "status": status,
    "delivery_profile": profile,
    "doctor_mode": doctor_mode,
    "worktree_mode": worktree_mode,
    "launch_mode": launch_mode,
    "publication_mode": publication_mode,
    "required_missing": split(required),
    "optional_missing": split(optional),
    "available_fallbacks": split(fallbacks),
    "recommended_next_action": next_action,
    "notes": split(notes),
}
print(json.dumps(payload, sort_keys=True))
PY

[[ "$status" != blocked ]]
