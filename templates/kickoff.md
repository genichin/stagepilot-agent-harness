# Kickoff Template

## Context
- project:
- approved discovery reference:
- approved REQ reference:
- goal:

## Scope guardrails
- canonical scope snapshot path (relative to delivery state):
- approved REQ revision (for example `REQ-42@3`):
- snapshot SHA-256:
- in scope:
- out of scope:
- locked decisions:
- change rule: lead-approved revision only; workers escalate scope conflicts instead of re-specifying

## Execution notes
- repo/workdir:
- acceptance definition:
- kickoff artifact path:
- delivery state path:
- launch command: `scripts/lead-launch-runner.sh <kickoff_artifact> <delivery_state>`
- launch mode: detached background `tmux`
- default delivery branch/worktree: auto-prepared isolated runner checkout for this kickoff
- live post-kickoff Discovery/REQ edits: do not auto-import into runner branch; require explicit lead sync/re-handoff
- delivery owner target: `delivery-runner`

## Root delivery-state seed
- status: `ready`
- current_stage: `kickoff`
- owner_target: `delivery-runner`
- goal:
- kickoff_artifact:
- updated_at:
- approved_refs: (must include the bound `REQ@revision`)
- scope_snapshot: (relative JSON path next to this state)
- scope_revision:
- scope_snapshot_sha256:
- scope_summary:
- evidence_paths:
- next_action: `launch_runner`
- optional pr_ref:
- expected reporting cadence / milestone:
- escalation conditions:
- optional Telegram notify destination/thread:
- optional queue note if another root kickoff is already active for this runner:
- optional PR / delivery-unit note:
