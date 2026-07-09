# escalation

## Trigger conditions

- scope ambiguity
- approval gate
- conflicting requirements
- blocked dependency
- publication auth / remote push capability missing for PR-bound delivery
- verification uncertainty affecting release judgment
- same QC gap remains unresolved on the 3rd verdict for the same acceptance scope
- release-risk posture exceeds runner authority

## Minimum payload

- `current_stage`
- `status` (normally `blocked`)
- `reason_class`
- `blocker_code`
- blocker summary
- options considered
- recommended next action
- cost of waiting / risk of proceeding
- QC verdict count for the affected acceptance scope when relevant
- whether the issue is implementation rework, evidence gap, or governance ambiguity
- `evidence_paths`
- machine-readable blocker code when available (for example `publication_auth_missing`, `publication_auth_missing:push_dry_run_failed`, `tooling_debt:stagepilot_doctor_unavailable`)

## Reason-class defaults

- `scope_or_requirements`
- `approval_or_priority`
- `tooling_or_access_blocker`
- `verification_or_release_risk`
- `queue_or_capacity`

## Blocker-code / subtype guidance

- Put the stable family in `blocker_code`, for example `publication_auth_missing`.
- Put the narrower subtype in `blocker_detail` when needed, for example `gh_auth_status_failed`, `push_dry_run_failed`, or `read_loop_no_diff`.
- When the supervisor already emitted a more specific result class such as `timeout_no_progress_read_loop`, preserve that exact value in either `blocker_code` or a mapped `blocker_code` + `blocker_detail` pair instead of replacing it with prose only.

## Required lead-facing question

Every escalation should make the missing lead decision explicit, for example:

- restore publication capability or pause PR-bound delivery
- resolve REQ ambiguity before further implementation
- choose between two priority-compatible delivery slices
- accept or reject a verification waiver / release-risk exception
