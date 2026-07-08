---
name: stagepilot-agent-harness
description: Use when setting up, refining, or operating the StagePilot multi-agent harness with lead, delivery-runner, dev-impl, and dev-qc roles.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, harness, multi-agent, roles, handoffs, artifacts]
    related_skills: [stagepilot-role-topology, stagepilot-handoffs, stagepilot-doctor-ops]
---

# StagePilot Agent Harness

## Overview

This skill is the umbrella entrypoint for the `stagepilot-agent-harness` operating model. Use it when the task is about shaping, adopting, or operating the four-role delivery topology built around:

- `lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

It compresses the repository's core operating assumptions into agent-facing guidance so Hermes can act consistently without relying on ad-hoc chat memory.

## When to Use

Use this skill when you need to:

- design or refine the StagePilot role topology;
- bootstrap a new project onto the harness;
- align SOUL templates, handoff contracts, and playbooks;
- decide whether a rule belongs in core harness vs project overlay;
- keep repo docs and runtime skills synchronized.

Do not use this skill as a substitute for project-specific implementation instructions. Pair it with a project overlay or delivery skill when work moves into concrete repo changes.

## Core operating model

### Role intent

| Role | Owns | Must not own |
|---|---|---|
| `lead` | user communication, prioritization, approval, ambiguity resolution | long-running delivery execution |
| `delivery-runner` | batch grouping inside approved REQ scope, orchestration, sequencing, handovers, escalation, completion reporting | product authority, silent scope changes |
| `dev-impl` | implementation, evidence, local validation | acceptance sign-off |
| `dev-qc` | independent verification, defect surfacing, release confidence | implementation ownership |

### Default operating rules that should stay synchronized with core docs

- After `confirm-req`, the lead may issue `lead -> delivery-runner` kickoff automatically unless the user explicitly asked to hold, defer, batch later, or wait for another confirmation point.
- The default `lead -> delivery-runner` root transport is a kickoff artifact plus delivery-state record; optional Telegram notification may mirror kickoff for visibility, but notification is not the source of truth.
- The default root launcher (`scripts/lead-launch-runner.sh`) prepares a dedicated git worktree/branch per kickoff and runs `delivery-runner` inside it so lead/human Discovery edits in the main checkout do not contaminate the delivery PR branch.
- Downstream `delivery-runner -> dev-impl` and `delivery-runner -> dev-qc` handoffs are transport-agnostic by default and must not use kanban.
- The default downstream launch path is explicit runner-owned worker execution: `scripts/runner-launch-impl.sh <impl_handoff_artifact> <delivery_state>` and `scripts/runner-launch-qc.sh <qc_handoff_artifact> <delivery_state>`.
- Default downstream mode is foreground bounded execution; `--background` is optional only for materially long-running or resumable child work.
- Unless a project overlay documents otherwise, a `delivery-runner` should have at most one root kickoff item in active execution globally.
- By default, one root kickoff item maps to one primary pull request. Any one-kickoff-to-many-PR split should be explicit in the project overlay or kickoff note.
- Live post-kickoff Discovery/REQ edits must not flow automatically into the runner delivery branch; importing them requires explicit lead re-handoff or sync direction.
- The runner may open and update that PR during delivery, but the default merge decision belongs to the lead after hand-back at `confirm-req-implemented`, during release-stage review.
- The standard delivery path includes an independent `delivery-runner -> dev-qc` handoff before `confirm-batch-verification`.
- Only a low-risk `batch-lite` path may skip explicit QC handoff, and the skip reason plus residual risk must be documented in verification output.
- The default QC retry cap is 3 verdict cycles for the same acceptance scope (initial review plus up to 2 rework/re-review loops).
- If the same QC gap remains unresolved on the 3rd verdict, the runner must escalate to the lead instead of continuing an unbounded loop.
- The canonical required successful completion signal is a lead-visible `done` delivery-state transition on the active root kickoff item plus persisted delivery artifacts/state. `archived` is reserved for terminal historical closure of a root kickoff that should no longer continue, not normal successful completion. A separate completion summary is optional by default.

### Harness layering

Use this decision rule:

1. **Core harness** if the rule should apply across projects.
2. **Project overlay** if the rule depends on one codebase, one board, one team, or one delivery chain.
3. **Profile template** if the rule belongs in role behavior at runtime.
4. **Skill text** if the agent needs the rule compressed into execution guidance.

## Required working style

1. Read the relevant files in `docs/`, `roles/`, `handoffs/`, and `projects/<name>/` before changing the model.
2. Keep role boundaries explicit; if a workflow blurs roles, document the exception and who is accountable.
3. Prefer canonical handovers over informal narration.
- 4. Keep blocked/unblocked/completed semantics externally inspectable through artifacts and state.
5. When you update a core operating rule, update the matching skill source in this repository in the same change.

## Common Pitfalls

1. **Treating the skill as the only source of truth.** The repository is authoritative; the skill is a compressed execution interface.
2. **Stuffing project-specific policy into core harness language.** Put those rules under `projects/<name>/` unless they truly generalize.
3. **Letting the runner become a shadow lead.** Runner may choose delivery grouping inside approved scope, but does not redefine scope, priority, or approvals.
4. **Collapsing impl and QC into one worker mindset.** Independent verification is part of the operating model, not optional ceremony.
5. **Updating core docs without updating the corresponding skills/templates.** This creates execution drift between human docs and runtime guidance.

## Verification Checklist

- [ ] The role or workflow change maps cleanly to core harness, profile template, or project overlay.
- [ ] Updated docs and updated skill text still say the same thing.
- [ ] Role boundaries remain explicit for lead, runner, impl, and qc.
- [ ] Handover or state changes are backed by artifacts, not only chat.
- [ ] Root handoff, PR-boundary, merge-ownership, QC-retry, and completion-signal rules still match the current core docs.
