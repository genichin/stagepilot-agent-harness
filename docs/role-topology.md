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
- `delivery-runner` begins after approved Discovery and approved REQ handoff, chooses batch grouping and delivery slicing within approved scope, owns default `draft-batch` execution for approved REQ sets inside that scope, and does not own Discovery drafting, Discovery approval, REQ drafting, or REQ approval.
- `dev-impl` and `dev-qc` operate on approved scope rather than redefining Discovery intent.

## Post-REQ kickoff rule

Default post-REQ behavior:

- `confirm-req` does not wait for a second user kickoff by default.
- The lead may issue `lead -> delivery-runner` automatically once REQ approval completes, unless the user explicitly asked to hold, defer, batch later, or wait.
- By default, this handoff is a kickoff artifact plus a small delivery-state record; optional Telegram notification may mirror it for visibility.
- Artifact creation alone does not start runner work. The lead must explicitly launch `delivery-runner`; the default harness launch path is `scripts/lead-launch-runner.sh`, which runs `hermes --profile delivery-runner` in detached background `tmux`.
- The default lead launch path also prepares a dedicated git worktree/branch for that kickoff so delivery PR work is isolated from lead/human Discovery edits in the main checkout.
- The runner claims that kickoff only through the documented artifact/state claim semantics.
- Default concurrency is one root kickoff item in active execution per runner globally unless a project overlay documents otherwise.
- Downstream impl/QC handoffs stay transport-agnostic and must not use kanban.
- One root kickoff item maps to one primary PR by default.
- Lead/human live Discovery edits stay in the main checkout by default; they do not automatically flow into the isolated runner worktree.
- The runner may open/update that PR, but the default merge decision belongs to the lead after `confirm-req-implemented`.

## Release boundary after delivery

The `delivery-runner` owns the approved-scope delivery chain through batch grouping, batch creation (`draft-batch`), batch execution, verification approval, and REQ sync to `Implemented` where evidence exists.

Standard delivery/release boundary:

- Runner-owned endpoint: `confirm-req-implemented`.
- Standard QC path: `delivery-runner -> dev-qc` before `confirm-batch-verification`.
- QC skip: allowed only for low-risk `batch-lite`, with skip reason and residual risk documented.
- QC retry cap: 3 verdict cycles for the same acceptance scope.
- 3rd unresolved verdict: escalate to `lead`.
- Immediate escalation instead of retry budget: REQ ambiguity, conflicting acceptance criteria, scope mismatch, or release-risk posture.
- Required successful completion signal: lead-visible `done` on the active root kickoff.
- `archived` is reserved for terminal historical closure when a root kickoff should no longer continue as active delivery work; it is not the normal successful completion signal.
- Optional artifact: separate runner-to-lead completion summary.
- After `confirm-req-implemented`, release-family work returns to `lead`.

## Exceptions

Create project-specific worker variants only when compliance, credentials, tooling, or repo topology meaningfully diverge from the shared baseline.
