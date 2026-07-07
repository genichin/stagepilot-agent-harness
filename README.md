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
| `lead` | Discovery drafting, Discovery approval, REQ drafting, REQ approval, prioritization, user collaboration | Getting trapped in long-running delivery execution |
| `delivery-runner` | Choose delivery grouping inside approved REQ scope and orchestrate the delivery chain after approved Discovery and approved REQ handoff | Acting as product owner or silently changing scope |
| `dev-impl` | Implement approved scope and provide concrete evidence | Declaring acceptance by itself |
| `dev-qc` | Independently verify acceptance, gaps, and regressions | Becoming a rubber stamp for implementation |

### Canonical handovers

Use these as the normative defaults:

- `lead` owns Discovery drafting/approval and REQ drafting/approval.
- `delivery-runner` starts after approved Discovery + approved REQ handoff and owns delivery orchestration within that approved scope.
- After `confirm-req`, the lead may auto-kick off delivery unless the user explicitly asked to hold, defer, batch later, or wait.
- Kanban is required by default only at the `lead -> delivery-runner` root boundary; downstream impl/QC handoffs are transport-agnostic unless an overlay opts into child cards.
- A kanban kickoff is claimed only when the root card is assigned to `delivery-runner`, moved from `ready` to `running`, and acknowledged by the runner.
- Default runner concurrency is one root kickoff card in `running` globally across boards; additional kickoff cards remain queued in `ready`.
- One root kickoff card maps to one primary PR by default; the runner may open/update it, but the default merge decision belongs to the lead after `confirm-req-implemented`.
- The standard path includes `delivery-runner -> dev-qc` before `confirm-batch-verification`.
- QC retry budget is 3 verdict cycles for the same acceptance scope; the 3rd unresolved verdict escalates to `lead`.
- Required completion signal: root kickoff reaches lead-visible `done` with persisted delivery artifacts. Separate completion summary is optional by default.

- `lead -> delivery-runner`
- `delivery-runner -> dev-impl`
- `delivery-runner -> dev-qc`
- `delivery-runner -> lead` escalation
- `delivery-runner -> lead` completion summary (optional)

### Default handoff chain

| Step | Handoff | Default meaning |
|---|---|---|
| 1 | `lead -> delivery-runner` | Approved Discovery + Approved REQ handoff starts delivery orchestration. |
| 2 | `delivery-runner -> dev-impl` | Implementation worker executes the approved batch scope and returns concrete change/test evidence. |
| 3 | `delivery-runner -> dev-qc` | Independent QC reviews verification target, acceptance mapping, evidence bundle, and suspicious areas before batch verification approval. |
| 4 | `delivery-runner -> lead` escalation | Scope, priority, approval, or release-policy questions go back to the lead instead of being decided silently in delivery. |
| 5 | `delivery-runner -> lead` completion summary (optional) | Optional wrap-up message after `confirm-req-implemented`; the required completion signal is the root kickoff moving to lead-visible `done` with persisted delivery artifacts available for release review. |

#### Visual chain

```text
┌──────────────┐
│    lead      │
│ Discovery /  │
│ REQ approval │
└──────┬───────┘
       │ approved Discovery + approved REQ
       ▼
┌──────────────┐
│delivery-runner│
│ batch grouping │
│ + orchestration│
└───┬────────┬──┘
    │        │
    │ impl   │ escalation / release-policy / scope / priority
    ▼        └──────────────────────────────────────────────► lead
┌──────────┐
│ dev-impl │
│ changes +│
│ evidence │
└────┬─────┘
     │ verification target + evidence bundle
     ▼
┌──────────┐
│  dev-qc  │
│independent│
│ verification │
└────┬─────┘
     │ QC verdict
     ▼
┌──────────────────────────────┐
│ confirm-batch-verification   │
└──────────────┬───────────────┘
               │ verification approved
               ▼
┌──────────────────────────────┐
│  confirm-req-implemented     │
└──────────────┬───────────────┘
               │ delivery complete
               ▼
┌──────────────┐
│    lead      │
│ draft-release│
│confirm-release│
└──────────────┘
```

#### Fast mental model

`lead` → `delivery-runner` → `dev-impl` → `dev-qc` → `confirm-batch-verification` → `confirm-req-implemented` → `lead`

Notes:

- `dev-impl` and `dev-qc` are intentionally distinct; QC is not an extension of implementation.
- Only a low-risk `batch-lite` path may skip explicit QC handoff, and that waiver must be documented with skip reason and residual risk in verification output.
- Escalate immediately instead of spending retry budget when the issue is caused by REQ ambiguity, conflicting acceptance criteria, scope mismatch, release-risk posture, or any decision outside runner authority.
- Waiver is not allowed for core functional failures, security/privacy issues, data integrity risks, or other unresolved blocking defects.
- Release-family work resumes with the lead after runner-managed delivery reaches `confirm-req-implemented`.

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
2. Use `docs/profile-bootstrap.md` when turning the harness into real Hermes profiles.
3. Use `docs/model-policy.md` for the default role-to-model mapping.
4. Copy or adapt the baseline role SOUL templates from `profiles/templates/`.
5. Use the handover templates in `templates/` and the contracts in `handoffs/`.
6. Install or export the repo-backed skills when you want Hermes profiles to consume the harness directly.
7. Place project-specific deviations under `projects/<project>/` rather than mutating core assumptions unnecessarily.
8. Run the verification checklists before adopting a new topology.

## Initial scope

This scaffold now captures both the operating model and its agent-facing skill layer, with hooks for:

- kanban-driven orchestration
- Telegram/home-channel notification rules
- profile bootstrap automation
- project overlays such as TREX
- future skill export/install automation

## Status

Harness scaffold plus initial in-repo StagePilot skill sources created by Hermes Agent.
