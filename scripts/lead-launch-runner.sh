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
  --delivery-profile NAME  fast | standard | guarded (default: state value or standard)
  --session-name NAME      tmux session name (default: runner-<kickoff-base>-<timestamp>)
  --log-dir PATH           Log directory (default: ./.stagepilot/runner-logs)
  --workdir PATH           Explicit working directory for the Hermes process; skips auto worktree prep
  --base-ref REF           Base ref for auto-prepared delivery branch/worktree (default: main)
  --branch-name NAME       Explicit delivery branch name for auto-prepared worktree
  --worktree-path PATH     Explicit path for auto-prepared worktree
  --skip-worktree          Do not auto-prepare isolated runner worktree
  --allow-fast-degraded    Permit documented fast-only foreground/current-workdir fallback
  --ack-fast-shared-workdir-risk
                           Explicitly accept the exclusive-checkout requirement for a fast
                           current-workdir fallback
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
DELIVERY_PROFILE=""
SESSION_NAME=""
LOG_DIR=""
WORKDIR=""
BASE_REF="main"
BRANCH_NAME=""
WORKTREE_PATH=""
SKIP_WORKTREE=0
ALLOW_FAST_DEGRADED=0
ACK_FAST_SHARED_WORKDIR_RISK=0
DRY_RUN=0
POSITIONAL=()
FAST_SHARED_WORKDIR_LOCK_DIR=""
FAST_SHARED_WORKDIR_LOCK_ROOT="${STAGEPILOT_FAST_SHARED_WORKDIR_LOCK_ROOT:-${TMPDIR:-/tmp}/stagepilot-fast-shared-workdir-locks}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --delivery-profile)
      DELIVERY_PROFILE=${2:-}
      [[ -n "$DELIVERY_PROFILE" ]] || { echo "error: --delivery-profile requires a value" >&2; exit 1; }
      shift 2
      ;;
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
    --allow-fast-degraded)
      ALLOW_FAST_DEGRADED=1
      shift
      ;;
    --ack-fast-shared-workdir-risk)
      ACK_FAST_SHARED_WORKDIR_RISK=1
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: required command not found: python3; cannot persist a JSON delivery blocker state" >&2
  exit 1
fi

KICKOFF_ARTIFACT="$(abspath "${POSITIONAL[0]}")"
DELIVERY_STATE="$(abspath "${POSITIONAL[1]}")"
PRELAUNCH_STATUS_FILE="${DELIVERY_STATE}.launcher-status.json"
LOG_DIR="$(abspath "$LOG_DIR")"

if [[ ! -f "$KICKOFF_ARTIFACT" ]]; then
  echo "error: kickoff artifact not found: $KICKOFF_ARTIFACT" >&2
  exit 1
fi
if [[ ! -f "$DELIVERY_STATE" ]]; then
  echo "error: delivery state not found: $DELIVERY_STATE" >&2
  exit 1
fi
if [[ -z "$DELIVERY_PROFILE" ]]; then
  DELIVERY_PROFILE="$(python3 - "$DELIVERY_STATE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        print(json.load(f).get('delivery_profile') or '')
except Exception:
    print('')
PY
)"
fi
DELIVERY_PROFILE=${DELIVERY_PROFILE:-standard}
case "$DELIVERY_PROFILE" in
  fast|standard|guarded) ;;
  *) echo "error: unknown delivery profile '$DELIVERY_PROFILE' (expected: fast, standard, guarded)" >&2; exit 1 ;;
esac
DOCTOR_MODE="$(python3 - "$DELIVERY_STATE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        print(json.load(f).get('doctor_adoption_mode') or '')
except Exception:
    print('')
PY
)"
DOCTOR_MODE=${DOCTOR_MODE:-not-adopted}
case "$DOCTOR_MODE" in
  required|optional|not-adopted) ;;
  *) echo "error: invalid doctor_adoption_mode '$DOCTOR_MODE' in delivery state" >&2; exit 1 ;;
esac

