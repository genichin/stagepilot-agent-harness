---
name: stagepilot-agent-harness
description: Use when setting up, refining, or operating the StagePilot multi-agent harness with lead, delivery-runner, dev-impl, and dev-qc roles.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, harness, multi-agent, roles, handoffs, kanban]
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
| `delivery-runner` | orchestration, sequencing, handovers, escalation, completion reporting | product authority, silent scope changes |
| `dev-impl` | implementation, evidence, local validation | acceptance sign-off |
| `dev-qc` | independent verification, defect surfacing, release confidence | implementation ownership |

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
4. Keep blocked/unblocked/completed semantics externally inspectable through artifacts, state, or kanban.
5. When you update a core operating rule, update the matching skill source in this repository in the same change.

## Common Pitfalls

1. **Treating the skill as the only source of truth.** The repository is authoritative; the skill is a compressed execution interface.
2. **Stuffing project-specific policy into core harness language.** Put those rules under `projects/<name>/` unless they truly generalize.
3. **Letting the runner become a shadow lead.** Runner coordinates execution but does not redefine scope or approvals.
4. **Collapsing impl and QC into one worker mindset.** Independent verification is part of the operating model, not optional ceremony.

## Verification Checklist

- [ ] The role or workflow change maps cleanly to core harness, profile template, or project overlay.
- [ ] Updated docs and updated skill text still say the same thing.
- [ ] Role boundaries remain explicit for lead, runner, impl, and qc.
- [ ] Handover or state changes are backed by artifacts, not only chat.
