# State Machine

## Canonical task states

- `todo`
- `ready`
- `running`
- `blocked`
- `done`
- `archived`

## Semantics

### ready
The task/card exists, routing is complete, and the intended owner can now claim it. For `lead -> delivery-runner` kickoff cards, `ready` means the lead has emitted the handoff but the runner has not yet accepted execution ownership.

When a `delivery-runner` already has another root kickoff item in active execution anywhere, additional root kickoff items normally remain in `ready` as queued work rather than being auto-claimed.

### running
The assigned worker has actively claimed the task/card and started execution. For `lead -> delivery-runner` kickoff cards, `running` means the runner is the explicit assignee/owner and has posted the initial orchestration acknowledgment.

Legacy aliases `claimed` and `in_progress` should be interpreted as `running` when reading older records, but new writes should normalize to `running`.

### blocked
A worker cannot proceed without an external dependency, approval, or clarified decision.

### done
The assigned unit of work has completed its expected execution path and produced evidence. For a `lead -> delivery-runner` root kickoff item, `done` is the required successful completion signal that returns active ownership to the lead for release-stage review.

### archived
The task is closed for active routing and retained only for history.

For a `lead -> delivery-runner` root kickoff item, `archived` is a valid terminal closure only when the kickoff should no longer continue as active delivery work, for example because it was superseded, withdrawn, or intentionally closed without further execution. It is not the normal successful delivery completion signal; that remains `done`.

## Root delivery-state record schema

The root delivery-state record is the canonical machine-readable status artifact for an active kickoff. Optional chat notifications may mirror it, but they do not replace it.

### Required fields

- `status`: canonical task state (`ready`, `running`, `blocked`, `done`, `archived`)
- `current_stage`: current delivery stage label such as `kickoff`, `impl-running`, `qc-review`, `lead-escalation`, `merge-ready`, or `closed`
- `owner_target`: intended active owner (`delivery-runner`, `dev-impl`, `dev-qc`, or `lead` depending on the moment)
- `goal`: short current delivery goal for the active root kickoff
- `kickoff_artifact`: path to the persisted root kickoff artifact
- `delivery_profile`: `fast`, `standard`, or `guarded`; new records must write it; legacy/missing records default to `standard`. See [Delivery profiles](delivery-profiles.md).
- `updated_at`: timestamp of the latest authoritative write

### Strongly recommended fields

- `root_type`: `req`, `batch`, or `discovery`; use `discovery` when the kickoff is a confirmed Discovery root that owns a batch queue
- `discovery_id`: required when `root_type=discovery`
- `approved_refs`: approved Discovery / REQ references anchoring scope; a launched root must include its exact bound `REQ@revision`
- `scope_snapshot`: relative JSON snapshot path next to the root state; required before `lead-launch-runner.sh` can launch
- `scope_revision`: positive approved revision matching the snapshot; required before launch
- `scope_snapshot_sha256`: SHA-256 of the exact snapshot bytes; required before launch
- `scope_summary`: short scope statement for this kickoff
- `current_handoff_artifact`: currently active impl/QC/escalation/completion artifact path when one exists
- `lifecycle_claims`: accepted, relative claim artifacts for release/deployment/milestone decisions; each binds the exact control-plane snapshot SHA-256
- `blocker_code`: machine-readable blocker code when `status=blocked`
- `blocker_detail`: subtype / precise reason when needed, for example `gh_auth_status_failed`, `push_dry_run_failed`, or `read_loop_no_diff`
- `evidence_paths`: artifact or evidence paths relevant to the current state
- `next_action`: expected next orchestration action such as `launch_impl`, `launch_qc`, `rework_impl`, `escalate_to_lead`, or `lead_merge_review`
- `pr_ref`: primary PR URL/number/branch note for the kickoff when applicable
- `implemented_reqs`: REQs from the root Discovery already synchronized to `Implemented`
- `remaining_approved_reqs`: Approved REQs still needing delivery under the root Discovery
- `batch_queue`: queue items or path to `batch-queue.json` for Discovery-level roots
- `current_batch`: active batch id/path when a Discovery-level root is executing a queue
- `completed_batches`: completed batch ids/paths for Discovery-level roots
- `verdict_count_for_scope`: QC verdict count for the same acceptance scope when QC looping is active
- `validation_commands`, `qc_waiver_reason`, `residual_risk`: required evidence/waiver fields when `fast`, and required for a `standard` QC waiver
- `doctor_adoption_mode`: `required`, `optional`, or `not-adopted`; the root state is authoritative and an overlay may supply this value only when the state is created
- `capability_status`: `ready`, `degraded`, or `blocked` when launch capability discovery was run
- `required_missing`, `optional_missing`: safe capability names from the launch preflight; never include credential values or raw authentication output
- `fallbacks_selected`, `degraded_capabilities`: every explicit approved fallback and its affected capabilities when execution continues in degraded mode
- `fallback_waivers`, `residual_risk_by_fallback`, `capability_evidence_path`: explicit fallback approval/policy, per-fallback residual risk, and the adjacent capability-evidence artifact path; values must not include credentials, remote URLs, or raw command output
- `tooling_debts`: optional non-blocking tooling debt objects, including code and fallback validation plan
- `launcher_status`, `launcher_status_file`: prelaunch failure classification and its adjacent machine-readable status artifact
- `runner_terminal_watcher`: optional detached-root watcher metadata, including its manifest, event journal, dispatch cursor, and watcher tmux session
- `notification_targets`: optional explicit array of structured-notification adapters. Each enabled target declares an `id`, `kind` (`lead-session` or `command`), event allow-list, and literal `argv` vector; never store credentials, URLs containing credentials, or raw notification output in root state.

