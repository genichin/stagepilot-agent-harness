# completion summary

This handoff artifact is optional by default. The required successful completion signal for runner work is a persisted delivery-state transition to `done` plus delivery artifacts/state that the lead can inspect during release review. `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue, not normal successful completion. Optional Telegram notification may mirror the completion for visibility, but notification is not the source of truth. Use a completion summary when an explicit runner-to-lead wrap-up message is helpful or when a project overlay requires it.

## Minimum payload

- `status` = `done` in the root delivery-state record (completion summary is secondary)
- final `current_stage` such as `merge-ready`
- scope delivered
- artifacts produced
- verification executed
- unresolved risks
- suggested next step
- `evidence_paths` that let the lead inspect the result directly
- `pr_ref` / branch reference when the kickoff maps to a PR

## Completion-state rule

A completion summary should match the root delivery-state record rather than invent a separate success definition.

- Successful normal completion => root state `status=done`
- Historical withdrawal/supersession => root state `status=archived` with closure reason
- If the runner still needs a lead decision, use escalation instead of completion
