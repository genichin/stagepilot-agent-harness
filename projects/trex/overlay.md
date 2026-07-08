# TREX overlay

## Known conventions

- project-specific lead profile: `trex-dev-lead`
- shared worker profiles: `delivery-runner`, `dev-impl`, `dev-qc`
- root kickoff transport: artifact-backed handoff + delivery state record
- root kickoff launch: lead explicitly starts `delivery-runner` in detached background `tmux` via `scripts/lead-launch-runner.sh`
- impl launch default: runner explicitly starts `dev-impl` in foreground via `scripts/runner-launch-impl.sh`
- qc launch default: runner explicitly starts `dev-qc` in foreground via `scripts/runner-launch-qc.sh`
- optional Telegram notify: project-specific thread/message routing if TREX wants visibility
- kanban: forbidden. Do not use board/card transport for kickoff, queueing, implementation, QC, or completion.

## Notes

TREX uses the shared worker topology with project-specific lead ownership.
