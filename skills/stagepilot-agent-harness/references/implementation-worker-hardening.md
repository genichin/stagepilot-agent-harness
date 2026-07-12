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

## Service seams
- exact function/class/module boundary to call or create
- source service function(s) and adapter function(s), with ownership
- use `N/A — direct file edit only` only when no data/API/service boundary exists

## Return shape
- expected fields/types/empty-state behavior that the seam returns or consumes
- use `N/A` only for no-data-contract edits

## Render insertion point
- UI/page/CLI/API insertion point and surrounding anchor
- use `N/A` only for non-rendering/internal edits

## Test assertions
- exact assertions/strings/fixtures/checks that prove acceptance

## Forbidden data exposure
- fields, paths, raw payloads, secrets, or internal names that must not be displayed/logged
- use `N/A` only when the slice has no data exposure surface

## Allowed search budget
- exact searches allowed
- what broad searches are forbidden
- what to do if an anchor/seam/return shape is invalid

## Validation commands
- command(s) the worker should run after editing

## First progress deadline
- deadline and required progress artifact fields
```

These headings are required even for simple work; put an explicit `N/A` with a reason rather than omitting a section. The goal is to force the runner to decide whether a slice is truly direct-edit work or whether it needs a pinned data/service contract before `dev-impl` starts.

Recommended optional sections:

```markdown
## Out of scope
## Known risks
## Fixture/data setup
```

## Readiness gate

The runner must not launch supervised `dev-impl` for non-trivial work until the implementation context is present and passes the readiness gate.

The readiness gate checks:

- context file exists;
- required headings are present, including service seams, return shape, render insertion point, test assertions, and forbidden data exposure;
- the worker prompt names the context file;
- first-progress deadline is passed to the supervisor;
- broad search is forbidden unless anchors/seams are invalid and the context explicitly permits the search.

A runner may use `--no-readiness-gate` only for a documented trivial/manual exception. The exception reason must be recorded in the delivery trail.


## Worker lane session rule

The first `delivery-runner -> dev-impl` handoff for a batch starts a fresh child execution session.

A same-lane continuation is allowed only when all of these are true:

- same root delivery;
- same batch;
- same handoff and implementation-context;
- same acceptance scope;
- previous execution produced concrete progress;
- no error, timeout, blocker, context compaction, no-progress stop, or failed-validation rework occurred;
- the continuation objective is a narrow follow-up to the same patch.

Any retry after error/no-progress/compaction/blocker, any implementation rework after QC, and any new batch must start a fresh child execution session. Prior attempt context must be passed only through explicit artifacts:

- implementation handoff;
- implementation-context;
- delivery state / batch queue;
- progress artifact;
- previous final-result/log paths;
- rework handoff or QC verdict document;
- git diff/status in the delivery worktree.

Do not paste whole previous conversations into a fresh child prompt. Summarize only the minimum needed facts in a handoff/rework artifact and link evidence paths. This keeps impl reproducible, auditable, and insulated from runner/QC role context.

## Worker prompt contract

`dev-impl` must:

1. Read `implementation_context` first when provided.
2. Treat it as the bounded source of edit anchors, service seams, return shape, render insertion point, test assertions, forbidden data exposure, and search budget.
3. Avoid broad repository search unless a listed anchor/seam is invalid and the context explicitly permits that search.
4. If an anchor, seam, return shape, or test assertion is missing/invalid, write a concrete blocker to the progress artifact and stop rather than designing a new contract silently.
5. Create/update the progress artifact before broad reading if no code diff/check evidence exists yet.
6. Return changed files, commands/checks, evidence paths, and residual blockers/risks.


## Patch-first worker behavior

When the readiness gate passes, the implementation-context is no longer a research prompt. It is the edit contract.

`dev-impl` must use this order:

1. Read `implementation_context` once.
2. Read the handoff/state only for scope and state alignment.
3. Read only the exact snippets named by `Target files` / `Edit anchors`.
4. Start one concrete outcome before additional exploration:
   - patch/write an in-scope file,
   - update the progress artifact with a concrete blocker naming the invalid anchor/seam/key, or
   - run a listed validation command only when the handoff explicitly requires pre-check evidence.
5. Do not re-discover or redesign service seams, return shapes, render insertion points, or test assertions already pinned in the context.
6. Do not use basename/path-finding retries as a normal step. If a pinned path is invalid, record the invalid path and stop unless the context explicitly permits a narrow exact search.

Progress artifact text that only says "reading context", "checking anchors", or "next step: implement" is intake, not concrete progress. A healthy `dev-impl` launch should show a diff or a concrete blocker before repeated read/search markers accumulate.

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


### Supervised worker lifecycle integrity

- Runner-owned supervised impl/QC calls should launch in background/tmux mode by default; foreground supervised execution is an explicit short-runtime exception only when the caller timeout is safely above the child max runtime.
- The runner must poll the launcher `exit_file`, worker log, and supervisor `final-result.json`. If `final-result.json` is missing or has `result_class=supervisor_interrupted`, classify it as `supervisor_integrity_failure` / harness execution failure, not as implementation acceptance failure.
- Child logs, diffs, and progress artifacts may be used as secondary evidence, but they do not replace the canonical supervisor final result.
- If a completed implementation has a simple same-scope implementation-context mismatch (for example visible label or CTA wording), the runner may create a fresh bounded rework handoff without lead escalation. Escalate only when the contract itself is ambiguous, scope changes, or governance/product authority is needed.
- Implementation contexts with user-visible copy requirements should include machine-checkable assertions such as required visible strings, forbidden visible strings, and required metric labels before QC handoff.
