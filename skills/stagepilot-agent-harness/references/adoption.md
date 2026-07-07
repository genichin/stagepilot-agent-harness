# Adopting the Harness

Use this checklist when onboarding a new project into the StagePilot harness.

1. Confirm whether the project uses the standard four-role topology unchanged.
2. Identify any project-specific overrides and write them under `projects/<name>/`.
3. Choose which profile templates to copy from `profiles/templates/`.
4. Confirm the canonical handover path for kickoff, implementation, QC, escalation, and completion.
5. Decide the canonical kanban board for the project and record it in the overlay. By default, use the lead-owned project name as the board stem (for example, `<project>-stagepilot`) unless a different board naming rule is explicitly documented.
6. Decide how kanban state and notifications will be surfaced to the lead. By default, this applies to the root kickoff / runner queue boundary; implementation and QC handoffs do not need separate kanban cards unless the overlay explicitly requires them.
7. Export or install the needed skills into the target Hermes runtime.
