# Skills in the Harness Repo

This repository keeps StagePilot-related Hermes skills **inside the project** rather than in a detached skill-only repository.

## Why

- The operating model and the skills evolve together.
- Handover contracts, role boundaries, and skill instructions must not drift.
- The repo should be the single review surface for topology changes.

## Current skill set

| Skill | Purpose |
|---|---|
| `stagepilot-agent-harness` | Umbrella entrypoint for the overall operating harness |
| `stagepilot-role-topology` | Role boundaries, ownership, and escalation model |
| `stagepilot-handoffs` | Canonical handover contracts and payload expectations |

## Recommended workflow

1. Update core docs first.
2. Reflect the same operational rule in the relevant SKILL.md file.
3. Run `python3 scripts/verify_structure.py`.
4. Export skills with `python3 scripts/export_skills.py --dest <path>` when you want a Hermes runtime copy.

## Future extensions

Potential future in-repo skills:

- `stagepilot-delivery-runner-operations`
- `stagepilot-kanban-orchestration`
- `stagepilot-notify-debugging`
