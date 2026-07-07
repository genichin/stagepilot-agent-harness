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
- `delivery-runner` begins after approved Discovery and approved REQ handoff, chooses batch grouping and delivery slicing within approved scope, and does not own Discovery drafting, Discovery approval, REQ drafting, or REQ approval.
- `dev-impl` and `dev-qc` operate on approved scope rather than redefining Discovery intent.

## Post-REQ kickoff rule

Default post-REQ behavior:

- `confirm-req` does not wait for a second user kickoff by default.
- The lead may issue `lead -> delivery-runner` automatically once REQ approval completes, unless the user explicitly asked to hold, defer, batch later, or wait.
- For kanban-backed delivery, this handoff is a root kickoff card on the project's canonical board.
- The runner claims that kickoff only through the documented claim semantics.
- Default concurrency is one root kickoff card in `running` per runner globally across boards.
- Downstream impl/QC handoffs stay transport-agnostic unless a project overlay opts into child-card routing.
- One root kickoff card maps to one primary PR by default.
- The runner may open/update that PR, but the default merge decision belongs to the lead after `confirm-req-implemented`.

## Release boundary after delivery

The `delivery-runner` owns the approved-scope delivery chain through batch grouping, batch creation, batch execution, verification approval, and REQ sync to `Implemented` where evidence exists.

Standard delivery/release boundary:

- Runner-owned endpoint: `confirm-req-implemented`.
- Standard QC path: `delivery-runner -> dev-qc` before `confirm-batch-verification`.
- QC skip: allowed only for low-risk `batch-lite`, with skip reason and residual risk documented.
- QC retry cap: 3 verdict cycles for the same acceptance scope.
- 3rd unresolved verdict: escalate to `lead`.
- Immediate escalation instead of retry budget: REQ ambiguity, conflicting acceptance criteria, scope mismatch, or release-risk posture.
- Required completion signal: lead-visible `done` on the active root kickoff.
- Optional artifact: separate runner-to-lead completion summary.
- After `confirm-req-implemented`, release-family work returns to `lead`.

## Exceptions

Create project-specific worker variants only when compliance, credentials, tooling, or repo topology meaningfully diverge from the shared baseline.
