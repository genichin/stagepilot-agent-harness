# TREX overlay

## Known conventions

- project-specific lead profile: `trex-dev-lead`
- shared worker profiles: `delivery-runner`, `dev-impl`, `dev-qc`
- root kickoff transport: artifact-backed handoff + delivery state record
- root kickoff launch: lead explicitly starts `delivery-runner` via `scripts/lead-launch-runner.sh`; detached background `tmux` is the default, while an explicitly approved local/reversible fast launch needs both `--allow-fast-degraded` and `--ack-fast-shared-workdir-risk` before it may run foreground/current-workdir.
- root kickoff workspace isolation: `scripts/lead-launch-runner.sh` prepares a per-kickoff delivery branch/worktree so TREX discovery edits in the main checkout do not leak into the runner PR branch
- impl launch default: runner explicitly starts `dev-impl` in foreground via `scripts/runner-launch-impl.sh`
- qc launch default: runner explicitly starts `dev-qc` in foreground via `scripts/runner-launch-qc.sh`
- publication preflight: for PR-bound `guarded` delivery, runner should run `scripts/check-publication-auth.sh --json` from the isolated delivery worktree before substantial impl/QC time; `fast`/`standard` escalate to `guarded` when publication or release-sensitive risk enters scope. Preflight failures escalate early with `publication_auth_missing...`.
- doctor adoption mode: persist `required`, `optional`, or `not-adopted` in each root delivery state; an overlay may supply it only at state creation, and runner/QC classify a missing entrypoint from that state instead of guessing
- optional structured notify: add root-state `notification_targets` only when TREX supplies an approved lead-session or messaging adapter. Each target receives one structured JSON event on stdin; adapter commands, IDs, and event filters are project configuration, while credentials remain outside the artifact/state trail.
- kanban: forbidden. Do not use board/card transport for kickoff, queueing, implementation, QC, or completion.

## Notes

TREX uses the shared worker topology with project-specific lead ownership.

## Merge approval policy

TREX uses risk-based merge approval. A BAT is a delivery slice, not automatically a human approval unit.

### Default: low-risk BATs

- After merge-ready evidence and the required profile/QC controls, the lead may approve and merge a low-risk BAT without a separate user approval request.
- The runner must still return a lead-visible `done` / `merge-ready` hand-back; runner completion is never merge authority.
- Normal REQ approval already authorizes batch grouping, implementation, testing, and QC inside the frozen scope. Do not request user approval during those intermediate steps.

### Required user approval: high-risk merge

The lead must request and record explicit user approval before merging when the PR includes, or has uncertain impact on:

- database schema/data migration, destructive or irreversible data operations
- authentication, authorization, secrets, sensitive data, or security posture
- payment, production messaging, public external side effects, or externally binding API/CLI behavior
- compliance, legal, contractual, or release/rollout commitments
- scope/revision changes, or any other product/release-risk posture that cannot be classified confidently as low-risk

For a high-risk PR, the lead records `merge_approval_mode = user_required`, the applicable `merge_risk_reasons`, the merge-ready evidence, and the user decision in the root delivery trail before merge. Ambiguity fails upward: do not silently downgrade a high-risk or uncertain change to lead-only approval.

### Approval cadence and PR grouping

- A required user approval happens once at merge-ready for the relevant PR, not during implementation, test, or QC steps.
- Do not automatically bundle every BAT from a Discovery into one PR just to reduce approvals. The lead and runner keep PRs reviewable and independently reversible; they may use an explicitly documented grouped PR plan when its cohesion and release posture justify it.
- This policy governs merge authorization only. Release/deployment approval remains a separate lead/user decision under the normal lifecycle controls.

## Overlay guidance for workspace layout

- Core harness only requires isolation between the lead/human primary checkout and the runner delivery worktree.
- Core harness default is repo-local `.worktrees/` when a project does not specify anything else.
- Parent-directory layout decisions such as a top-level project-control folder, `repos/` as the home for main checkouts, or a shared external worktree root are project-adoption decisions and should be documented here.
- If TREX wants `repos/<repo-name>` for lead/human main checkouts and a separate sibling path for runner worktrees, state that override here and pass explicit `--worktree-path` / `--workdir` values when needed.
