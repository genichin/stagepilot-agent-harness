---
name: run-discovery-delivery
description: "Use when: orchestrating delivery for a confirmed Discovery after related REQs are approved, running /run-discovery-delivery with a DCY ID or Discovery path, creating/adopting a batch queue from remaining Approved REQs, and sequentially running batch delivery until the Discovery root is done, blocked, or escalated."
version: 0.1.0
author: Justin Ko
license: private
argument-hint: "예: dcy-015 또는 docs/discovery/dcy-015_YYYYMMDD_topic.md"
user-invocable: true
metadata:
  hermes:
    tags: [stage-pilot, discovery, delivery, orchestration, batch, sdlc]
    related_skills: [suggest-batch-reqs, draft-batch, run-batch-delivery, confirm-req-implemented, stagepilot-agent-harness, stagepilot-handoffs]
---

# Purpose

This skill is the Discovery-level delivery controller for the StagePilot harness.

It takes a confirmed Discovery plus its linked REQ set, treats already `Implemented` REQs as satisfied dependencies, converts remaining `Approved` REQs into a runner-owned batch queue, and sequentially drives batch delivery until the Discovery root is complete, blocked, or explicitly escalated.

This skill exists to prevent confusion between two different handoffs:

- valid: `lead -> delivery-runner` with a confirmed Discovery root objective and Approved/Implemented REQ set
- invalid: `delivery-runner -> dev-impl` with the entire Discovery as one unsliced implementation task

# When to use

- `/run-discovery-delivery dcy-015` after the Discovery is confirmed and related REQs have passed `confirm-req`
- A lead has handed a confirmed Discovery to `delivery-runner` as the root delivery objective
- A Discovery produced multiple Approved REQs that need batch grouping and sequential delivery
- A Discovery-level root state exists and needs to resume from the current batch queue item
- The user asks to complete implementation/verification for all Approved REQs related to a Discovery

## Do not use when

- The Discovery is not confirmed (`confirm-discovery` comes first)
- The Discovery has no drafted REQs (`draft-req` comes first)
- Linked REQs are still `Proposed` and should be approved first (`confirm-req` comes first)
- You need to run only one already-created batch (`run-batch-delivery` is the narrower entrypoint)
- You need to change Discovery scope or REQ acceptance criteria (`change-req` or lead clarification comes first)
- Release planning/approval is the next step after delivery (`draft-release` / `confirm-release` belongs after this flow)

# Inputs

- Discovery identifier or path
  - `dcy-015`
  - full Discovery ID / slug
  - `docs/discovery/<DISCOVERY>.md`
- Optional existing Discovery root delivery state path
  - `.stagepilot/delivery/<dcy-id>_<slug>/state.json`
- `docs/discovery/index.md`
- source Discovery document
- `docs/srs/index.md`
- linked REQ documents
- `docs/batches/index.md` when present
- existing batch documents and root queue artifacts when resuming

# Core Rules

## 1. Discovery root, not direct implementation

- A confirmed Discovery may be the root delivery objective handed to `delivery-runner`.
- The runner must not send the whole Discovery directly to `dev-impl` as a single implementation task.
- The runner must operate through Approved REQs, batches, and bounded impl/QC handoffs.

## 2. REQ state partition

For the input Discovery, partition linked REQs into:

- `Implemented`: already satisfied; record as dependency/evidence, do not redo by default
- `Approved`: remaining delivery input; eligible for batch queue
- `Proposed`: approval gate still open; stop and report `confirm-req` needed
- `Deprecated` / `Superseded`: exclude with reason
- missing or inconsistent status: stop or escalate before delivery

## 3. Batch queue ownership

- The `delivery-runner` owns batch grouping inside the Approved REQ scope.
- The runner should use `suggest-batch-reqs` to evaluate grouping unless the grouping is already explicitly specified in the handoff.
- The runner then uses `draft-batch` to create batch documents and records queue state.
- The queue must be sequential by default: only one queue item is active unless a project overlay explicitly permits parallel batch delivery.

Recommended queue artifact:

```text
.stagepilot/delivery/<dcy-id>_<slug>/batch-queue.json
```

Each item should include at least:

- `batch_id` or planned batch slug
- included REQs
- status (`ready`, `running`, `blocked`, `done`, or `archived`)
- ordering/dependency reason
- evidence paths or PR refs once available

## 4. Batch execution

- Each queued batch is executed with `run-batch-delivery`.
- The batch-level chain remains responsible for planning, design, implementation, verification drafting, QC, verification approval, and REQ implementation sync for that batch.
- After a batch completes, update the Discovery root state and queue before starting the next batch.
- If a batch blocks, the Discovery root blocks unless the runner can safely defer that batch within approved authority; scope/priority/release-policy deferral requires lead escalation.

