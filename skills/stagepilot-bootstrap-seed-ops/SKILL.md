---
name: stagepilot-bootstrap-seed-ops
description: "Use when planning, applying, verifying, or reporting an explicit-target StagePilot Hermes profile bootstrap from this harness without touching an active runtime by default."
version: 1.0.0
author: Justin Ko
license: private
metadata:
  hermes:
    tags: [stagepilot, bootstrap, profiles, provisioning, rollback]
    related_skills: [bootstrap-baseline, stagepilot-agent-harness, stagepilot-skill-catalog-governance, stagepilot-doctor-ops]
---

# StagePilot Bootstrap Seed Operations

## Boundary

This repository is the source of truth. Never infer or modify an active Hermes home/profile. All mutation requires an explicit fixture or approved `--target-home`; plan and verify are read-only.

## Contract

1. Run `profile_bootstrap.py plan` with an explicit target home and profile topology input.
2. Review the machine-readable plan: target paths, SOUL templates, catalog revision, and requested cwd/model/toolset values.
3. Run `apply` only after plan review. Apply stages the target, validates the exported skill catalog, and preserves a rollback point.
4. Run `verify` to check profile SOUL files, required topology, and exported catalog parity.
5. Use `report` for drift and recovery instructions. Do not expose credentials, remote URLs, or active-home paths in evidence.

## Safety Rules

- `apply` must reject missing explicit target, symlink escape, or an unsafe overlap with this source repository.
- A failed apply must retain/recover the prior target state.
- Repeat apply is idempotent when the requested seed is unchanged.
- Test only against temporary fixture homes; real runtime rollout is a separate approved handoff.

## Evidence

Record command, source catalog revision, requested profiles, validation result, and rollback outcome. Redact target-specific sensitive identifiers where required.