write_capability_state() {
  local capability_status="$1" fallback_selected="$2" degraded_capabilities="$3"
  local evidence_path="${DELIVERY_STATE}.capability-evidence.json"
  python3 - "$DELIVERY_STATE" "$evidence_path" "$capability_status" "$fallback_selected" "$degraded_capabilities" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, evidence_path, capability_status, fallback_selected, degraded_capabilities = sys.argv[1:]
with open(path, encoding='utf-8') as handle:
    state = json.load(handle)
if not isinstance(state, dict):
    raise SystemExit('delivery state must be a JSON object')
state['capability_status'] = capability_status
existing_fallbacks = state.get('fallbacks_selected', [])
if not isinstance(existing_fallbacks, list):
    existing_fallbacks = []
if fallback_selected:
    state['fallback_selected'] = fallback_selected
    if fallback_selected not in existing_fallbacks:
        existing_fallbacks.append(fallback_selected)
    residual_risk_by_fallback = {
        'foreground_runner_without_tmux': 'fast delivery is not detached or tmux-supervised',
        'current_workdir_without_worktree': 'fast delivery shares the lead checkout; exclusive clean local/reversible scope was explicitly acknowledged',
        'runner_validation_without_doctor': 'runner validation substitutes for unavailable optional stagepilot-doctor',
    }
    risk = residual_risk_by_fallback.get(fallback_selected)
    if risk:
        state['residual_risk'] = risk
        risks = state.get('residual_risk_by_fallback', {})
        if not isinstance(risks, dict):
            risks = {}
        risks[fallback_selected] = risk
        state['residual_risk_by_fallback'] = risks
        waivers = state.get('fallback_waivers', [])
        if not isinstance(waivers, list):
            waivers = []
        waiver = {
            'fallback': fallback_selected,
            'approval': 'delivery-profile policy',
            'residual_risk': risk,
            'evidence_path': evidence_path,
        }
        waivers = [item for item in waivers if not isinstance(item, dict) or item.get('fallback') != fallback_selected]
        waivers.append(waiver)
        state['fallback_waivers'] = waivers
    if fallback_selected == 'current_workdir_without_worktree':
        state['fast_shared_workdir_risk_acknowledged'] = True
if existing_fallbacks:
    state['fallbacks_selected'] = existing_fallbacks
existing_degraded = state.get('degraded_capabilities', [])
if not isinstance(existing_degraded, list):
    existing_degraded = []
for capability in filter(None, degraded_capabilities.split(',')):
    if capability not in existing_degraded:
        existing_degraded.append(capability)
if existing_degraded:
    state['degraded_capabilities'] = existing_degraded
if 'stagepilot_doctor' in existing_degraded:
    debts = state.get('tooling_debts', [])
    if not isinstance(debts, list):
        debts = []
    debt = {
        'code': 'stagepilot_doctor_optional_missing',
        'fallback_validation': 'runner_validation_without_doctor',
    }
    if debt not in debts:
        debts.append(debt)
    state['tooling_debts'] = debts
state['updated_at'] = datetime.now(timezone.utc).isoformat()
state['capability_evidence_path'] = evidence_path
with open(path, 'w', encoding='utf-8') as handle:
    json.dump(state, handle, indent=2, sort_keys=True)
    handle.write('\n')
evidence = {
    'schema_version': 1,
    'delivery_state': path,
    'capability_status': state.get('capability_status'),
    'fallbacks_selected': state.get('fallbacks_selected', []),
    'fallback_waivers': state.get('fallback_waivers', []),
}
with open(evidence_path, 'w', encoding='utf-8') as handle:
    json.dump(evidence, handle, indent=2, sort_keys=True)
    handle.write('\n')
PY
}

