# Implementation worker hardening

## Purpose

This reference defines the harness-level contract that keeps `delivery-runner -> dev-impl` execution bounded, auditable, and safe from autonomous broad-search / context-compaction loops.

It was added after DCY-015 showed that Discovery-level orchestration could create a batch queue correctly, but the child implementation worker could still burn tokens by repeatedly reading/searching the repo without producing a progress artifact, code diff, or blocker.

## Required artifacts

For non-trivial supervised implementation work, the runner must prepare both:

1. `impl-<batch>.md` — the implementation handoff / task contract.
2. `impl-<batch>-implementation-context.md` — the bounded implementation context.

The implementation context is not optional busywork. It is the guardrail that turns a free-form coding chat into a bounded coding worker.

## Required implementation-context sections

`runner-launch-impl.sh --supervised` readiness gate expects these headings unless explicitly disabled with `--no-readiness-gate`:

```markdown
# Implementation context — <batch>

## Target files
- path/to/file.py — why it is in scope

## Edit anchors
- path/to/file.py: function/class/heading/string anchor to patch

## Allowed search budget
- exact searches allowed
- what broad searches are forbidden
- what to do if an anchor is invalid

## Validation commands
- command(s) the worker should run after editing

## First progress deadline
- deadline and required progress artifact fields
```

Recommended optional sections:

```markdown
## Existing APIs / seams
## Expected output strings / behavior
## Out of scope
## Known risks
```

## Readiness gate

The runner must not launch supervised `dev-impl` for non-trivial work until the implementation context is present and passes the readiness gate.

The readiness gate checks:

- context file exists;
- required headings are present;
- the worker prompt names the context file;
- first-progress deadline is passed to the supervisor;
- broad search is forbidden unless anchors are invalid.

A runner may use `--no-readiness-gate` only for a documented trivial/manual exception. The exception reason must be recorded in the delivery trail.

## Worker prompt contract

`dev-impl` must:

1. Read `implementation_context` first when provided.
2. Treat it as the bounded source of edit anchors and search budget.
3. Avoid broad repository search unless a listed anchor is invalid.
4. If an anchor is invalid, write a concrete blocker to the progress artifact and stop.
5. Create/update the progress artifact before broad reading if no code diff/check evidence exists yet.
6. Return changed files, commands/checks, evidence paths, and residual blockers/risks.

## Supervisor early-stop contract

`supervise_worker.py` now has three early-stop classes before the ordinary checkpoint:

| Result class | Exit | Trigger |
|---|---:|---|
| `first_progress_deadline_exceeded` | 127 | no git/progress evidence before `--first-progress-minutes` |
| `early_context_compaction_loop` | 128 | compaction markers exceed `--early-compaction-threshold` before progress |
| `early_read_loop_no_diff` | 129 | read/search markers exceed `--early-read-search-threshold` with no write/diff/progress |

These are cost-control failures, not implementation failures. The runner should mark the worker step blocked, record the final-result path, and escalate to the lead or rebuild the implementation context.

## Default launch shape

```bash
scripts/runner-launch-impl.sh \
  --supervised \
  --implementation-context .stagepilot/delivery/<root>/impl-<batch>-implementation-context.md \
  --first-progress-minutes 2 \
  .stagepilot/delivery/<root>/impl-<batch>.md \
  .stagepilot/delivery/<root>/state.json
```

## Success criteria

A launch is healthy only when at least one of these appears before the first-progress deadline:

- meaningful progress artifact update;
- git diff/status change from intentional edits;
- explicit blocker artifact explaining why editing cannot start.

Reading files, searching, or heartbeat text alone is not progress.
