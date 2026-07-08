---
name: stagepilot-handoffs
description: Use when drafting, reviewing, or enforcing canonical StagePilot handover payloads between lead, delivery-runner, dev-impl, and dev-qc.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, handoffs, kickoff, escalation, completion, contracts]
    related_skills: [stagepilot-agent-harness, stagepilot-role-topology]
---

# StagePilot Handoffs

## Overview

This skill standardizes how work crosses role boundaries inside the StagePilot harness. The goal is to make handovers self-contained, reviewable, and testable rather than implied through chat context.

## When to Use

Use when you need to:

- draft a kickoff from lead to runner;
- route implementation work from runner to impl;
- request verification from runner to qc;
- escalate a blocker back to lead;
- prepare a completion summary for lead or the user.

## Canonical handovers

### lead -> delivery-runner
Must include:
- approved Discovery reference
- approved REQ reference
- objective
- scope and non-goals
- acceptance definition
- repo/workdir context
- constraints or approvals already granted
- escalation triggers
- expected reporting cadence

For artifact-backed delivery, also include:
- kickoff artifact path
- delivery state path
- delivery owner target (`delivery-runner`)
- initial delivery state (normally `ready`)
- isolated delivery worktree / branch note (explicit or auto-prepared by launcher)
- optional Telegram notify destination/thread
- queue note when another root kickoff is already active for the same runner

### delivery-runner -> dev-impl
Must include:
- impl handoff artifact path
- root delivery state path
- implementation objective
- files/systems likely affected
- acceptance target
- explicit out-of-scope items
- evidence expected back from impl

Default execution rule:
- runner explicitly launches `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>`
- default mode is foreground bounded worker execution
- use `--background` only for materially long-running or resumable child work

### delivery-runner -> dev-qc
Must include:
- qc handoff artifact path
- root delivery state path
- verification target
- acceptance criteria to test
- known risk areas
- required evidence format
- rules for fail vs conditional pass vs pass

Default execution rule:
- runner explicitly launches `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>`
- default mode is foreground bounded worker execution
- use `--background` only for materially long-running or resumable child work

### delivery-runner -> lead escalation
Must include:
- current state
- exact blocker
- options considered
- decision required
- impact of delay or wrong choice

### delivery-runner -> lead completion
This handoff is optional by default.

- The canonical required completion signal is a lead-visible `done` delivery-state transition on the active root kickoff item plus persisted delivery artifacts/state that the lead can inspect during release review.
- Use an explicit completion summary when it improves handoff clarity or when a project overlay requires it.

If a completion summary is sent, it should include:
- original objective
- delivered result
- evidence summary
- residual risk or follow-up
- recommendation for next action

## Writing rules

1. Assume the receiving role has no hidden chat context.
2. Prefer bulletized fields over prose blobs.
3. Separate facts, evidence, and recommendations.
4. If a handover changes authority, treat it as escalation.
5. If a handover cannot be audited later, it is not good enough.
6. Do not silently convert an optional completion summary into a mandatory completion gate unless the project overlay explicitly says so.

## Common Pitfalls

1. **Narrative-only handovers.** They sound helpful but are hard to validate.
2. **Missing acceptance fields.** Receivers cannot decide done-ness from vibes.
3. **Combining escalation with a silent decision.** If authority is needed, surface it directly.
4. **QC requests without risk framing.** This weakens independent verification.
5. **Treating completion summary as the only completion signal.** The default required signal is the root kickoff reaching lead-visible `done` with inspectable delivery artifacts.

## Verification Checklist

- [ ] The receiving role could act without rereading the whole conversation.
- [ ] Objective, scope, evidence, and decision points are explicit.
- [ ] Escalations clearly state what authority is being requested.
- [ ] Any completion summary separates results from residual risk.
- [ ] Optional completion-summary behavior is not mistaken for the canonical required completion signal.
