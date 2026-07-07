# StagePilot doctor finding triage quick guide

## Common findings

| Finding code | Typical meaning | Default handling |
|---|---|---|
| `bootstrap-required` | Fresh repo is missing baseline bootstrap files | Usually informational guidance before first Discovery; route to `bootstrap-baseline` |
| `orphan-approved-req` | An approved REQ is not yet in any batch | Often expected immediately after REQ approval; clear with batch creation |
| `approved-req-no-release-candidate-batch` | Approved REQ is not yet covered by a release-ready batch | Often expected before verification confirmation; rerun after batch promotion |
| `report-write-failed` | Requested Markdown report could not be written | Blocker when report output was part of the task deliverable |

## Operator rule

When in doubt:

1. classify the finding,
2. name the next StagePilot skill that resolves it,
3. rerun doctor after that step,
4. record the rerun result in the artifact or summary.
