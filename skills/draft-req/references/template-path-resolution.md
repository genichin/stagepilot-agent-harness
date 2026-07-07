# Template Path Resolution for `draft-req`

Use this reference when StagePilot is installed in different physical locations across agents or repositories.

## Core rule

Do **not** treat one physical path as the canonical template location for every agent.

Instead:

- treat `stage-pilot/templates/...` as the stable logical template path
- resolve that logical path against the active workspace or agent installation
- keep template source paths separate from generated target paths under `docs/srs/`

## Logical template paths

For `draft-req`, the logical template sources are:

- `stage-pilot/templates/srs/index.md`
- `stage-pilot/templates/srs/req-template.md`

These names are portable across Hermes Agent, GitHub Copilot, Claude, and similar environments. The physical path may differ.

## Physical path resolution order

When resolving a logical template path, check candidates in this order:

1. Workspace-local / subtree install: `.stage-pilot/templates/...`
2. Hermes external install: `~/.stage-pilot/templates/...`

Prefer the current workspace's installed copy over a user-level fallback.

## Source vs target distinction

Keep these separate:

- Template source: `stage-pilot/templates/...` resolved to one physical path above
- Generated targets: `docs/srs/index.md` and `docs/srs/<Type>/req-XXX_<slug>.md`

Do not describe a generated `docs/srs/...` file as if it were the template source.

## Ambiguity rule

If multiple physical candidates exist:

- prefer the highest-priority path in the resolution order above
- do not silently mix sources from different installs
- report which physical path was used when ambiguity could matter

## Durable pitfall

A common portability mistake is to hardcode only one of these:

- `.stage-pilot/templates/...`
- `~/.stage-pilot/templates/...`

That works for one install shape but breaks on another machine or agent. The durable pattern is:

- logical path in the skill
- resolution rule in the workflow
- generated target path documented separately
