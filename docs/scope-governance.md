# Canonical Scope Governance

This document is the single entry point for preventing an already approved feature from being silently re-specified during delivery. It applies to every root kickoff launched with `scripts/lead-launch-runner.sh`.

## Authority and roles

- A **scope snapshot** is the canonical, immutable delivery input for one approved requirement revision.
- The **lead** owns snapshot publication, change approval, and revision increments.
- The **delivery-runner** may slice and sequence work inside the snapshot, but must not alter its acceptance criteria, non-goals, or locked decisions.
- **dev-impl** and **dev-qc** implement and verify the bound snapshot; neither role redefines it.
- A missing, conflicting, stale, or unapproved snapshot is a `scope_or_requirements` blocker. It requires lead escalation, not a replacement specification authored by a worker.

## Snapshot contract

Keep the snapshot next to the root delivery state. The state records a *relative* path, revision, and SHA-256 digest; absolute paths and `..` traversal are deliberately rejected.

```json
{
  "schema_version": 1,
  "requirement_id": "REQ-42",
  "revision": 3,
  "status": "approved",
  "approval_ref": "APR-42-R3",
  "risk_assessment": "Checkout behavior remains within the approved provider boundary.",
  "evidence_refs": ["EVID-42-TEST"],
  "change_request_ref": "CR-42-R3",
  "supersedes": "REQ-42@2",
  "source_refs": ["DISC-17", "DEC-08"],
  "scope_summary": "Implement the approved checkout adjustment.",
  "acceptance_criteria": ["The defined checkout behavior passes its focused test."],
  "non_goals": ["Do not alter the payment provider."],
  "locked_decisions": [
    {"id": "DEC-08", "rule": "Retain the approved callback format."}
  ],
  "change_policy": "lead_approved_revision"
}
```

Required properties:

1. `status` is exactly `approved`, and `approval_ref` points to the lead's recorded approval.
2. `revision` is a positive integer and `requirement_id` is a stable identifier.
3. `source_refs`, `evidence_refs`, and `risk_assessment` preserve the approved provenance, evidence, and residual-risk basis.
4. Revisions above `1` must carry a `change_request_ref` and exactly supersede the prior `REQ@revision`.
5. `acceptance_criteria` and `non_goals` are the worker's executable scope boundary.
6. `locked_decisions` captures constraints that must not be rediscovered or silently reversed.
7. `change_policy` is exactly `lead_approved_revision`.

## Root delivery-state binding

The root state contains the binding, while the kickoff repeats either the REQ revision (`REQ-42@3`) or the relative snapshot path for human audit.

```json
{
  "approved_refs": ["REQ-42@3"],
  "scope_snapshot": "scope-REQ-42-r3.json",
  "scope_revision": 3,
  "scope_snapshot_sha256": "<sha256 of the snapshot bytes>"
}
```

Validate it without side effects:

```bash
scripts/validate_scope_snapshot.py \
  --state .stagepilot/delivery/DEL-42/state.json \
  --kickoff .stagepilot/delivery/DEL-42/kickoff.md
```

The root launcher runs this validation before capability checks, worktree preparation, or worker launch. A failure persists a `blocked` root state with `reason_class=scope_or_requirements` and the deterministic validator finding as `blocker_code`.

## Change protocol

A worker must never edit a bound snapshot in place. To change approved scope:

1. Create a lead-owned change request identifying the active `REQ@revision`, affected acceptance/non-goal/decision, rationale, risk, and supporting evidence.
2. The lead approves or rejects it. A rejected or unapproved request does not alter delivery scope.
3. On approval, write a new snapshot with a higher revision and new digest. Mark the old revision superseded in the lead's decision/requirement record.
4. Update the root state and kickoff binding together. Any active worker receives an explicit re-handoff; live document edits do not flow into a runner branch automatically.
5. Re-run scope validation before implementation resumes. Evidence and handoffs must reference the new `REQ@revision`.

If the requested change is ambiguous, conflicts with a locked decision, or lacks lead approval, preserve the current revision and escalate with `reason_class=scope_or_requirements`.

## Evidence traceability

Each impl/QC handoff and delivery-transition artifact should cite the same `REQ@revision`. This yields a compact trace:

```text
approved REQ revision -> scope snapshot digest -> root state/kickoff
-> impl/QC handoff -> validation evidence -> completion state
```

Do not put credentials, absolute project paths, raw logs, remote URLs, or personal identifiers in snapshots, change requests, or observation reports.
