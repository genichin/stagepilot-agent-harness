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

## Notification guidance

At minimum, `blocked`, `done`, and root-level `archived` should be considered lead-visible state changes.

For runner-owned successful delivery completion, the lead-visible `done` delivery-state transition is mandatory; a separate completion notification/summary is optional unless a project overlay explicitly requires one.

For root kickoff closure without successful completion, `archived` should be accompanied by a reason in the artifact/state trail so the lead can distinguish superseded/withdrawn history from a completed delivery path.

Queued kickoff buildup, uncertain ordering, or reprioritization need should also be surfaced to the lead when it affects delivery flow.
