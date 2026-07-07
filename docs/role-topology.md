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

After `confirm-req`, the default assumption is not "wait for a second user kickoff." The lead may issue the `lead -> delivery-runner` handoff automatically once REQ approval is complete, as long as the user has not explicitly asked to hold, defer, batch later, or wait for additional confirmation. This keeps post-approval delivery non-blocking without transferring REQ ownership away from the lead.

## Release boundary after delivery

The `delivery-runner` owns the approved-scope delivery chain through batch grouping, batch creation, batch execution, verification approval, and REQ sync to `Implemented` where evidence exists.

- In the standard model, the runner-owned endpoint is `confirm-req-implemented`.
- Before `confirm-batch-verification`, the standard path includes an independent `delivery-runner -> dev-qc` handoff.
- Only a low-risk `batch-lite` path may skip explicit QC handoff, and that exception should be documented in verification output.
- After that point, release-family work returns to the lead: `draft-release`, `confirm-release`, and human-facing release planning are not runner-owned by default.
- This keeps delivery automation fast while preserving release timing, rollout posture, and go/no-go decisions as lead-plus-human responsibilities.

## Exceptions

Create project-specific worker variants only when compliance, credentials, tooling, or repo topology meaningfully diverge from the shared baseline.