write_blocked_state() {
  local blocker_detail="$1"
  python3 - "$DELIVERY_STATE" "$PRELAUNCH_STATUS_FILE" "$blocker_detail" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, status_path, detail = sys.argv[1:]
blocker_codes = {
    'hermes_not_found': 'hermes_profile_unavailable',
    'hermes_profile_unavailable': 'hermes_profile_unavailable',
    'tmux_unavailable': 'tmux_unavailable',
    'git_not_found': 'git_worktree_prepare_failed',
    'prepare_worktree_helper_unavailable': 'git_worktree_prepare_failed',
    'git_worktree_prepare_failed': 'git_worktree_prepare_failed',
    'worktree_isolation_bypassed': 'worktree_isolation_bypassed',
    'fast_shared_workdir_risk_unacknowledged': 'fast_shared_workdir_risk_unacknowledged',
    'fast_shared_workdir_not_clean': 'fast_shared_workdir_not_clean',
    'fast_shared_workdir_in_use': 'fast_shared_workdir_in_use',
    'doctor_unavailable': 'stagepilot_doctor_required_missing',
}
blocker_code = blocker_codes.get(detail, 'launcher_prerequisite_missing')
timestamp = datetime.now(timezone.utc).isoformat()
launcher_status = {
    'classification': blocker_code,
    'detail': detail,
    'phase': 'prelaunch',
    'status': 'blocked',
    'updated_at': timestamp,
}
with open(path, encoding='utf-8') as handle:
    state = json.load(handle)
if not isinstance(state, dict):
    raise SystemExit('delivery state must be a JSON object')
state.update({
    'status': 'blocked',
    'state': 'blocked',
    'current_stage': 'kickoff',
    'reason_class': 'tooling_or_access_blocker',
    'blocker_code': blocker_code,
    'blocker_detail': detail,
    'capability_status': 'blocked',
    'launcher_status': launcher_status,
    'launcher_status_file': status_path,
    'updated_at': timestamp,
})
with open(path, 'w', encoding='utf-8') as handle:
    json.dump(state, handle, indent=2, sort_keys=True)
    handle.write('\n')
with open(status_path, 'w', encoding='utf-8') as handle:
    json.dump(launcher_status, handle, indent=2, sort_keys=True)
    handle.write('\n')
PY
}

fail_blocked() {
  local detail="$1" message="$2"
  echo "error: $message" >&2
  if ! write_blocked_state "$detail"; then
    echo "error: additionally failed to persist delivery blocker state" >&2
  fi
  exit 1
}

require_fast_shared_workdir_ack() {
  local shared_workdir="${1:-$DEFAULT_ROOT_WORKDIR}"
  if [[ "$DELIVERY_PROFILE" != fast || "$ALLOW_FAST_DEGRADED" -ne 1 || "$ACK_FAST_SHARED_WORKDIR_RISK" -ne 1 ]]; then
    fail_blocked fast_shared_workdir_risk_unacknowledged \
      "current-workdir fallback requires fast --allow-fast-degraded and --ack-fast-shared-workdir-risk"
  fi
  if command -v git >/dev/null 2>&1 && git -C "$shared_workdir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ -n "$(git -C "$shared_workdir" status --porcelain)" ]]; then
      fail_blocked fast_shared_workdir_not_clean \
        "current-workdir fallback refused because the checkout has uncommitted changes"
    fi
  fi
}

release_fast_shared_workdir_lock() {
  if [[ -n "$FAST_SHARED_WORKDIR_LOCK_DIR" ]]; then
    rm -f "$FAST_SHARED_WORKDIR_LOCK_DIR/owner.pid" 2>/dev/null || true
    rmdir "$FAST_SHARED_WORKDIR_LOCK_DIR" 2>/dev/null || true
    FAST_SHARED_WORKDIR_LOCK_DIR=""
  fi
}

acquire_fast_shared_workdir_lock() {
  local shared_workdir="$1" lock_key owner_pid
  lock_key="$(python3 - "$shared_workdir" <<'PY'
import hashlib
import sys
print(hashlib.sha256(sys.argv[1].encode()).hexdigest())
PY
)"
  FAST_SHARED_WORKDIR_LOCK_DIR="$FAST_SHARED_WORKDIR_LOCK_ROOT/$lock_key"
  if ! mkdir -p "$FAST_SHARED_WORKDIR_LOCK_ROOT"; then
    FAST_SHARED_WORKDIR_LOCK_DIR=""
    fail_blocked fast_shared_workdir_in_use "could not establish the fast shared-workdir ownership lock"
  fi
  if ! mkdir "$FAST_SHARED_WORKDIR_LOCK_DIR"; then
    owner_pid="$(cat "$FAST_SHARED_WORKDIR_LOCK_DIR/owner.pid" 2>/dev/null || true)"
    if [[ "$owner_pid" =~ ^[0-9]+$ ]] && ! kill -0 "$owner_pid" 2>/dev/null; then
      rm -f "$FAST_SHARED_WORKDIR_LOCK_DIR/owner.pid" 2>/dev/null || true
      rmdir "$FAST_SHARED_WORKDIR_LOCK_DIR" 2>/dev/null || true
    fi
    if ! mkdir "$FAST_SHARED_WORKDIR_LOCK_DIR"; then
      FAST_SHARED_WORKDIR_LOCK_DIR=""
      fail_blocked fast_shared_workdir_in_use \
        "current-workdir fallback refused because another fast delivery may own the shared checkout"
    fi
  fi
  if ! printf '%s\n' "$$" > "$FAST_SHARED_WORKDIR_LOCK_DIR/owner.pid"; then
    release_fast_shared_workdir_lock
    fail_blocked fast_shared_workdir_in_use "could not persist the fast shared-workdir ownership lock"
  fi
  trap release_fast_shared_workdir_lock EXIT
}

