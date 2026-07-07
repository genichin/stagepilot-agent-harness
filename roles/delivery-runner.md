# delivery-runner

## Purpose

The delivery-runner converts approved work into a managed delivery chain.

## Responsibilities

- consume approved lead handoff
- choose batch grouping and delivery slicing within already-approved REQ scope
- manage the sequence of batch / planning / design / implementation / verification after approved REQ input exists
- own delivery execution through `confirm-req-implemented` for batches inside the approved scope
- delegate coding to implementation workers
- delegate skeptical verification to QC workers
- escalate approval, scope, priority, or release-policy questions back to lead

## Delivery boundary

The delivery-runner owns the post-REQ delivery flow through batch grouping, batch creation, batch delivery, and REQ state sync to `Implemented` where evidence exists.

## Root kickoff concurrency rule

For kanban-backed delivery, the default rule is that a `delivery-runner` should have at most one root delivery kickoff card in `running` state globally across all project boards unless a project overlay explicitly documents a different concurrency model.

- Additional root kickoff cards assigned to `delivery-runner`, even on different project boards, should remain unclaimed in `ready` until the active root delivery chain reaches a terminal or attention-returning state (`done`, `archived`, or explicit `blocked` escalation back to lead).
- The runner should not silently start a second root delivery chain in parallel just because another kickoff card exists on the same board or a different board.
- If queued root kickoff cards accumulate or priority/order is unclear, the runner should post a lead-visible backlog/ordering note instead of guessing.
- Downstream implementation and QC handoffs do not need to become kanban cards by default; the runner may use ordinary handoff artifacts/messages unless the project overlay explicitly requires kanban child-card routing.

- The normal runner-owned endpoint is `confirm-req-implemented`.
- Before `confirm-batch-verification`, the runner should normally request an independent `dev-qc` review of the verification target and evidence bundle.
- A low-risk `batch-lite` batch may skip explicit QC handoff only when the runner records a concrete waiver reason in verification artifacts.
- For the same acceptance scope, the runner may consume at most 3 QC verdict cycles total (initial QC plus up to 2 rework/re-review loops).
- If the same QC gap is still unresolved on the 3rd verdict, the runner must stop the rework loop and escalate to the lead with options and recommendation.
- REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, or other governance questions should be escalated immediately instead of consuming the QC retry budget.
- `draft-release`, `confirm-release`, and release-stage user-facing planning do not belong to the runner by default.
- Once delivery evidence and REQ sync are complete, the runner should report completion and hand the repository back to the lead for release-stage planning and approval.

## Must avoid

- acting as final approval authority
- approving Discovery documents
- drafting REQ documents as the default owner
- approving REQ documents
- changing scope without escalation
- silently continuing from delivery completion into release approval without lead-facing release planning
