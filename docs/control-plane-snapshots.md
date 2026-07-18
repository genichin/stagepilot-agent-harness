# Evidence-backed control-plane snapshots

A control-plane snapshot is a durable, redacted assessment artifact used to decide whether a lifecycle claim may be made. It is separate from the approved scope snapshot:

- [scope governance](scope-governance.md) binds a delivery to approved requirements;
- this contract proves that the requested release, deployment, milestone, or program decision is based on current, attributable evidence.

## Core / overlay boundary

Core harness supplies only the JSON contract and `scripts/validate_control_plane_snapshot.py`. It is read-only and never contacts a provider, executes a collector command, or reads credentials.

A project overlay declares the source IDs and categories it requires and may name a project-owned `collector_id` for each. The overlay invokes and owns its collector; the collector writes a durable snapshot. `collector_id` is an identifier, **not an executable command**. This prevents a generic harness validator from becoming an arbitrary-command or credential boundary.

Required source categories are:

- `repository_baseline`
- `lifecycle_documents`
- `external_work_tracker`
- `operational_evidence`

Every overlay must declare at least one required source for each category; a partial overlay is invalid.

The example is in [`examples/control-plane-overlay/`](../examples/control-plane-overlay/).

## Snapshot v1

```json
{
  "schema_version": 1,
  "snapshot_id": "CPS-42",
  "assessment_at": "2026-07-18T11:55:00Z",
  "expires_at": "2026-07-18T12:30:00Z",
  "decision": {
    "kind": "release_readiness",
    "context_id": "REL-42",
    "requested_outcome": "ready"
  },
  "result": "PASS",
  "sources": [
    {
      "id": "repository",
      "category": "repository_baseline",
      "status": "available",
      "observed_at": "2026-07-18T11:54:00Z",
      "provenance": {"revision": "abc123", "recorded_at": "2026-07-18T11:54:00Z"},
      "evidence_ref": "repo-baseline-42"
    }
  ],
  "blockers": []
}
```

A source record requires a revision, recorded timestamp, observed timestamp, and safe evidence reference. Keep snapshots free of URLs, credentials, absolute paths, and raw logs.

`assessment_at`, source observation/provenance timestamps, and `expires_at` are evaluated against the validator clock; future assessment or provenance is invalid, and `expires_at` avoids treating an old successful assessment as current. Consumers can additionally assert the requested `--decision-kind` and `--decision-context`.

## Fail-closed validation

```bash
python3 scripts/validate_control_plane_snapshot.py \
  --overlay projects/example/control-plane-overlay.json \
  --snapshot .stagepilot/control-plane/CPS-42.json \
  --decision-kind release_readiness \
  --decision-context REL-42
```

The command emits JSON. Exit `0` means `PASS`; every malformed, stale, unavailable, conflicting, or mismatched artifact emits `BLOCKED` and exits non-zero. Normalized blocker codes are `source_unavailable`, `baseline_stale_or_unknown`, `source_conflict`, and `evidence_missing`.

## Authoritative lifecycle claims

Only `scripts/record_lifecycle_claim.py` may record these positive lifecycle claim kinds:

- `release_readiness`
- `release_completion`
- `milestone_completion` (including program completion)
- `deployment_readiness`

It invokes the read-only validator and requires an exact decision kind/context match, a `PASS` current at the claim writer's system clock, and an unchanged snapshot digest. The claim writer deliberately has no caller-controlled clock override. An accepted claim records the requested claim, the snapshot artifact path/ID/timestamps/SHA-256, and the redacted source revision summary. It never promotes a delivery-state `done` transition to a release claim.

Any unsupported kind or unavailable, stale, conflicting, malformed, or mismatched snapshot exits non-zero and writes a durable `status: unverified`, `result: BLOCKED` report at the requested artifact path when that path is safe and unused. The report contains only the requested claim, snapshot artifact summary, and normalized findings; it has no accepted `claim` field. Existing claim/report artifacts are immutable and are never overwritten.

## Markdown rendering convention

Project renderers must put only these redacted fields in a lifecycle handoff:

```markdown
## Control-plane assessment

- Snapshot: `CPS-42`
- Decision: `release_readiness` / `REL-42` / `ready`
- Assessed: `2026-07-18T11:55:00Z`; expires: `2026-07-18T12:30:00Z`
- Result: `PASS`
- Sources: `repository@abc123`, `tracker@T-42`
- Blockers: none
```

Render IDs, revisions, timestamps, categories, and normalized codes only. Do not render collector output, remote URLs, absolute paths, tokens, or raw logs.