use_fast_worktree_fallback() {
  local detail="$1" message="$2"
  if [[ "$DELIVERY_PROFILE" == fast && "$ALLOW_FAST_DEGRADED" -eq 1 ]]; then
    require_fast_shared_workdir_ack
    acquire_fast_shared_workdir_lock "$DEFAULT_ROOT_WORKDIR"
    echo "warning: $message; continuing in current workdir only because fast degraded mode was explicitly approved" >&2
    WORKDIR="$DEFAULT_ROOT_WORKDIR"
    LAUNCH_MODE="foreground"
    write_capability_state degraded current_workdir_without_worktree "$detail"
    return 0
  fi
  return 1
}

if ! command -v hermes >/dev/null 2>&1; then
  fail_blocked hermes_not_found "required command not found: hermes"
fi
if ! hermes --profile "$PROFILE" profile show "$PROFILE" >/dev/null 2>&1; then
  fail_blocked hermes_profile_unavailable "selected Hermes profile is unavailable"
fi
case "$DOCTOR_MODE" in
  required)
    if ! command -v stagepilot-doctor >/dev/null 2>&1; then
      fail_blocked doctor_unavailable "required doctor command not found: stagepilot-doctor"
    fi
    ;;
  optional)
    if ! command -v stagepilot-doctor >/dev/null 2>&1; then
      write_capability_state degraded runner_validation_without_doctor stagepilot_doctor
    fi
    ;;
esac
if ! command -v tmux >/dev/null 2>&1; then
  if [[ "$DELIVERY_PROFILE" == fast && "$ALLOW_FAST_DEGRADED" -eq 1 ]]; then
    LAUNCH_MODE="foreground"
    write_capability_state degraded foreground_runner_without_tmux tmux
  else
    fail_blocked tmux_unavailable "required command not found: tmux"
  fi
else
  LAUNCH_MODE="detached"
fi

PREPARED_WORKTREE_PATH=""
PREPARED_BRANCH_NAME=""
if [[ -n "$WORKDIR" ]]; then
  WORKDIR="$(abspath "$WORKDIR")"
  case "$DELIVERY_PROFILE" in
    guarded|standard)
      fail_blocked worktree_isolation_bypassed \
        "$DELIVERY_PROFILE delivery cannot bypass isolated worktree preparation with --workdir"
      ;;
    fast)
      require_fast_shared_workdir_ack "$WORKDIR"
      acquire_fast_shared_workdir_lock "$WORKDIR"
      LAUNCH_MODE="foreground"
      write_capability_state degraded current_workdir_without_worktree worktree
      ;;
  esac
elif [[ "$SKIP_WORKTREE" -eq 1 ]]; then
  if [[ "$DELIVERY_PROFILE" == guarded || "$DELIVERY_PROFILE" == standard ]]; then
    fail_blocked worktree_isolation_bypassed "$DELIVERY_PROFILE delivery cannot skip isolated worktree preparation"
  fi
  if [[ "$DELIVERY_PROFILE" == fast ]]; then
    require_fast_shared_workdir_ack "$DEFAULT_ROOT_WORKDIR"
    acquire_fast_shared_workdir_lock "$DEFAULT_ROOT_WORKDIR"
    LAUNCH_MODE="foreground"
    write_capability_state degraded current_workdir_without_worktree worktree
  fi
  WORKDIR="$DEFAULT_ROOT_WORKDIR"
