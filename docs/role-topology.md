# Role Topology

## Baseline topology

- `<project>-dev-lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

## Why

This keeps user-facing work free from long-running execution while preserving reusable worker roles.

## Responsibility boundaries

- `<project>-dev-lead` owns Discovery drafting, Discovery approval, REQ drafting, REQ approval, clarification, prioritization, and user-facing scope decisions.
- `delivery-runner` begins after approved Discovery and approved REQ handoff and does not own Discovery drafting, Discovery approval, REQ drafting, or REQ approval.
- `dev-impl` and `dev-qc` operate on approved scope rather than redefining Discovery intent.

## Exceptions

Create project-specific worker variants only when compliance, credentials, tooling, or repo topology meaningfully diverge from the shared baseline.
