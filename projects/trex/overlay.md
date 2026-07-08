# TREX overlay

## Known conventions

- project-specific lead profile: `trex-dev-lead`
- shared worker profiles: `delivery-runner`, `dev-impl`, `dev-qc`
- root kickoff transport: artifact-backed handoff + delivery state record
- root kickoff launch: lead explicitly starts `delivery-runner` in detached background `tmux` via `scripts/lead-launch-runner.sh`
- root kickoff workspace isolation: `scripts/lead-launch-runner.sh` prepares a per-kickoff delivery branch/worktree so TREX discovery edits in the main checkout do not leak into the runner PR branch
- impl launch default: runner explicitly starts `dev-impl` in foreground via `scripts/runner-launch-impl.sh`
- qc launch default: runner explicitly starts `dev-qc` in foreground via `scripts/runner-launch-qc.sh`
- optional Telegram notify: project-specific thread/message routing if TREX wants visibility
- kanban: forbidden. Do not use board/card transport for kickoff, queueing, implementation, QC, or completion.

## Notes

TREX uses the shared worker topology with project-specific lead ownership.

## Overlay guidance for workspace layout

- Core harness only requires isolation between the lead/human primary checkout and the runner delivery worktree.
- Core harness default is repo-local `.worktrees/` when a project does not specify anything else.
- Parent-directory layout decisions such as a top-level project-control folder, `repos/` as the home for main checkouts, or a shared external worktree root are project-adoption decisions and should be documented here.
- If TREX wants `repos/<repo-name>` for lead/human main checkouts and a separate sibling path for runner worktrees, state that override here and pass explicit `--worktree-path` / `--workdir` values when needed.
