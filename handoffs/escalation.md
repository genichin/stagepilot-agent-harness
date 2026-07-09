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

- current stage
- blocker summary
- options considered
- recommended next action
- cost of waiting / risk of proceeding
- QC verdict count for the affected acceptance scope
- whether the issue is implementation rework, evidence gap, or governance ambiguity
- machine-readable blocker code when available (for example `publication_auth_missing`, `publication_auth_missing:push_dry_run_failed`, `tooling_debt:stagepilot_doctor_unavailable`)
