# Adopting the Harness

Use this checklist when onboarding a new project into the StagePilot harness.

1. Confirm whether the project uses the standard four-role topology unchanged.
2. Identify any project-specific overrides and write them under `projects/<name>/`.
3. Choose which profile templates to copy from `profiles/templates/`.
4. Confirm the canonical handover path for kickoff, implementation, QC, escalation, and completion.
5. Decide the canonical root handoff artifact/state paths for the project and record them in the overlay.
6. Decide whether Telegram notification should mirror kickoff/completion for lead visibility. Kanban is forbidden and must not be introduced by overlay.
7. Export or install the needed skills into the target Hermes runtime.
