# Template and Scaffold Resolution for `draft-req`

Use this reference when the workflow skill must create REQ documents without assuming one legacy install path.

## Core rule

Do **not** treat one physical path such as `.stage-pilot/...` or `~/.stage-pilot/...` as the canonical template location for every agent.

Instead:

- treat the repository as the source of truth for workflow behavior
- resolve REQ scaffolding from the current repository or its project overlay first
- keep scaffold source paths separate from generated target paths under `docs/srs/`

## What must be resolved

For `draft-req`, the workflow needs two document scaffolds:

- the REQ register/index scaffold
- the individual REQ document scaffold

The exact physical path may differ by repository layout, overlay, or export method.

## Resolution order

When resolving a REQ scaffold source, check candidates in this order:

1. A repo-local or project-overlay document scaffold source maintained with the harness
2. A vendored or exported StagePilot document-template source that the current workspace actually provides
3. If neither exists, the current repository's existing `docs/srs/` files as the local style exemplar for manual document creation

Prefer the current repository's own source over any user-level fallback.

## Source vs target distinction

Keep these separate:

- Scaffold source: the repo-owned or workspace-provided document scaffold you read from
- Generated targets: `docs/srs/index.md` and `docs/srs/<Type>/req-XXX_<slug>.md`

Do not describe a generated `docs/srs/...` file as if it were the scaffold source.

## Ambiguity rule

If multiple physical candidates exist:

- prefer the highest-priority source in the resolution order above
- do not silently mix scaffold files from different installs or exports
- report which source you used when the choice could matter

## Durable pitfall

A common portability mistake is to hardcode only one historical install shape.

The durable pattern is:

- repo-backed workflow rules in the skill
- repository/project-local scaffold resolution at runtime
- generated target paths documented separately
