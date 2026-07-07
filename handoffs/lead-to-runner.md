# lead -> delivery-runner

## Kickoff rule

This handoff is normally issued by the lead after `confirm-req` completes. A second explicit user kickoff is not required unless the user has asked to hold, defer, or wait for another approval point.

When the harness uses kanban-backed delivery, emit this handoff as a root kickoff card on the project's canonical board.

## Required fields

- approved discovery reference
- approved REQ reference
- project / repo path
- current goal
- explicit scope boundaries
- escalation triggers
- expected reporting cadence or milestones

If the handoff is emitted through kanban, also set:

- canonical board name
- root kickoff card state = `ready`
- explicit assignee/owner target = `delivery-runner`
- queue note if another root kickoff is already `running` for the same runner

## Output expectation

Runner should acknowledge current stage, next artifact, likely blockers, and first execution step.

## Claim rule for kanban-backed kickoff

The `delivery-runner` has *claimed* the kickoff only when all of the following are true:

1. the runner is the explicit assignee/owner of the root kickoff card
2. the root kickoff card moves from `ready` to `running`
3. the runner posts an acknowledgment update covering current stage, next artifact, likely blockers, and first execution step

Reading a board card without those actions is not a valid claim.

## Queue / hold rule for additional kickoff cards

- `delivery-runner` should claim at most one root kickoff card into `running` at a time globally across project boards unless the project overlay says otherwise.
- Newly arrived kickoff cards for the same runner naturally wait by remaining in `ready`; they are not auto-claimed.
- If the waiting order is ambiguous or materially risky, the runner should leave a lead-visible backlog note or request reprioritization instead of choosing silently.