## 5. Completion condition

A Discovery root is `done` only when every linked remaining Approved REQ is one of:

- `Implemented` with merge-backed evidence
- explicitly deferred by lead decision with artifact trail
- escalated/blocked with lead-visible evidence and root status no longer claiming successful completion

One completed batch is not enough to mark the Discovery root `done` if other Approved REQs remain.

## 6. PR boundary

- Default single-root/single-PR rule still applies to REQ or batch roots.
- Discovery-level roots are an explicit multi-batch exception.
- A Discovery root may produce one PR per queued batch or a grouped PR plan, but the handoff or root state must say this is a Discovery-level multi-batch root.
- The runner may open/update PRs, but default merge authority remains with the lead unless a project overlay says otherwise.

# Execution Procedure

1. Resolve the Discovery path from the input.
2. Verify the Discovery is confirmed.
3. Read the Discovery's generated REQ references and/or reverse-map REQ documents by source Discovery.
4. Read each linked REQ and `docs/srs/index.md`; validate status consistency.
5. Partition REQs into `Implemented`, `Approved`, `Proposed`, and excluded states.
6. If any delivery-relevant REQ remains `Proposed`, stop with `confirm-req required` rather than delivering a partial accidental subset.
7. If no remaining `Approved` REQ exists, verify all linked REQs are `Implemented` or explicitly excluded/deferred, then mark/report Discovery root done or no-op.
8. Create or read the Discovery root state under `.stagepilot/delivery/<dcy-id>_<slug>/`.
9. If no queue exists, run `suggest-batch-reqs` conceptually or explicitly for remaining Approved REQs and choose the default runner grouping inside approved scope.
10. Use `draft-batch` for each selected queue item, recording `Root Delivery`, `Source Discovery`, `Queue Item`, included REQs, deferred/excluded siblings, and implementation readiness seed (target area, likely service seam, return/data shape, render/API insertion point, representative test assertions, forbidden data exposure, and open questions) in the batch artifacts.
11. Write/update `batch-queue.json` and root `state.json` with queue order, `current_batch`, `remaining_approved_reqs`, and `implemented_reqs`.
12. Execute the first non-done queue item with `run-batch-delivery`.
13. After each batch, inspect evidence and REQ status sync; update queue item status and root state.
14. Continue to the next queue item until the queue is complete or a blocker/escalation stops execution.
15. On successful completion, set root status to `done` and `current_stage` to a lead-visible completion/merge-review stage. Recommend release-stage next steps; do not silently proceed to release approval.

# Output Expectations

- Discovery path and confirmation status
- Linked REQ partition: Implemented / Approved remaining / Proposed blockers / excluded
- Root delivery state path
- Batch queue path and queue summary
- Created or adopted batch IDs
- For each batch: status, PR/evidence refs, implemented REQ sync result
- Final root status: `done`, `blocked`, or `ready/running` with next action
- Lead escalation if scope, priority, release policy, or repeated worker stalls exceed runner authority

# Common Pitfalls

1. Treating a Discovery root as a direct implementation task
   - The Discovery root belongs to runner orchestration, not to a single impl handoff.

2. Delivering only the first Approved REQ and forgetting sibling Approved REQs
   - A Discovery root remains open until all remaining Approved REQs are handled.

3. Letting `suggest-batch-reqs` remain a report instead of creating queue state
   - Runner-owned delivery must turn the chosen grouping into `draft-batch` artifacts and queue records.

4. Marking root `done` after one batch
   - Root `done` requires all queue items / remaining Approved REQs to be complete, deferred, or escalated.

5. Changing approved scope while grouping batches
   - Batch grouping is runner authority; scope change is lead authority.

6. Skipping QC because the root is large
   - The standard QC rule applies per batch. Only documented low-risk `batch-lite` exceptions may skip explicit QC.

# Verification Checklist

- [ ] Discovery is confirmed.
- [ ] Linked REQ set was discovered from explicit references and/or source Discovery reverse mapping.
- [ ] REQ status is consistent between body and `docs/srs/index.md`.
- [ ] No `Proposed` REQ is being silently delivered.
- [ ] Remaining `Approved` REQs are represented in the batch queue or explicitly deferred/escalated.
- [ ] Already `Implemented` REQs are recorded but not reimplemented by default.
- [ ] Batch queue is sequential unless a project overlay explicitly permits parallelism.
- [ ] Each batch uses `run-batch-delivery` and preserves impl/QC separation.
- [ ] Root `done` is not set until all remaining Approved REQs are Implemented, deferred, or escalated.
- [ ] Release work is recommended but not auto-approved.
