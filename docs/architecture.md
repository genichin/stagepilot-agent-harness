# Architecture

`stagepilot-agent-harness` separates **operating model** from **project implementation**.

## Layers

1. **Core harness**
   - role definitions
   - handover contracts
   - state semantics
   - templates
   - verification checklists

2. **Project overlays**
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
