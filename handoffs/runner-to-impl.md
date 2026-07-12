# delivery-runner -> dev-impl

This handoff is transport-agnostic. It may be issued through ordinary runner-to-worker instructions, documents, or messages. Kanban representation is forbidden.

## Default launch rule

- Default launch mode is foreground bounded worker execution.
- For non-trivial implementation handoffs, the preferred foreground path is supervised checkpoint execution via `scripts/runner-launch-impl.sh --supervised --implementation-context <implementation_context> <impl_handoff_artifact> <delivery_state>`.
- Supervised implementation launches require an implementation-context artifact by default. It must identify Target files, Edit anchors, Allowed search budget, Validation commands, and First progress deadline before the worker starts.
- The launcher is expected to run in place from the harness repo (often by absolute path) even when the runner cwd is the target delivery worktree; helper scripts resolve relative to the launcher location, while worker `--workdir`, git evidence, and progress artifacts stay rooted in the target worktree.
- The runner may still use `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` for short/simple bounded work.
- The wrapper runs `hermes --profile dev-impl chat -q ...`; in supervised mode it checkpoints progress every N minutes and extends only when concrete evidence exists. It also stops early on first-progress deadline miss, repeated context compaction, or read/search loops without write/diff/progress evidence.
- Concrete evidence includes git diff/status changes or updated progress artifacts under `.stagepilot/worker-progress/`; heartbeat-only messages do not qualify.
- Before significant impl work for a PR-bound kickoff, the runner should already have completed publication auth preflight in the delivery worktree and escalated immediately on `publication_auth_missing` rather than discovering auth/push failure only after impl/QC completion.
- Runner slicing should normally target impl work that can show concrete progress evidence within about 5 minutes and is likely to finish within about 30 minutes, i.e. roughly half of the default supervised checkpoint/runtime budget.
- If a proposed impl slice is unlikely to finish within about 30 minutes, split it further before launch unless the work is genuinely atomic.
- If the work remains genuinely atomic and still cannot reasonably fit inside the default 60-minute supervised cap, the runner may use an explicit long-run supervised exception with larger `--checkpoint-minutes` / `--max-minutes` values, but the handoff must record why the task cannot be usefully sliced further, what early progress artifact or git evidence should appear, and what hard cap is being used.
- `scripts/runner-launch-impl.sh` also supports runtime-budget presets: `--preset default` (10/60), `--preset stretched` (15/90), and `--preset long-run` (20/120). Explicit minute flags still override the preset when a justified nonstandard budget is needed.
- The default is foreground because implementation is a bounded child task inside runner-owned orchestration; it is not a second root orchestrator.
- Use `--background` only when the implementation step is materially long-running, needs a resumable detached session, or would otherwise block unrelated runner work for too long.

## Required state reflection

- Before launch, the runner should reflect `current_stage: impl-running` in the root delivery-state or paired delivery artifact trail.
- The handoff should name the impl handoff artifact path and the root delivery-state path.
- When implementation returns, the runner should record evidence paths, the executed checks summary, and either `done` or `blocked` status for the implementation step.
- A separate root delivery-state file for impl is not required by default; impl execution is tracked as a worker step under the active root delivery item.

## Required fields

- impl handoff artifact path
- root delivery state path
- exact bounded task
- relevant approved docs
- acceptance target
- commands/tests to run
- evidence required back
- implementation-context artifact path and readiness-gate result

## Claim / start rule

`dev-impl` has started only when both are true:

1. the runner has explicitly launched the worker through the wrapper or an equivalent foreground Hermes call
2. the delivery trail reflects `impl-running` (or equivalent worker-start acknowledgment) tied to the active handoff artifact

## Output expectation

Implementation should return changed files, executed checks, and any remaining risks.

- Minimum return payload: changed files, commands/checks run, evidence paths, residual risks/blockers.
- If implementation cannot proceed, it should return a concrete `blocked` reason rather than silently timing out or waiting indefinitely.
