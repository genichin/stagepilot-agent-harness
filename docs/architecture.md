# Architecture

`stagepilot-agent-harness` separates **operating model** from **project implementation**, while keeping the **agent-facing skill source** in the same repository.

## Layers

1. **Core harness**
   - role definitions
   - handover contracts
   - state semantics
   - templates
   - verification checklists

2. **Skill source layer**
   - in-repo `skills/*/SKILL.md`
   - linked references for agent consumption
   - export/install tooling for Hermes profiles

3. **Project overlays**
   - project-specific rules
   - repo/workspace conventions
   - notification targets
   - examples

4. **Detached-runner supervision control plane**
   - the root delivery-state remains the lifecycle source of truth
   - `lead-launch-runner.sh` creates a versioned manifest with trusted-artifact-root-relative paths
   - `watch_runner_terminal.py` reconciles detached tmux exit with root state and runner artifacts, writes sequenced append-only events, and fails closed on integrity gaps
   - notification adapters consume structured JSON events over stdin; the cursor claims event IDs before dispatch for local at-most-once delivery
   - the QC rework controller owns a delivery-state-scoped lock and records each fresh QC artifact/count before evaluating or escalating it

## Design principles

- Shared worker roles by default; project-specific lead overlays when needed.
- Lead owns decisions; runner owns orchestration.
- Implementation and QC stay independent.
- State transitions should be externally inspectable.
- Handover payloads should be self-contained.
- Skills should compress the operating model into reusable agent instructions without becoming a forked source of truth.

## Source-of-truth rule

The repository is the source of truth.

- `docs/`, `roles/`, `handoffs/`, `templates/`, and `playbooks/` define the human operating model.
- `skills/` translates that model into Hermes-executable instructions.
- `governance/sync-contract.yaml` declares source-to-dependent co-change contracts; `scripts/validate_governance_sync.py` enforces them for reviewed Git ranges.
- Project-specific deviations belong in `projects/<name>/`, not inside core role definitions unless the rule is truly global.

The local quality gate remains useful without a Git range. In CI, pass an explicit reviewed range to enforce contracts and version provenance:

```bash
GIT_BASE="$(git merge-base origin/main HEAD)" GIT_HEAD=HEAD bash scripts/check_quality.sh
```

An exception must be an expiring, reviewed entry in `governance/sync-contract.yaml`; it must not be a permanent comment or a bypass of runtime target safety.

## Installation flow

1. Edit the model in this repository.
2. Use `docs/profile-bootstrap.md` to create or update the Hermes profiles.
3. Use `docs/model-policy.md` to choose the default role-to-model mapping.
4. Validate repository structure and skill frontmatter.
5. Export selected skills into a Hermes runtime directory when needed.
6. Apply profile-specific overlays separately from the core harness.
