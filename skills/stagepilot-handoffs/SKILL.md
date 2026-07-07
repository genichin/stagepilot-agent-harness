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
- objective
- scope and non-goals
- acceptance definition
- constraints or approvals already granted
- expected reporting cadence

### delivery-runner -> dev-impl
Must include:
- implementation objective
- files/systems likely affected
- acceptance target
- explicit out-of-scope items
- evidence expected back from impl

### delivery-runner -> dev-qc
Must include:
- verification target
- acceptance criteria to test
- known risk areas
- required evidence format
- rules for fail vs conditional pass vs pass

### delivery-runner -> lead escalation
Must include:
- current state
- exact blocker
- options considered
- decision required
- impact of delay or wrong choice

### delivery-runner -> lead completion
Must include:
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

## Common Pitfalls

1. **Narrative-only handovers.** They sound helpful but are hard to validate.
2. **Missing acceptance fields.** Receivers cannot decide done-ness from vibes.
3. **Combining escalation with a silent decision.** If authority is needed, surface it directly.
4. **QC requests without risk framing.** This weakens independent verification.

## Verification Checklist

- [ ] The receiving role could act without rereading the whole conversation.
- [ ] Objective, scope, evidence, and decision points are explicit.
- [ ] Escalations clearly state what authority is being requested.
- [ ] Completion summaries separate results from residual risk.
