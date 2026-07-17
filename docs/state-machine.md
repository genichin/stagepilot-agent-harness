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
- `approved_refs`: approved Discovery / REQ references anchoring scope
- `scope_summary`: short scope statement for this kickoff
- `current_handoff_artifact`: currently active impl/QC/escalation/completion artifact path when one exists
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
- `tooling_debts`: optional non-blocking tooling debt objects, including code and fallback validation plan
- `launcher_status`, `launcher_status_file`: prelaunch failure classification and its adjacent machine-readable status artifact

### State-specific requirements

- `ready`: include `owner_target=delivery-runner`, kickoff references, and enough scope context for claim.
- `running`: include the claimed owner plus `current_stage` and active handoff/evidence trail.
- `blocked`: include `blocker_code`, human-readable blocker summary, and `next_action`.
- `done`: include evidence paths and merge/release review hand-back context. For `root_type=discovery`, `done` requires every linked Approved REQ to be `Implemented`, explicitly deferred by lead decision, or represented by a lead-visible escalation/blocked record.
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
| runner returned merge-ready evidence | `done` | `merge-ready` |  |  |
| kickoff withdrawn/superseded | `archived` | `closed` |  | closure reason required |

## Notification guidance

At minimum, `blocked`, `done`, and root-level `archived` should be considered lead-visible state changes.

For runner-owned successful delivery completion, the lead-visible `done` delivery-state transition is mandatory; a separate completion notification/summary is optional unless a project overlay explicitly requires one.

For root kickoff closure without successful completion, `archived` should be accompanied by a reason in the artifact/state trail so the lead can distinguish superseded/withdrawn history from a completed delivery path.

Queued kickoff buildup, uncertain ordering, or reprioritization need should also be surfaced to the lead when it affects delivery flow.
