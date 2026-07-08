# delivery-runner -> dev-qc

This handoff is transport-agnostic. It may be issued through ordinary runner-to-worker instructions, documents, or messages. Kanban representation is forbidden.

## Default launch rule

- Default launch mode is foreground bounded worker execution.
- The runner should normally call QC explicitly via `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>`.
- The wrapper runs `hermes --profile dev-qc chat -q ...` and blocks until QC returns a verdict.
- The default is foreground because QC is a bounded review step inside runner-owned orchestration; it is not a second root kickoff chain.
- Use `--background` only when the review is materially long-running, needs a resumable detached session, or the project overlay explicitly requires detached worker execution.

## Required state reflection

- Before launch, the runner should reflect `current_stage: qc-review` in the root delivery-state or paired verification artifact trail.
- The handoff should name the QC handoff artifact path and the root delivery-state path.
- When QC returns, the runner should record the verdict, verdict count for the same acceptance scope, reviewed evidence paths, and required follow-up.
- A separate root delivery-state file for QC is not required by default; QC execution is tracked as a worker step under the active root delivery item.

## Default trigger

This handoff is the normal path before `confirm-batch-verification`.

- The runner should request QC review once implementation evidence and verification drafting are ready.
- A low-risk `batch-lite` exception may skip the handoff only if the runner documents the skip reason and residual risk in the verification artifact.
- The default retry budget for the same acceptance scope is 3 QC verdict cycles total; if the same gap is still unresolved on the 3rd verdict, escalate to `lead` rather than looping again.

## Required fields

- qc handoff artifact path
- root delivery state path
- verification target
- acceptance criteria
- evidence bundle to inspect
- pass/fail format
- suspicious areas or risks

## Claim / start rule

`dev-qc` has started only when both are true:

1. the runner has explicitly launched the worker through the wrapper or an equivalent foreground Hermes call
2. the delivery or verification trail reflects `qc-review` (or equivalent worker-start acknowledgment) tied to the active handoff artifact

## Output expectation

QC should return a verdict, evidence reviewed, uncovered gaps, and required follow-up.

- If the runner requested review on an exception or waiver path, QC should explicitly state whether the waiver seems acceptable and what residual risk remains.
- If QC sees REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, or another governance-bound issue, QC should mark that the case needs immediate lead escalation instead of normal implementation retry.
- If QC is returning a repeated unresolved gap, it should say whether this is 1st/2nd/3rd verdict for the same acceptance scope so the runner can enforce the retry cap.

- Minimum return payload: verdict, evidence reviewed, uncovered gaps, follow-up required, verdict count for the same acceptance scope.