else
  if ! command -v git >/dev/null 2>&1; then
    use_fast_worktree_fallback git_not_found "required command not found: git" || fail_blocked git_not_found "required command not found: git"
  elif [[ ! -x "$PREPARE_WORKTREE_SCRIPT" ]]; then
    use_fast_worktree_fallback prepare_worktree_helper_unavailable "helper script not executable: $PREPARE_WORKTREE_SCRIPT" || fail_blocked prepare_worktree_helper_unavailable "helper script not executable: $PREPARE_WORKTREE_SCRIPT"
  else
    TARGET_REPO_ROOT="$(python3 - "$DELIVERY_STATE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('repo') or '')
except Exception:
    print('')
PY
)"
    if [[ -z "$TARGET_REPO_ROOT" ]]; then
      TARGET_REPO_ROOT="$(pwd)"
    fi
    prep_args=("$KICKOFF_ARTIFACT" "$DELIVERY_STATE" --repo-root "$TARGET_REPO_ROOT" --base-ref "$BASE_REF")
    if [[ -n "$BRANCH_NAME" ]]; then prep_args+=(--branch-name "$BRANCH_NAME"); fi
    if [[ -n "$WORKTREE_PATH" ]]; then prep_args+=(--worktree-path "$WORKTREE_PATH"); fi
    if [[ "$DRY_RUN" -eq 1 ]]; then prep_args+=(--dry-run); fi
    if ! prep_output="$($PREPARE_WORKTREE_SCRIPT "${prep_args[@]}")"; then
      use_fast_worktree_fallback git_worktree_prepare_failed "delivery worktree preparation failed" || fail_blocked git_worktree_prepare_failed "delivery worktree preparation failed"
    else
      PREPARED_WORKTREE_PATH="$(printf '%s\n' "$prep_output" | awk -F': ' '/^worktree_path:/ {print $2}')"
      PREPARED_BRANCH_NAME="$(printf '%s\n' "$prep_output" | awk -F': ' '/^branch_name:/ {print $2}')"
      if [[ -z "$PREPARED_WORKTREE_PATH" ]]; then
        use_fast_worktree_fallback git_worktree_prepare_failed "failed to derive worktree path from prepare-runner-worktree output" || fail_blocked git_worktree_prepare_failed "failed to derive worktree path from prepare-runner-worktree output"
      else
        WORKDIR="$PREPARED_WORKTREE_PATH"
      fi
    fi
  fi
fi
WORKDIR="$(abspath "$WORKDIR")"

if [[ -z "$SESSION_NAME" ]]; then
  kickoff_base="$(basename "$KICKOFF_ARTIFACT")"
  kickoff_base="${kickoff_base%.*}"
  kickoff_base="$(printf '%s' "$kickoff_base" | tr -cs 'A-Za-z0-9._-' '-')"
  timestamp="$(date +%Y%m%d-%H%M%S)"
  SESSION_NAME="runner-${kickoff_base}-${timestamp}"
fi

if ! mkdir -p "$LOG_DIR"; then
  fail_blocked launcher_runtime_prepare_failed "failed to create launcher log directory"
fi
LOG_FILE="$LOG_DIR/${SESSION_NAME}.log"
EXIT_FILE="$LOG_DIR/${SESSION_NAME}.exit"
STATUS_FILE="$LOG_DIR/${SESSION_NAME}.status"
if ! TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stagepilot-runner-${SESSION_NAME}.XXXXXX")"; then
  fail_blocked launcher_runtime_prepare_failed "failed to create launcher temporary directory"
fi
PROMPT_FILE="$TMP_DIR/prompt.txt"
RUNNER_SCRIPT="$TMP_DIR/run-runner.sh"
IMPL_LAUNCHER="$SCRIPT_DIR/runner-launch-impl.sh"
QC_LAUNCHER="$SCRIPT_DIR/runner-launch-qc.sh"
PUBLICATION_PREFLIGHT="$SCRIPT_DIR/check-publication-auth.sh"
if [[ "$DELIVERY_PROFILE" == "guarded" ]]; then
  PREFLIGHT_INSTRUCTION="- For PR-bound guarded delivery, run publication auth preflight before substantial impl/QC effort and record the outcome in the delivery trail:
  - publication_preflight: $PUBLICATION_PREFLIGHT --json
  - minimum checks: git remote get-url origin, gh auth status, git ls-remote origin, git push --dry-run origin HEAD:refs/heads/<current-branch>
  - if preflight fails, stop early, reflect a blocked/escalation trail entry, and classify it with reason code publication_auth_missing (or a more specific suffix from the helper output)."