### State-specific requirements

- `ready`: include `owner_target=delivery-runner`, kickoff references, and enough scope context for claim. Before `lead-launch-runner.sh` starts, it must bind an approved snapshot with matching `scope_snapshot`, `scope_revision`, `scope_snapshot_sha256`, and `approved_refs`; see [Canonical scope governance](scope-governance.md).
- `running`: include the claimed owner plus `current_stage` and active handoff/evidence trail.
- `blocked`: include `blocker_code`, human-readable blocker summary, and `next_action`.
- `done`: include evidence paths and merge/release review hand-back context. It is a delivery hand-back, not a positive release/deployment/milestone claim. For `root_type=discovery`, `done` requires every linked Approved REQ to be `Implemented`, explicitly deferred by lead decision, or represented by a lead-visible escalation/blocked record.
- `archived`: include closure reason so terminal historical closure is not confused with successful completion.

### Normalization rules

- Legacy `claimed` and `in_progress` values should be read as `running` and normalized on the next write.
- `done` is the required successful root completion signal; `archived` is not a success synonym.
- `current_stage` is intentionally narrower than `status`: many stages may map to `running`.

### Discovery-level root queue fields

A Discovery-level root should use a root state plus an optional `batch-queue.json` artifact. Queue item states follow the same canonical state vocabulary where practical: `ready`, `running`, `blocked`, `done`, or `archived`. The runner advances only one queue item at a time unless a project overlay explicitly permits parallel batch execution.

Minimum Discovery root fields:

- `root_type = discovery`
- `discovery_id`
- `implemented_reqs`
- `remaining_approved_reqs`
- `batch_queue` or `batch_queue_path`
- `current_batch`
- `completed_batches`
- `done_definition`

A Discovery root must not be marked `done` merely because one batch completed. It is `done` only when the queue has no remaining non-deferred Approved REQ work and the REQ state/evidence trail is synchronized.

### Example record

```json
{
  "status": "blocked",
  "current_stage": "lead-escalation",
  "owner_target": "lead",
  "goal": "Ship approved kickoff scope for REQ-42",
  "kickoff_artifact": "artifacts/kickoff/req-42.md",
  "updated_at": "2026-07-09T14:12:00Z",
  "approved_refs": ["discovery-17", "req-42"],
  "scope_summary": "Implement batch-lite acceptance updates for REQ-42",
  "current_handoff_artifact": "artifacts/escalation/req-42-publication-auth.md",
  "blocker_code": "publication_auth_missing",
  "blocker_detail": "push_dry_run_failed",
  "evidence_paths": [
    ".stagepilot/artifacts/publication-preflight.json",
    ".stagepilot/worker-progress/runner.md"
  ],
  "next_action": "lead_restore_publication_capability",
  "pr_ref": "feature/req-42-delivery"
}
```

## Escalation artifact schema

Escalation artifacts are the canonical persisted explanation of why runner execution stopped or returned control to the lead.

### Required fields

