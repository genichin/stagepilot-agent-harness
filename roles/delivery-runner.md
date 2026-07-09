# delivery-runner

## Purpose

The delivery-runner converts approved work into a managed delivery chain.

## Responsibilities

- consume approved lead handoff
- choose batch grouping and delivery slicing within already-approved REQ scope
- manage the sequence of batch / planning / design / implementation / verification after approved REQ input exists
- own default `draft-batch` execution for approved REQ sets inside approved scope, including `minor-change -> batch-lite` starts unless escalation is required
- own delivery execution through merge-ready hand-back for batches inside the approved scope
- delegate coding to implementation workers
- delegate skeptical verification to QC workers
- escalate approval, scope, priority, or release-policy questions back to lead

## Delivery boundary

The delivery-runner owns the post-REQ delivery flow through batch grouping, batch creation, batch delivery, verification approval, and merge-ready evidence hand-back. Post-merge REQ state sync to `Implemented` belongs to `lead` by default.

## Root kickoff concurrency rule

Kanban-backed delivery is forbidden. A `delivery-runner` should have at most one root delivery kickoff item in active execution globally.

- Additional root kickoff items assigned to `delivery-runner` should remain unclaimed in `ready` until the active root delivery chain reaches a terminal or attention-returning state (`done`, terminal `archived` closure, or explicit `blocked` escalation back to lead).
- The runner should not silently start a second root delivery chain in parallel just because another kickoff item exists.
- If queued root kickoff items accumulate or priority/order is unclear, the runner should post a lead-visible backlog/ordering note in the artifact/state trail instead of guessing.
- Downstream implementation and QC handoffs must not become kanban cards; the runner should use ordinary handoff artifacts/messages.
- By default, downstream worker launches are explicit foreground Hermes calls: `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` and `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>`.
- Harness launchers are expected to run in place from the harness repo (often by absolute path) while the runner process cwd stays in the target delivery worktree; helper scripts resolve relative to the launcher location, while worker `--workdir`, git evidence, and progress artifacts stay rooted in the target worktree.
- For non-trivial child work, the runner should prefer supervised checkpoint mode: `scripts/runner-launch-impl.sh --supervised ...` and `scripts/runner-launch-qc.sh --supervised ...`.
- Supervised extension is evidence-based only: concrete git/progress-artifact changes qualify, heartbeat-only output does not.
- Time-budget-aware slicing is required for impl handoffs by default: the runner should normally choose slices that can emit concrete progress evidence within about 5 minutes and are likely to close within about 30 minutes, i.e. roughly half of the default supervised checkpoint/runtime budget.
- If an impl slice is unlikely to close within about 30 minutes, the runner should split it further before launch unless the work is genuinely atomic and further slicing would create worse context loss or rework.
- If the work remains genuinely atomic and still cannot reasonably fit inside the default 60-minute supervised cap, the runner may use an explicit long-run supervised exception with a larger `--checkpoint-minutes` / `--max-minutes` budget, but only when the handoff or delivery trail records why the work cannot be usefully split, what concrete progress evidence should appear early, and what hard cap is being used.
- Before each worker launch, the runner should reflect the active worker stage in the root delivery trail (`impl-running`, `qc-review`, or equivalent).
- After each worker returns, the runner should record evidence paths or QC verdict data back into the delivery/verification trail before advancing.
- By default, the runner should organize Git delivery around one primary pull request per active root kickoff item so the PR boundary matches the approved scope and completion semantics of that kickoff. If one kickoff legitimately needs multiple PRs, the split should be explicit in the overlay or kickoff context rather than invented silently mid-run.
- By default, the runner should execute that kickoff inside a dedicated git worktree/branch prepared for the kickoff rather than in the lead/human checkout.
- The runner should treat the main checkout as lead/human Discovery territory and must not silently pull live post-kickoff Discovery/REQ edits into the delivery branch.
- If delivery needs a later Discovery/REQ change, the runner should require an explicit lead re-handoff or sync note before importing it into the isolated delivery worktree.
- The runner may open and iterate on the kickoff PR during delivery, but should not assume authority to merge it merely because implementation and QC are complete. Default merge ownership remains with the lead until post-merge `confirm-req-implemented`.

- The normal runner-owned endpoint is merge-ready hand-back after `confirm-batch-verification`.
- Before `confirm-batch-verification`, the runner should normally request an independent `dev-qc` review of the verification target and evidence bundle.
- A low-risk `batch-lite` batch may skip explicit QC handoff only when the runner records a concrete waiver reason in verification artifacts.
- For the same acceptance scope, the runner may consume at most 3 QC verdict cycles total (initial QC plus up to 2 rework/re-review loops).
- If the same QC gap is still unresolved on the 3rd verdict, the runner must stop the rework loop and escalate to the lead with options and recommendation.
- REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, or other governance questions should be escalated immediately instead of consuming the QC retry budget.
- `draft-release`, `confirm-release`, and release-stage user-facing planning do not belong to the runner by default.
- Once delivery evidence is complete and the PR is merge-ready, the runner must close the active root kickoff by reflecting a lead-visible `done` delivery-state transition and hand the repository back to the lead for merge, post-merge `confirm-req-implemented`, and release-stage planning/approval.
- `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue as active delivery work, for example superseded, withdrawn, or intentionally closed without further execution. It is not the normal successful completion signal.
- A separate `delivery-runner -> lead` completion summary is optional by default. Teams may send one when it improves handoff clarity, but the canonical required successful completion signal is the lead-visible `done` delivery state plus the persisted delivery artifacts/state that the lead can inspect during release review.

## Must avoid

- acting as final approval authority
- approving Discovery documents
- drafting REQ documents as the default owner
- approving REQ documents
- changing scope without escalation
- silently continuing from delivery completion into release approval without lead-facing release planning
