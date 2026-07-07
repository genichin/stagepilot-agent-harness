# delivery-runner -> dev-qc

This handoff is transport-agnostic. It may be issued through ordinary runner-to-worker instructions, documents, or messages. Kanban representation is forbidden.

## Default trigger

This handoff is the normal path before `confirm-batch-verification`.

- The runner should request QC review once implementation evidence and verification drafting are ready.
- A low-risk `batch-lite` exception may skip the handoff only if the runner documents the skip reason and residual risk in the verification artifact.
- The default retry budget for the same acceptance scope is 3 QC verdict cycles total; if the same gap is still unresolved on the 3rd verdict, escalate to `lead` rather than looping again.

## Required fields

- verification target
- acceptance criteria
- evidence bundle to inspect
- pass/fail format
- suspicious areas or risks

## Output expectation

QC should return a verdict, evidence reviewed, uncovered gaps, and required follow-up.

- If the runner requested review on an exception or waiver path, QC should explicitly state whether the waiver seems acceptable and what residual risk remains.
- If QC sees REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, or another governance-bound issue, QC should mark that the case needs immediate lead escalation instead of normal implementation retry.
- If QC is returning a repeated unresolved gap, it should say whether this is 1st/2nd/3rd verdict for the same acceptance scope so the runner can enforce the retry cap.
