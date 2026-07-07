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

When a `delivery-runner` already has another root kickoff card in `running` anywhere, additional root kickoff cards normally remain in `ready` as queued work rather than being auto-claimed, even if they are on a different project board.

### running
The assigned worker has actively claimed the task/card and started execution. For `lead -> delivery-runner` kickoff cards, `running` means the runner is the explicit assignee/owner and has posted the initial orchestration acknowledgment.

### blocked
A worker cannot proceed without an external dependency, approval, or clarified decision.

### done
The assigned unit of work has completed its expected execution path and produced evidence. For a `lead -> delivery-runner` root kickoff card, `done` is the required completion signal that returns active ownership to the lead for release-stage review.

### archived
The task is closed for active routing and retained only for history.

## Notification guidance

At minimum, `blocked` and `done` should be considered lead-visible state changes.

For runner-owned delivery completion, the lead-visible `done` state is mandatory; a separate completion notification/summary is optional unless a project overlay explicitly requires one.

Queued kickoff buildup, uncertain ordering, or reprioritization need should also be surfaced to the lead when it affects delivery flow.
