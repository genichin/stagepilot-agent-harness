# TREX overlay

## Known conventions

- project-specific lead profile: `trex-dev-lead`
- shared worker profiles: `delivery-runner`, `dev-impl`, `dev-qc`
- kanban board: `trex-stagepilot`
- kanban scope: root kickoff visibility and runner queueing only by default; downstream `delivery-runner -> dev-impl` and `delivery-runner -> dev-qc` handoffs stay non-kanban unless TREX explicitly overrides this.

## Notes

TREX uses the shared worker topology with project-specific lead ownership.
