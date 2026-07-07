# State Machine

## Canonical task states

- `todo`
- `ready`
- `running`
- `blocked`
- `done`
- `archived`

## Semantics

### blocked
A worker cannot proceed without an external dependency, approval, or clarified decision.

### done
The assigned unit of work has completed its expected execution path and produced evidence.

### archived
The task is closed for active routing and retained only for history.

## Notification guidance

At minimum, `blocked` and `done` should be considered lead-visible state changes.
