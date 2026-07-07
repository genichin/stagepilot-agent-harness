# StagePilot Skill Audit

## Scope

This audit records the consolidation that made this repository the canonical skill catalog.

It compares:

- the historical StagePilot workflow-skill inventory that was consolidated
- `stagepilot-agent-harness/skills/` as the current source-of-truth catalog

## Inventory result

| Source | Count | Notes |
|---|---:|---|
| Historical StagePilot workflow inventory | 21 | Full workflow catalog that was consolidated into this repo |
| Existing harness-core skills | 3 | Topology, handoff, and harness umbrella skills |
| Added operational tooling skills | 1 | `stagepilot-doctor-ops` |
| `stagepilot-agent-harness/skills/` current total | 25 | 21 imported + 3 harness-core + 1 operational |

Migration check result: **all 21 StagePilot skills are present in `stagepilot-agent-harness/skills/`**.

## Imported skill families

### Discovery family
- `bootstrap-baseline`
- `new-discovery`
- `review-discovery`
- `confirm-discovery`
- `suggest-next-discovery`

### Requirements family
- `draft-req`
- `confirm-req`
- `change-req`
- `confirm-req-implemented`

### Batch family
- `suggest-batch-reqs`
- `draft-batch`
- `draft-batch-planning`
- `draft-batch-design`
- `run-batch-implementation`
- `draft-batch-verification`
- `confirm-batch-verification`
- `run-batch-delivery`

### Release family
- `draft-release`
- `confirm-release`
- `capture-release-feedback`

### Orchestration family
- `run-sdlc`

### Harness-core family
- `stagepilot-agent-harness`
- `stagepilot-role-topology`
- `stagepilot-handoffs`

### Operational tooling family
- `stagepilot-doctor-ops`

## Duplication / redundancy assessment

### Exact duplicates

No exact duplicate skill names or 1:1 duplicate responsibilities were found across the imported StagePilot workflow skills, the harness-core skills, and the new doctor operations skill.

### Partial overlap candidates

| Skills | Overlap type | Current recommendation |
|---|---|---|
| `run-sdlc` vs `run-batch-delivery` | Both orchestrate multi-step flow | **Keep both**. `run-sdlc` is cross-lifecycle routing; `run-batch-delivery` is batch-scoped execution chaining. |
| `review-discovery` vs `confirm-discovery` | Both inspect Discovery quality | **Keep both**. `review-discovery` is a non-gating review helper; `confirm-discovery` performs approval/state transition. |
| `stagepilot-agent-harness` vs imported SDLC skills | Both discuss StagePilot operating behavior | **Keep both**. The harness skill is topology/operating-model guidance; the imported skills are concrete SDLC procedures. |
| `stagepilot-doctor-ops` vs doctor guidance embedded in workflow skills | Both mention doctor checks | **Keep both**. Embedded guidance stays lightweight, while `stagepilot-doctor-ops` is the dedicated execution/triage manual. |

### Skills that look easy to delete but should not be removed yet

| Skill | Why it should stay |
|---|---|
| `bootstrap-baseline` | It covers first-run repository bootstrapping and cross-cutting baseline docs, which `new-discovery` does not replace. |
| `suggest-batch-reqs` | It preserves a distinct batch-grouping analysis step before batch creation; even with runner-owned selection, separating recommendation from batch creation keeps rationale and escalation points visible. |
| `confirm-req-implemented` | It enforces REQ/document state sync after delivery evidence exists; this is distinct from batch verification itself. |
| `stagepilot-doctor-ops` | Doctor behavior is reused by many workflow skills, so centralizing triage logic reduces duplicated interpretation rules. |

## Unnecessary skill assessment

At the current catalog size, there is **no clearly unnecessary skill** that can be removed without losing a meaningful lifecycle boundary, quality-control step, or operational validation pattern.

The better optimization is:

1. clear grouping,
2. explicit related-skill metadata,
3. centralized operational guidance,
4. repo-level governance docs.

## Ancillary file policy

The imported external-pack root files `skills/README.md` and `skills/CHANGELOG.md` were useful as migration input, but they are **not part of the canonical harness skill tree**.

Policy going forward:

- `skills/` contains skill directories only;
- catalog description belongs in `docs/skills.md`;
- audit/governance notes belong in `docs/skill-audit.md`;
- pack-level history should be recorded at repository level rather than mixed into the runtime skill directory.

## Missing skill opportunities

The current catalog still has meaningful gaps around operational tooling that already exists in `stage-pilot/tools/` or is implied by the workflow.

### Highest remaining additions

| Proposed skill | Why it is needed | Grounding |
|---|---|---|
| `stagepilot-bootstrap-seed-ops` | Bootstrap seed generation already exists as a script, but there is still no dedicated skill that explains when to seed, how to answer prompts, and how to validate the resulting baseline YAML plus generated docs. | `stage-pilot/tools/stagepilot-bootstrap-seed.py`; referenced from `bootstrap-baseline` and `stage-pilot/README.md` |
| `stagepilot-skill-catalog-governance` | Now that this repo is the source-of-truth catalog, a maintenance skill for import/update/export/audit workflow would reduce drift and make future sync decisions explicit. | Needed by the repo-backed catalog model in this repository |

### Lower-priority additions

| Proposed skill | Why it may help |
|---|---|
| `stagepilot-release-triage` | Could separate release follow-up classification from document authoring when release volume grows. |
| `stagepilot-baseline-doc-maintenance` | Could centralize upkeep rules for `project-structure`, `runtime-flows`, `interface-contract`, and `data-model` if those docs start drifting often. |

## Recommended target model

1. Keep the **25 current skills** in the harness repo.
2. Treat the **21 imported StagePilot skills** as the canonical SDLC workflow layer.
3. Treat the **3 harness-core skills** as the canonical multi-agent operating layer.
4. Treat **`stagepilot-doctor-ops`** as the canonical validation/triage layer.
5. Add bootstrap-seed and catalog-governance skills next instead of deleting current workflow skills prematurely.
6. Keep export and verification in this repository so other systems can install from one place.
