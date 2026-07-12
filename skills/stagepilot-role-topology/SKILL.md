---
name: stagepilot-role-topology
description: Use when defining or reviewing ownership boundaries, escalation points, and scope limits across the StagePilot lead, delivery-runner, dev-impl, and dev-qc roles.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, role-topology, lead, delivery-runner, dev-impl, dev-qc]
    related_skills: [stagepilot-agent-harness, stagepilot-handoffs]
---

# StagePilot Role Topology

## Overview

This skill focuses on the role graph itself: who owns what, what each role must avoid, and when work must escalate rather than silently continue.

## When to Use

Use when you need to:

- assign responsibilities among lead, runner, impl, and qc;
- detect role drift or overlap;
- decide whether a task belongs to orchestration, implementation, or verification;
- review whether an operating design preserves independence between implementation and QC.

## Boundary rules

### Lead
- Owns discovery, approval, prioritization, and user-facing tradeoffs.
- Should remain the control tower, not the delivery worker.
- Must receive escalations for ambiguity, blocked decisions, or optional completion summaries needing human judgment.
- Owns the default merge decision for kickoff-aligned pull requests before post-merge `confirm-req-implemented`.

### Delivery-runner
- Owns execution choreography across the delivery chain.
- Owns batch grouping and delivery slicing within already-approved scope.
- May break work into handovers, route tasks, collect evidence, and report status.
- Must pause and escalate when authority is missing.
- Must not silently redefine scope or acceptance criteria.
- Should normally have at most one root kickoff item in active execution globally unless a project overlay documents another concurrency model.
- Uses artifact-backed root handoff at the `lead -> delivery-runner` boundary, with optional Telegram notification for visibility; downstream impl/QC handoffs stay transport-agnostic, must not use kanban, and are launched explicitly by the runner as bounded worker calls.
- Runs each active root kickoff in a dedicated delivery git worktree/branch by default so lead/human Discovery edits in the main checkout stay separate from PR-branch delivery execution.
- Default downstream launch commands are `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` and `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>` in foreground mode unless an overlay documents a long-running detached exception.
- Should organize Git delivery around one primary pull request per active root kickoff by default.
- May open and update the kickoff PR during delivery, but does not own the default merge decision.
- Owns the standard delivery chain through merge-ready hand-back, including default QC handoff before `confirm-batch-verification`.
- Must enforce the default QC retry cap of 3 verdict cycles for the same acceptance scope, then escalate instead of looping indefinitely.

### Dev-impl
- Owns changes to code/config/artifacts within approved scope.
- Must provide concrete evidence of what changed and what was tested.
- When runner provides a patch-ready implementation-context, must execute patch-first: exact target snippets, then edit/write or concrete blocker; not broad research.
- Must not self-certify final acceptance.

### Dev-qc
- Owns independent verification of acceptance and regressions.
- Should report evidence, residual risk, and gaps.
- Must not become a formality attached to implementation.

## Escalation heuristics

Escalate to `lead` when:

- a decision changes scope, priority, acceptance, or release readiness;
- the runner cannot resolve a blocker with existing authority;
- implementation findings invalidate the kickoff assumptions;
- QC finds a gap that needs product-level tradeoff;
- the same QC gap remains unresolved on the 3rd verdict for the same acceptance scope;
- merge timing, release posture, or go/no-go judgment is needed.

## Common Pitfalls

1. **Runner acting like product owner.** Delivery planning inside approved scope is allowed; changing scope, priority, or approval policy is not.
2. **Lead staying inside implementation loops too long.** This reduces leverage and muddies ownership.
3. **QC reviewing its own implementation path.** Keep independence visible.
4. **Using titles without contracts.** A role name is meaningless if its input/output expectations are not explicit.
5. **Treating runner completion as automatic merge authorization.** Merge timing belongs to lead-owned release judgment by default.

## Verification Checklist

- [ ] Each role has a clear owner, mandate, and stop boundary.
- [ ] Escalation rules route authority questions back to lead.
- [ ] Impl and QC remain separable in both responsibility and evidence.
- [ ] The topology can be explained without relying on unstated tribal knowledge.
- [ ] Root concurrency, PR boundary, merge ownership, and QC retry-cap rules are explicit rather than implied.
