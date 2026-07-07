# Bootstrap Playbook

1. Clone or create the harness repo.
2. Review core docs and role definitions.
3. Copy baseline SOUL templates into real profiles.
4. Create a project overlay under `projects/<name>/`.
5. Define the project's canonical kanban board and record it in the project overlay. The default rule is to create a board named from the lead-owned project identifier (for example, `<project>-stagepilot`) unless a different convention is explicitly documented.
6. Wire notification and kanban conventions. By default, this board is required for the `lead -> delivery-runner` root kickoff only; downstream `delivery-runner -> dev-impl` and `delivery-runner -> dev-qc` handoffs remain ordinary transport-agnostic handoffs unless the overlay explicitly opts into kanban child-card routing.
7. Run verification checklist.
