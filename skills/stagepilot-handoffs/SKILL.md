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
- approved REQ reference or approved REQ set
- objective
- scope and non-goals
- acceptance definition
- repo/workdir context
- constraints or approvals already granted
- escalation triggers
- expected reporting cadence

For Discovery-level root delivery, also include:
- `root_type=discovery`
- confirmed Discovery id/path
- already Implemented REQs and remaining Approved REQs
- runner obligation to create/adopt a batch queue and execute one batch at a time
- explicit non-goal: do not send the full Discovery as one unsliced direct implementation handoff
- root done definition

For artifact-backed delivery, also include:
- kickoff artifact path
- delivery state path
- `owner_target` (`delivery-runner`)
- `status` (normally `ready`)

Isolation rule for mutable delivery artifacts:
- If the runner is expected to work in an isolated delivery worktree, any kickoff/state/batch queue artifacts that the runner will mutate should be worktree-local or explicitly declared as lead-checkout control-plane artifacts.
- Do not hand the runner absolute mutable artifact paths in the lead/main checkout while instructing it to create delivery docs and PR-bound changes in the isolated worktree; that causes split-brain delivery state.
- If `lead-launch-runner.sh --workdir` is used to relaunch an existing worktree, prefer kickoff/state paths inside that worktree.
- If the launcher auto-prepares a worktree from lead-checkout kickoff/state paths, the handoff must clearly distinguish which artifacts remain lead-visible control-plane state and which project docs must be created in the delivery worktree.

- `current_stage` (`kickoff`)
- `goal`
- `updated_at`
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
- runner explicitly launches `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` for short/simple bounded work
- for non-trivial implementation handoffs, prefer `scripts/runner-launch-impl.sh --supervised <impl_handoff_artifact> <delivery_state>`
- launchers are expected to run in place from the harness repo (often by absolute path) while the runner cwd stays in the target delivery worktree; helper scripts resolve relative to the launcher location, while worker `--workdir`, git evidence, and progress artifacts stay rooted in the target worktree
- supervised mode checkpoints git/progress evidence and extends only on concrete progress; heartbeat-only output does not qualify
- runner should normally slice impl work so concrete progress evidence can appear within about 5 minutes and completion is likely within about 30 minutes
- if a slice is unlikely to finish within about 30 minutes, split it further before launch unless the work is genuinely atomic
- if the work remains genuinely atomic and still cannot reasonably fit inside the default 60-minute supervised cap, use only an explicit long-run supervised exception with larger checkpoint/runtime values and recorded early-progress evidence expectations
- `scripts/runner-launch-impl.sh` supports `--preset default|stretched|long-run` for the standard supervision budgets; explicit minute flags may still override when a justified nonstandard budget is needed
- `--background` remains optional only for materially long-running or resumable child work

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
- runner explicitly launches `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>` for short/simple bounded review work
- for non-trivial QC handoffs, prefer `scripts/runner-launch-qc.sh --supervised <qc_handoff_artifact> <delivery_state>`
- supervised mode checkpoints git/progress evidence and extends only on concrete progress; heartbeat-only output does not qualify
- `--background` remains optional only for materially long-running or resumable child work

### delivery-runner -> lead escalation
Must include:
- `current_stage`
- `status` (normally `blocked`)
- `reason_class`
- `blocker_code`
- optional `blocker_detail`
- blocker summary / exact blocker
- options considered
- required lead decision
- recommended next action
- impact of delay or risk of proceeding
- `evidence_paths`

Recommended reason classes:
- `scope_or_requirements`
- `approval_or_priority`
- `tooling_or_access_blocker`
- `verification_or_release_risk`
- `queue_or_capacity`

### delivery-runner -> lead completion
This handoff is optional by default.

- The canonical required successful completion signal is a lead-visible `done` delivery-state transition on the active root kickoff item plus persisted delivery artifacts/state that the lead can inspect during release review. `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue, not normal successful completion.
- Use an explicit completion summary when it improves handoff clarity or when a project overlay requires it.
- A completion summary should align to the root state by preserving `status=done`, the final `current_stage` (normally `merge-ready`), and direct `evidence_paths` / `pr_ref` where applicable.

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
- [ ] Optional completion-summary behavior is not mistaken for the canonical required successful completion signal.
