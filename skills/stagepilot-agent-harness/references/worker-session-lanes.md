# Worker session lanes

## Purpose

This reference defines how `delivery-runner` manages `dev-impl` and `dev-qc` execution sessions across a root delivery, batch, retry, and rework cycle.

The goal is to balance two needs:

1. **Clean role/context boundaries** so workers do not inherit stale runner, impl, or QC chat context.
2. **Efficient healthy continuation** so a worker that is already making concrete progress on the same handoff does not need to relearn the same narrow context.

## Terms

- **Worker execution session**: one concrete child Hermes execution, such as `hermes --profile dev-impl chat -q ...`, supervised or unsupervised.
- **Worker lane**: the continuity envelope for a single handoff/context/objective. A lane may contain the first child execution and, only while healthy, narrowly-scoped continuations of that same handoff.
- **Fresh lane/session**: a new child execution that receives prior state only through explicit artifacts, not through previous chat/session memory.

## Default policy

Default to a fresh worker lane for each new handoff.

A runner may continue the same worker lane only when all of these are true:

1. same root delivery;
2. same batch;
3. same handoff artifact;
4. same implementation-context or QC handoff contract;
5. same acceptance scope;
6. previous execution produced concrete progress;
7. no error, timeout, context compaction, no-progress stop, blocker, or failed-validation rework occurred;
8. continuation objective is a narrow follow-up to the same patch/verdict run.

Concrete progress means a meaningful git diff/status change, a completed validation/check after an intentional edit, or a specific evidence artifact. Intake-only progress artifacts, repeated reads/searches, and heartbeat text do not qualify.

## Mandatory fresh lane/session triggers

Start a fresh worker execution session when any of these occurs:

- first impl handoff for a batch;
- first QC handoff for a verification target;
- new batch;
- new root delivery / Discovery / PR-bound kickoff;
- retry after error, timeout, context compaction, read-loop/no-diff, no-progress stop, or process interruption;
- blocker resolution followed by retry;
- QC fail or conditional pass requiring implementation rework;
- implementation rework after QC;
- QC re-review after rework, unless a project overlay explicitly documents a low-risk same-verdict continuation;
- handoff/context/acceptance scope changed;
- model/tool/profile/runtime changed in a way that could affect execution.

## Impl lane policy

The first `delivery-runner -> dev-impl` handoff for a batch starts fresh.

Same-lane impl continuation is allowed only for healthy continuation of the same handoff, for example:

- the first child edited code and the runner asks it to update the implementation evidence document;
- the first child edited code and a listed validation command revealed a tiny fix inside the same target files;
- the worker needs to run the remaining listed validation commands for the same patch.

Same-lane impl continuation is forbidden after:

- no diff / no progress;
- compaction/read-loop early stop;
- failed validation that changes the task into rework rather than a tiny continuation;
- any blocker requiring a new decision or updated handoff/context;
- transition to a different batch or REQ scope.

## QC lane policy

The first `delivery-runner -> dev-qc` handoff for a verification target starts fresh.

Same-lane QC continuation is allowed only within the same active verdict run, for example continuing a long but healthy test/check sequence whose scope has not changed.

QC re-review after implementation rework starts fresh by default so the verifier is not anchored to its previous judgment. Previous verdicts and implementation evidence must be supplied as artifacts.

## Artifact-only continuity

Fresh lanes receive continuity only through explicit artifacts, including:

- root delivery state and batch queue;
- impl/QC handoff documents;
- implementation-context;
- progress artifacts;
- final-result metadata;
- child logs;
- QC verdicts;
- rework handoffs;
- git diff/status and validation output.

Do not paste whole previous conversations into a fresh child prompt. Summarize only the minimum facts needed in a handoff or rework artifact and link evidence paths.

## Runner responsibilities

The runner must record which policy path it used:

- `fresh_lane` for a new child execution;
- `same_lane_continuation` for a healthy same-handoff continuation;
- `fresh_after_failure` for retry/rework after a failed or contaminated lane.

If the runner cannot decide whether reuse is safe, choose a fresh lane.
