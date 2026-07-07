# Bootstrap Playbook

1. Clone or create the harness repo.
2. Review core docs and role definitions.
3. Copy baseline SOUL templates into real profiles.
4. Create a project overlay under `projects/<name>/`.
5. Define the project's default root handoff paths and record them in the project overlay. The default transport is a persisted kickoff artifact plus delivery-state record. If the project wants chat visibility, also define the optional Telegram notify destination/thread.
6. Wire launch and notification conventions. `lead -> delivery-runner` uses artifact-backed handoff plus explicit lead launch through `scripts/lead-launch-runner.sh`, which runs the runner in detached background `tmux`. Downstream `delivery-runner -> dev-impl` / `delivery-runner -> dev-qc` handoffs remain ordinary transport-agnostic handoffs. Kanban is forbidden in this harness.
7. Run verification checklist.