elif [[ "$DELIVERY_PROFILE" == "fast" ]]; then
  PREFLIGHT_INSTRUCTION="- This is a local-only fast delivery. Do not create a PR, push, release, or perform other publication actions. If publication or release-sensitive work enters scope, stop and escalate to standard or guarded."
else
  PREFLIGHT_INSTRUCTION="- Do not run publication preflight unless publication becomes part of the approved standard-delivery scope. Escalate to guarded for PR publication or release-sensitive risk."
fi

cat > "$PROMPT_FILE" <<EOF
Claim and execute this kickoff.

kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE
delivery_profile: $DELIVERY_PROFILE
doctor_adoption_mode: $DOCTOR_MODE

Instructions:
- Read both files first.
- Operate inside the current working directory; it is the delivery-isolated repo checkout for this kickoff unless the lead explicitly overrode it.
- If the delivery owner target is $PROFILE and the delivery state is ready, claim it by updating the state to canonical running. If you encounter legacy claimed or in_progress values, normalize them to running on the next write.
- Write the required acknowledgment with current stage, next artifact, likely blockers, and first execution step.
- Keep all delivery-branch code, tests, commits, and PR work inside the current isolated worktree.
- Do not pull unapproved live Discovery/REQ edits from the lead checkout into the delivery branch automatically; require explicit lead re-handoff or sync direction.
- Continue orchestration only within approved scope.
- Enforce the declared delivery_profile and normalize a missing/legacy state field to it on the next state write:
  - fast: only a small local low-risk change; launch impl foreground without supervision, do not launch QC, and record targeted validation plus the QC waiver reason/residual risk in root state.
  - standard: use normal handoffs, but require QC/supervision only when risk triggers apply; record any waiver structurally in root state.
  - guarded: retain isolated worktree, publication preflight, supervised impl and supervised independent QC.
$PREFLIGHT_INSTRUCTION
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

if [[ "$LAUNCH_MODE" == detached ]] && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  fail_blocked tmux_session_name_conflict "tmux session already exists: $SESSION_NAME"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  cat <<EOF
DRY RUN
session_name: $SESSION_NAME
profile: $PROFILE
delivery_profile: $DELIVERY_PROFILE
launch_mode: $LAUNCH_MODE
kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE
workdir: $WORKDIR
prepared_branch_name: ${PREPARED_BRANCH_NAME:-}
log_file: $LOG_FILE
exit_file: $EXIT_FILE
status_file: $STATUS_FILE
launch_command: $([[ "$LAUNCH_MODE" == detached ]] && printf 'tmux new-session -d -s %s bash %s' "$SESSION_NAME" "$RUNNER_SCRIPT" || printf 'bash %s' "$RUNNER_SCRIPT")
EOF
  exit 0
fi

if [[ "$LAUNCH_MODE" == foreground ]]; then
  cat <<EOF
started: true
background: false
launch_mode: foreground
session_name: $SESSION_NAME
profile: $PROFILE
delivery_profile: $DELIVERY_PROFILE
kickoff_artifact: $KICKOFF_ARTIFACT
delivery_state: $DELIVERY_STATE
workdir: $WORKDIR
prepared_branch_name: ${PREPARED_BRANCH_NAME:-}
log_file: $LOG_FILE
exit_file: $EXIT_FILE
status_file: $STATUS_FILE
EOF
  bash "$RUNNER_SCRIPT"
  exit $?
fi

tmux new-session -d -s "$SESSION_NAME" bash "$RUNNER_SCRIPT"

cat <<EOF
started: true
background: true
launch_mode: detached
session_name: $SESSION_NAME
profile: $PROFILE
delivery_profile: $DELIVERY_PROFILE
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
