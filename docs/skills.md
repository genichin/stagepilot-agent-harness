# Skills in the Harness Repo

This repository keeps StagePilot-related Hermes skills **inside the project** and now serves as the source-of-truth skill catalog for the StagePilot operating model.

## Why

- The operating model and the skills evolve together.
- Handover contracts, role boundaries, SDLC rules, and skill instructions must not drift.
- The repo should be the single review surface for topology and workflow changes.
- A single export path should be enough to provision another Hermes runtime.

## Current skill set

The harness currently carries **25 skills**:

- **3 harness-core skills** authored in this repository
- **21 consolidated StagePilot workflow skills** now maintained in this repository
- **1 operational tooling skill** for doctor execution and triage

### Harness-core skills

| Skill | Purpose |
|---|---|
| `stagepilot-agent-harness` | Umbrella entrypoint for the overall operating harness |
| `stagepilot-role-topology` | Role boundaries, ownership, escalation model |
| `stagepilot-handoffs` | Canonical handover contracts and payload expectations |

### Operational tooling skill

| Skill | Purpose |
|---|---|
| `stagepilot-doctor-ops` | Run, interpret, classify, and rerun `stagepilot-doctor` checks with explicit blocker vs expected-warning triage |

### Imported StagePilot workflow skills

#### Discovery and intake

| Skill | Purpose |
|---|---|
| `bootstrap-baseline` | Initialize baseline docs and active indexes before the first real Discovery |
| `new-discovery` | Create or update a Discovery entry for a real change |
| `review-discovery` | Non-gating quality review for a Discovery before confirmation |
| `confirm-discovery` | Revalidate and promote a Discovery to confirmed |
| `suggest-next-discovery` | Recommend the next Discovery candidate from feedback, gaps, or doctor output |

#### Requirements and change management

| Skill | Purpose |
|---|---|
| `draft-req` | Draft REQ documents from a confirmed Discovery |
| `confirm-req` | Approve REQ documents for delivery input |
| `change-req` | Apply controlled changes to existing REQs |
| `confirm-req-implemented` | Sync approved REQs to Implemented after merge-backed delivery evidence exists |

#### Batch planning and delivery

| Skill | Purpose |
|---|---|
| `suggest-batch-reqs` | Recommend cohesive REQ groupings for a delivery batch |
| `draft-batch` | Create a new batch from approved REQs |
| `draft-batch-planning` | Fill planning.md for an existing batch |
| `draft-batch-design` | Fill design.md for an existing batch |
| `run-batch-implementation` | Execute implementation work for a confirmed batch |
| `draft-batch-verification` | Draft verification evidence for a batch |
| `confirm-batch-verification` | Promote a verified batch to release-candidate |
| `run-batch-delivery` | Orchestrate the full delivery chain for one batch |

#### Release and feedback loop

| Skill | Purpose |
|---|---|
| `draft-release` | Create a release document from release-candidate batches |
| `confirm-release` | Approve a release plan |
| `capture-release-feedback` | Record post-release observations and follow-up inputs |

#### Top-level orchestration

| Skill | Purpose |
|---|---|
| `run-sdlc` | Route the repository to the next appropriate StagePilot skill from current state |

## Recommended workflow

1. Update core docs first.
2. Reflect the same operational rule in the relevant `SKILL.md` file.
3. When StagePilot SDLC behavior changes, update both the imported workflow skill and any overlapping harness-core or operational skill.
4. Run `python3 scripts/verify_structure.py`.
5. Export skills with `python3 scripts/export_skills.py --dest <path>` when you want a Hermes runtime copy.

## Repository policy for the `skills/` directory

- `skills/` should contain **skill directories only**.
- Legacy external-pack root files such as `skills/README.md` and `skills/CHANGELOG.md` are repository documentation, not skills.
- In the harness repo, catalog and governance notes live under `docs/` so exports stay directory-oriented and the `skills/` tree remains clean.

## Optimization notes

- The imported StagePilot skills, the harness-core skills, and the doctor operations skill are **complementary**, not exact duplicates.
- `run-sdlc` and `run-batch-delivery` remain distinct entrypoints.
- `review-discovery` remains useful as a non-state-changing quality gate even though `confirm-discovery` performs deeper approval work.
- Skills that explicitly depend on doctor checks now link to `stagepilot-doctor-ops` through `related_skills` metadata.
- Gaps and merge candidates are tracked in `docs/skill-audit.md`.
