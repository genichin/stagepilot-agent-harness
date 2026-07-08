# lead -> delivery-runner

## Kickoff rule

This handoff is normally issued by the lead after `confirm-req` completes. A second explicit user kickoff is not required unless the user has asked to hold, defer, or wait for another approval point.

By default, emit this handoff as a persisted kickoff artifact plus a small delivery-state record. Optional Telegram notification may mirror the kickoff for visibility, but notification is not the source of truth.

Artifact creation alone does not start execution. The lead must explicitly launch `delivery-runner` after writing the kickoff artifact/state. In this harness the default launch mechanism is the repo wrapper script `scripts/lead-launch-runner.sh`, which starts `hermes --profile delivery-runner` in a detached `tmux` session.

## Required fields

- approved discovery reference
- approved REQ reference
- project / repo path
- current goal
- explicit scope boundaries
- escalation triggers
- expected reporting cadence or milestones
- kickoff artifact path
- delivery state path

If the handoff is emitted through artifact-backed transport, also set:

- delivery owner target = `delivery-runner`
- initial delivery state = `ready`
- current stage = `kickoff`
- approved reference list in the state record

Kanban transport is forbidden in this harness. Do not emit root kickoff cards or board-based queue state.

## Output expectation

Runner should acknowledge current stage, next artifact, likely blockers, and first execution step.

## Launch rule

- Default launch mode is background execution.
- The lead should launch `delivery-runner` explicitly via `scripts/lead-launch-runner.sh <kickoff_artifact> <delivery_state>`.
- The wrapper starts a detached `tmux` session and runs `hermes --profile delivery-runner chat -q ...` with the kickoff/state paths embedded in the prompt.
- After the Hermes runner process exits, the wrapper validates the delivery-state record and writes externally inspectable `exit_file` + `status_file` results. A root kickoff is not considered complete unless the state reaches lead-visible `done` or explicit `blocked`.
- Detached background launch is the default because runner work is long-lived orchestration; the lead should not block its own session waiting for runner completion.
- If the launch command is not issued, the kickoff remains only a persisted `ready` handoff and the runner has not started.

## Claim rule for default artifact-backed kickoff

The `delivery-runner` has *claimed* the kickoff only when all of the following are true:

1. the runner is the explicit owner target in the delivery state record
2. the delivery state moves from `ready` to `claimed` or `in_progress`
3. the runner updates the state or paired acknowledgment artifact with current stage, next artifact, likely blockers, and first execution step

Reading the artifact without those actions is not a valid claim.

## Optional Telegram notify rule

- Telegram notification is optional and secondary.
- If used, it should include the kickoff artifact path, current stage, and next step.
- The notification may point humans to the artifact/state record, but it does not replace them.

## Queue / hold rule for additional kickoff items

- `delivery-runner` should claim at most one root kickoff item into active execution at a time globally unless the project overlay says otherwise.
- Newly arrived kickoff items for the same runner naturally wait by remaining in `ready`; they are not auto-claimed.
- If the waiting order is ambiguous or materially risky, the runner should leave a lead-visible backlog note in the artifact/state trail or request reprioritization instead of choosing silently.
