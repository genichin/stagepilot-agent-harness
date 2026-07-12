# Discovery-level delivery orchestration

## Purpose

This reference defines the first-class StagePilot protocol for delivering a confirmed Discovery that produced multiple REQs.

The key distinction is:

```text
Discovery root handoff to delivery-runner: valid
Whole Discovery direct handoff to dev-impl: invalid
```

A Discovery root handoff lets the runner orchestrate all remaining approved work for that Discovery while preserving small implementation and independent QC boundaries.

## Canonical flow

```text
confirmed Discovery
→ draft one or more REQs
→ confirm-req approves eligible Proposed REQ set
→ lead emits Discovery-level root handoff to delivery-runner
→ runner partitions linked REQs into Implemented / remaining Approved / blockers
→ runner runs suggest-batch-reqs
→ runner creates/adopts batch queue via draft-batch
→ runner runs one batch at a time via run-batch-delivery
→ each batch performs impl + independent QC + verification approval + REQ sync
→ root done only when every remaining Approved REQ is Implemented, deferred, or escalated
```

## Root state shape

Recommended path:

```text
.stagepilot/delivery/<dcy-id>_<slug>/state.json
```

Recommended fields:

```json
{
  "schema_version": 1,
  "root_type": "discovery",
  "delivery_id": "dcy-015_monthly-settlement",
  "discovery_id": "DCY-015",
  "owner_target": "delivery-runner",
  "status": "ready",
  "current_stage": "kickoff",
  "repo": "/path/to/repo",
  "approved_refs": ["DCY-015", "REQ-023", "REQ-024", "REQ-025"],
  "implemented_reqs": ["REQ-022"],
  "remaining_approved_reqs": ["REQ-023", "REQ-024", "REQ-025"],
  "batch_queue_path": ".stagepilot/delivery/dcy-015_monthly-settlement/batch-queue.json",
  "current_batch": null,
  "completed_batches": [],
  "done_definition": "All remaining Approved REQs are Implemented, explicitly deferred, or escalated with lead-visible evidence."
}
```

## Queue shape

Recommended path:

```text
.stagepilot/delivery/<dcy-id>_<slug>/batch-queue.json
```

Recommended fields:

```json
{
  "schema_version": 1,
  "discovery_id": "DCY-015",
  "root_delivery_id": "dcy-015_monthly-settlement",
  "current_index": 0,
  "items": [
    {
      "queue_index": 0,
      "batch_id": "BAT-019",
      "included_reqs": ["REQ-023"],
      "status": "ready",
      "reason": "Dashboard shell and KPI sections should precede operational blocker sections.",
      "evidence_paths": []
    }
  ]
}
```

## Runner authority

The runner may:

- choose batch grouping inside the already-approved REQ scope
- create batch artifacts with `draft-batch`
- sequence queue items
- launch `dev-impl` and `dev-qc` per batch
- retry implementation/QC within documented caps
- mark queue items done when evidence and REQ sync support it

The runner may not:

- approve Discovery or REQ documents
- change approved scope or acceptance criteria silently
- send the whole Discovery as one direct impl task
- mark the Discovery root done while remaining Approved REQs still need delivery
- skip QC except for documented low-risk `batch-lite` exceptions
- proceed into release approval without lead hand-back

## Escalation triggers

Escalate to lead when:

- linked REQ state is inconsistent or contains delivery-relevant `Proposed` items
- batch grouping would change scope, priority, or release policy
- a batch blocks on tooling/access or repeated worker stalls
- QC reveals ambiguity in REQ acceptance criteria
- deferring a remaining Approved REQ requires product/priority authority

## Relationship to one-root/one-PR default

The default remains one root kickoff → one primary PR for ordinary REQ/batch roots.

A Discovery-level root is an explicit exception. It may own a multi-batch queue and multiple batch PRs when the kickoff or root state declares `root_type=discovery` and names the linked REQ set.

The exception does not remove lead merge authority by default. The runner may open/update batch PRs, but merge/release authority remains with the lead unless a project overlay says otherwise.