- `current_stage`: stage at the moment of escalation
- `status`: normally `blocked` for active escalations
- `reason_class`: broad escalation class such as `scope_or_requirements`, `approval_or_priority`, `tooling_or_access_blocker`, `verification_or_release_risk`, or `queue_or_capacity`
- `blocker_code`: machine-readable blocker code
- `blocker_summary`: short human-readable summary
- `options_considered`: concrete options already evaluated
- `recommended_next_action`: runner recommendation
- `cost_of_waiting_or_risk_of_proceeding`: why the lead should care now

### Strongly recommended fields

- `blocker_detail`: subtype / precise detail
- `required_lead_decision`: explicit decision the lead must make
- `affected_scope`: kickoff / batch / acceptance scope impacted
- `verdict_count_for_scope`: when escalation follows repeated QC loops
- `evidence_paths`: referenced artifacts, logs, progress files, or preflight outputs
- `handoff_back_target`: usually `lead`

### Reason-class guidance

- `scope_or_requirements`: REQ ambiguity, conflicting acceptance criteria, or scope mismatch
- `approval_or_priority`: sequencing, priority, or business/governance decisions outside runner authority
- `tooling_or_access_blocker`: publication auth, missing doctor tooling when required, unavailable credentials, broken environment entrypoints
- `verification_or_release_risk`: unresolved QC risk, waiver boundary violations, or release posture beyond runner authority
- `queue_or_capacity`: root kickoff ordering ambiguity or capacity conflict that needs lead direction

### Example artifact

```json
{
  "current_stage": "lead-escalation",
  "status": "blocked",
  "reason_class": "tooling_or_access_blocker",
  "blocker_code": "publication_auth_missing",
  "blocker_detail": "gh_auth_status_failed",
  "blocker_summary": "Runner delivery worktree cannot verify GitHub publication capability.",
  "options_considered": [
    "Retry after refreshing gh auth",
    "Switch to a different publication-capable environment"
  ],
  "recommended_next_action": "Restore publication capability before further impl/QC work.",
  "required_lead_decision": "Decide whether to restore publication capability or pause PR-bound delivery.",
  "cost_of_waiting_or_risk_of_proceeding": "Continuing impl/QC without publication capability risks merge-ready work that still cannot be published.",
  "affected_scope": "REQ-42 root kickoff",
  "evidence_paths": [
    ".stagepilot/artifacts/publication-preflight.json",
    ".stagepilot/worker-progress/runner.md"
  ],
  "handoff_back_target": "lead"
}
```

## Mapping guidance

| Situation | `status` | `current_stage` | `reason_class` | `blocker_code` / detail |
|---|---|---|---|---|
| kickoff emitted, not yet claimed | `ready` | `kickoff` |  |  |
| impl child active | `running` | `impl-running` |  |  |
| QC active | `running` | `qc-review` |  |  |
| publication preflight failed | `blocked` | `lead-escalation` | `tooling_or_access_blocker` | `publication_auth_missing` + subtype |
| launcher prerequisite unavailable | `blocked` | `kickoff` | `tooling_or_access_blocker` | specific code: `hermes_profile_unavailable`, `tmux_unavailable`, `git_worktree_prepare_failed`, `worktree_isolation_bypassed`, or `stagepilot_doctor_required_missing` |
| unacknowledged fast shared-workdir fallback | `blocked` | `kickoff` | `tooling_or_access_blocker` | `fast_shared_workdir_risk_unacknowledged` |
| approved fast fallback used | `running` | `kickoff` |  | `capability_status=degraded`, all fallbacks, tooling debt (when any), and residual risk recorded |
| supervised child hit read-only stall | `blocked` | `lead-escalation` or `impl-running` | `tooling_or_access_blocker` or `verification_or_release_risk` depending on context | `timeout_no_progress_read_loop` / `read_loop_no_diff` |
| doctor required but unavailable | `blocked` | `qc-review` or `lead-escalation` | `tooling_or_access_blocker` | `stagepilot_doctor_required_missing` |
| QC loop reaches a PASS verdict | `running` | `verification-complete` |  | `qc_rework_loop.status=passed`; runner continues to `confirm-batch-verification` |
| same-scope QC verdict remains unresolved at cycle 3 | `blocked` | `lead-escalation` | `verification_or_release_risk` | `qc_rework_budget_exhausted` with a durable lead-escalation artifact |
| QC verdict is malformed/missing or its supervised launch fails | `blocked` | `lead-escalation` | `tooling_or_access_blocker` | `qc_verdict_integrity_failure` or `supervisor_integrity_failure`; never infer an implementation FAIL |
| runner returned merge-ready evidence | `done` | `merge-ready` |  |  |
| kickoff withdrawn/superseded | `archived` | `closed` |  | closure reason required |

