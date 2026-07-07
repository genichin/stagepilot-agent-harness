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
- Project-specific deviations belong in `projects/<name>/`, not inside core role definitions unless the rule is truly global.

## Installation flow

1. Edit the model in this repository.
2. Validate repository structure and skill frontmatter.
3. Export selected skills into a Hermes runtime directory when needed.
4. Apply profile-specific overlays separately from the core harness.
