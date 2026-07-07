# stagepilot-agent-harness

A reusable operating harness for StagePilot-style multi-agent delivery using four core roles:

- `lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

This repository standardizes role boundaries, handover contracts, state transitions, notification hooks, profile templates, **and skill sources** so the operating model can be reused across projects instead of living only in chat context.

## Goals

- Keep the **lead** user-facing and decision-oriented.
- Keep the **delivery-runner** responsible for orchestration across the delivery chain.
- Keep **implementation** and **QC** as distinct worker roles.
- Make handovers explicit, reviewable, and reusable.
- Treat kanban state + notifications as operational signals rather than informal chat memory.
- Support project-specific overlays without cloning the full operating model per project.
- Keep docs, templates, SOUL baselines, and Hermes skills under a single source of truth.

## Repository Layout

```text
stagepilot-agent-harness/
  docs/                    Architecture and operating model docs
  roles/                   Role charters and boundaries
  handoffs/                Required handover contracts and examples
  templates/               Kickoff / escalation / completion templates
  skills/                  In-repo Hermes skill sources for this harness
  profiles/templates/      Baseline SOUL.md templates by role
  scripts/                 Harness helper scripts
  playbooks/               Operational runbooks
  verification/            Checklists for role and handover quality
  projects/trex/           TREX-specific overlay and examples
```

## Core Model

### Roles

| Role | Primary purpose | Must avoid |
|---|---|---|
| `lead` | Discovery, approval, prioritization, user collaboration | Getting trapped in long-running delivery execution |
| `delivery-runner` | Orchestrate approved work through the delivery chain | Acting as product owner or silently changing scope |
| `dev-impl` | Implement approved scope and provide concrete evidence | Declaring acceptance by itself |
| `dev-qc` | Independently verify acceptance, gaps, and regressions | Becoming a rubber stamp for implementation |

### Canonical handovers

- `lead -> delivery-runner`
- `delivery-runner -> dev-impl`
- `delivery-runner -> dev-qc`
- `delivery-runner -> lead` escalation
- `delivery-runner -> lead` completion summary

## Skill strategy

This repository now treats `skills/` as part of the harness source tree and as the source-of-truth StagePilot skill catalog.

- The repo holds the editable source of StagePilot-related Hermes skills.
- Docs in `docs/`, contracts in `handoffs/`, and role definitions in `roles/` remain the human-readable operating model.
- Skills package the same model into agent-facing instructions that can be copied or symlinked into a Hermes profile later.
- `scripts/export_skills.py` can export the in-repo skills into a target Hermes skills directory.
- `docs/skills.md` tracks the current catalog and `docs/skill-audit.md` tracks overlap, gap, and optimization analysis.

The current catalog contains:

- **3 harness-core skills**
  - `skills/stagepilot-agent-harness/`
  - `skills/stagepilot-role-topology/`
  - `skills/stagepilot-handoffs/`
- **1 operational tooling skill**
  - `skills/stagepilot-doctor-ops/`
- **21 imported StagePilot workflow skills**
  - discovery, requirements, batch, release, and orchestration skills imported from `stage-pilot/skills/`

Repository policy: `skills/` should contain skill directories only. Catalog/audit prose belongs under `docs/`.

## Recommended Use

1. Start from the docs in `docs/` and `roles/`.
2. Copy or adapt the baseline role SOUL templates from `profiles/templates/`.
3. Use the handover templates in `templates/` and the contracts in `handoffs/`.
4. Install or export the repo-backed skills when you want Hermes profiles to consume the harness directly.
5. Place project-specific deviations under `projects/<project>/` rather than mutating core assumptions unnecessarily.
6. Run the verification checklists before adopting a new topology.

## Initial scope

This scaffold now captures both the operating model and its agent-facing skill layer, with hooks for:

- kanban-driven orchestration
- Telegram/home-channel notification rules
- profile bootstrap automation
- project overlays such as TREX
- future skill export/install automation

## Status

Harness scaffold plus initial in-repo StagePilot skill sources created by Hermes Agent.
