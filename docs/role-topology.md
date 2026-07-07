# Role Topology

## Baseline topology

- `<project>-dev-lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

## Why

This keeps user-facing work free from long-running execution while preserving reusable worker roles.

## Exceptions

Create project-specific worker variants only when compliance, credentials, tooling, or repo topology meaningfully diverge from the shared baseline.
