# delivery-runner -> dev-qc

## Default trigger

This handoff is the normal path before `confirm-batch-verification`.

- The runner should request QC review once implementation evidence and verification drafting are ready.
- A low-risk `batch-lite` exception may skip the handoff only if the runner documents the skip reason and residual risk in the verification artifact.

## Required fields

- verification target
- acceptance criteria
- evidence bundle to inspect
- pass/fail format
- suspicious areas or risks

## Output expectation

QC should return a verdict, evidence reviewed, uncovered gaps, and required follow-up.

- If the runner requested review on an exception or waiver path, QC should explicitly state whether the waiver seems acceptable and what residual risk remains.
