---
name: stagepilot-skill-catalog-governance
description: Use when adding, importing, changing, versioning, deprecating, exporting, auditing, or reviewing StagePilot harness skills and their catalog governance artifacts.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stagepilot, skills, catalog, governance, validation, lifecycle]
    related_skills: [stagepilot-agent-harness, stagepilot-role-topology, stagepilot-doctor-ops]
---

# StagePilot Skill Catalog Governance

## Scope and source of truth

- `skills/<skill-name>/SKILL.md` is the canonical instruction source.
- `governance/skill-catalog.json` is the canonical lifecycle, ownership, review, and catalog-version source.
- A runtime export is a derived copy. Never edit a runtime copy and treat it as canonical.
- Runtime mutation requires an explicit destination and belongs to the export/release workflow; repository design work must not modify an active Hermes profile.

## Required change procedure

1. Read the affected `SKILL.md`, its related skills, and `governance/skill-catalog.json`.
2. Apply the source and manifest change in the same review unit.
3. Match directory name, frontmatter `name`, and manifest key exactly.
4. Update the skill `version` in both frontmatter and manifest, then update the catalog `version` for any inventory, lifecycle, ownership, or validator-contract change. Use semantic `MAJOR.MINOR.PATCH`:
   - patch: clarification or compatible correction;
   - minor: compatible new capability or workflow;
   - major: changed invocation, role boundary, handoff contract, or required input.
5. Install the pinned validator dependency in a clean environment:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

6. Validate source, contract coherence, and range provenance before export:

   ```bash
   python3 scripts/validate_skill_catalog.py --root . --format json
   GIT_BASE="$(git merge-base origin/main HEAD)" GIT_HEAD=HEAD bash scripts/check_quality.sh
   ```

   The range gate requires declared dependents for changed authority sources and version increments for changed skills; use only an expiring reviewed `sync-contract.yaml` exception when a co-change is intentionally deferred.

7. Record only validated release/export evidence. Do not record credentials, remote URLs, or auth-home paths.

## Ownership and review boundary

The `owner` and `reviewer` values in `governance/skill-catalog.json` identify accountable operating roles, not a runtime profile target.

| Change surface | Owner | Required reviewer |
|---|---|---|
| catalog schema, validator, exporter | `stagepilot-catalog-maintainer` | `stagepilot-governance-reviewer` |
| role topology, SOUL, handoff contracts | `stagepilot-operating-model-maintainer` | `stagepilot-governance-reviewer` |
| workflow skills | `stagepilot-workflow-maintainer` | `stagepilot-governance-reviewer` |
| runtime/doctor operations skills | `stagepilot-runtime-maintainer` | `stagepilot-governance-reviewer` |

## Lifecycle rules

- New skills start as `active` only after required metadata, ownership, and validation are present.
- Deprecated skills remain in the catalog until their planned sunset and require all of:
  - a distinct, existing replacement skill;
  - an ISO-8601 `sunset` date;
  - a non-empty `migration_note`.
- Do not delete a deprecated skill before its replacement and migration path have been reviewed.
- `related_skills` must target an existing skill and cannot self-reference. Relationship cycles are permitted only when they represent intentional bidirectional navigation; keep them minimal.

## Audit and exception handling

- Run the strict validator for every catalog change and before any export release.
- Audit catalog ownership, lifecycle metadata, relationship integrity, and source/runtime parity on the scheduled governance cadence.
- An exception must identify the violated rule, owner, reviewer, expiry, mitigation, and follow-up issue. Do not encode exceptions by weakening the validator globally.
- If validation fails, stop export or runtime propagation and repair source metadata first.

## Rollback boundary

- Repository source rollback is a normal version-control operation.
- Runtime rollback must use an explicit release artifact/manifest and must not silently overwrite an active profile.
- A source validation pass does not prove runtime parity; run the parity/export checks once those lifecycle tools are available.
