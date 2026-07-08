# completion summary

This handoff artifact is optional by default. The required successful completion signal for runner work is a persisted delivery-state transition to `done` plus delivery artifacts/state that the lead can inspect during release review. `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue, not normal successful completion. Optional Telegram notification may mirror the completion for visibility, but notification is not the source of truth. Use a completion summary when an explicit runner-to-lead wrap-up message is helpful or when a project overlay requires it.

## Minimum payload

- scope delivered
- artifacts produced
- verification executed
- unresolved risks
- suggested next step