## Notification guidance

At minimum, `blocked`, `done`, and root-level `archived` should be considered lead-visible state changes. Detached root runners use `scripts/watch_runner_terminal.py` to emit a durable structured event for `done`, `blocked`, `archived`, `incomplete`, or `supervisor_integrity_failure`; an absent or malformed root exit/status artifact after its tmux session disappears is fail-closed as `supervisor_integrity_failure`.

The launcher supplies the watcher a schema-versioned manifest with a trusted artifact root and safe root-relative artifact paths. The watcher writes its append-only, monotonically sequenced event journal and dispatch cursor next to the root runner log. It atomically claims each event ID in that cursor before invoking a configured target, giving local at-most-once dispatch across restart; receivers that require retries must deduplicate by event ID. It sends the JSON event on stdin only to configured `notification_targets`; an omitted target list records `not_configured` without inventing a messaging destination. Notification delivery mirrors the root delivery-state and must never replace it.

For runner-owned successful delivery completion, the lead-visible `done` delivery-state transition is mandatory; a separate completion notification/summary is optional unless a project overlay explicitly requires one.

## Lifecycle claim gate

Positive lifecycle claims are limited to `release_readiness`, `release_completion`, `milestone_completion` (including program completion), and `deployment_readiness`. Create them only with `scripts/record_lifecycle_claim.py`; it validates the overlay-declared source snapshot, exact decision kind/context, expiration, and unchanged snapshot digest before atomically writing an accepted claim. The claim binds the snapshot artifact path/ID/timestamps/SHA-256 and redacted source revision summary. If the kind is unsupported or the snapshot is unavailable, stale, conflicting, malformed, or mismatched, the command writes no positive claim: it returns non-zero and, when the safe requested artifact path is unused, writes an immutable `unverified` / `BLOCKED` report with normalized findings. See [Control-plane snapshots](control-plane-snapshots.md).

For root kickoff closure without successful completion, `archived` should be accompanied by a reason in the artifact/state trail so the lead can distinguish superseded/withdrawn history from a completed delivery path.

Queued kickoff buildup, uncertain ordering, or reprioritization need should also be surfaced to the lead when it affects delivery flow.

## Bounded autonomous QC rework loop

For a `standard` or `guarded` delivery that requires independent QC, the runner can
use `scripts/run_qc_rework_loop.py` to make the approved same-scope loop executable:

```bash
python3 scripts/run_qc_rework_loop.py \
  --delivery-state .stagepilot/delivery-state.json \
  --acceptance-scope 'REQ-42@3:checkout' \
  --impl-handoff .stagepilot/handoffs/impl.md \
  --implementation-context .stagepilot/handoffs/impl-context.md \
  --qc-handoff .stagepilot/handoffs/qc.md \
  --validation-command 'python3 -m unittest discover -s tests -p "test_*.py"'
```

The controller always performs fresh supervised QC. A QC worker must replace the
controller-provided `--verdict-output` JSON template before it returns. A valid
verdict binds `schema_version: 1`, the exact `acceptance_scope`, a `pass` or `fail`
verdict, and, for FAIL, a classified non-empty gap list. Only
`implementation_defect` and `evidence_gap` can launch one fresh implementation
rework followed by the required validation commands and another fresh QC review.

The durable `qc_rework_loop` state records the acceptance scope and verdict count. After every fresh QC invocation returns, including malformed/missing verdict and QC launcher/supervisor failure paths, the root state records `verdict_count_for_scope` and `current_qc_verdict_artifact` before verdict evaluation or escalation. Rework adds `current_handoff_artifact`, `owner_target=dev-impl`, and `next_action=rework_impl`; fresh QC returns ownership to `dev-qc`. This makes the verdict count, remediation handoff, and next owner visible in the canonical root trail rather than only inside controller-local artifacts.
It has a fixed maximum of three QC verdict cycles (initial review plus no more than
two rework/re-review cycles). Scope/approval/release-risk failures escalate
immediately; malformed verdicts and launcher/supervisor failures are integrity
failures; and cycle three unresolved creates `blocked / lead-escalation` with a
machine-readable escalation artifact. Terminal PASS and blocked states are
idempotent: rerunning the controller does not launch another worker.
