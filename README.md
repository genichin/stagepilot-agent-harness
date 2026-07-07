# stagepilot-agent-harness

A reusable operating harness for StagePilot-style multi-agent delivery using four core roles:

- `lead`
- `delivery-runner`
- `dev-impl`
- `dev-qc`

This repository standardizes role boundaries, handover contracts, state transitions, notification hooks, profile templates, and project overlays so the operating model can be reused across projects instead of living only in chat context.

## Goals

- Keep the **lead** user-facing and decision-oriented.
- Keep the **delivery-runner** responsible for orchestration across the delivery chain.
- Keep **implementation** and **QC** as distinct worker roles.
- Make handovers explicit, reviewable, and reusable.
- Treat kanban state + notifications as operational signals rather than informal chat memory.
- Support project-specific overlays without cloning the full operating model per project.

## Repository Layout

```text
stagepilot-agent-harness/
  docs/                    Architecture and operating model docs
  roles/                   Role charters and boundaries
  handoffs/                Required handover contracts and examples
  templates/               Kickoff / escalation / completion templates
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

## Recommended Use

1. Start from the docs in `docs/` and `roles/`.
2. Copy or adapt the baseline role SOUL templates from `profiles/templates/`.
3. Use the handover templates in `templates/` and the contracts in `handoffs/`.
4. Place project-specific deviations under `projects/<project>/` rather than mutating core assumptions unnecessarily.
5. Run the verification checklists before adopting a new topology.

## Initial scope

This initial scaffold captures the operating model and leaves hooks for:

- kanban-driven orchestration
- Telegram/home-channel notification rules
- profile bootstrap automation
- project overlays such as TREX

## Status

Initial scaffold created by Hermes Agent.
