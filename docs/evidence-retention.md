# Evidence Retention and Reconciliation

Runtime evidence is outside the repository and is never purged by automation. `scripts/reconcile_evidence.py` is read-only: it emits JSON findings and sets `purge_performed: false`.

## Authority and retention

- The designated delivery lead owns retention, archive destination, access grants, and any purge approval.
- A purge requires a recorded authority, scope, retention expiry, and restore location; this repository supplies no purge command.
- Archive manifests list relative artifact paths and SHA-256 values. A checksum mismatch is an escalation, not an automatic overwrite.

## Release provenance and cadence

After an explicitly approved fixture rollout, retain the exported `catalog-manifest.json` and successful parity JSON, then create the evidence record with an explicit destination:

```bash
python3 scripts/record_release_evidence.py \
  --manifest /abs/export/catalog-manifest.json \
  --parity-result /abs/export/parity.json \
  --evidence-dir /abs/fixture-evidence \
  --verifier-version stagepilot-sync-v1
```

The record binds source revision, catalog version/hash, export-manifest hash, verifier version, timestamp, and parity success. Reconciliation reports missing, malformed, or catalog-stale release provenance without changing any target.

Cadence: review contracts with every behavior-boundary change; produce export/parity evidence only at an approved rollout; review contract ownership and expiring exemptions quarterly.

## Fixture contract

An evidence directory contains `state.json`, optional `locks/*.lock`, optional `supervisor-result.json`, and `archive-manifest.json`:

```json
{"status":"running","updated_at":"2026-07-18T00:00:00Z","catalog_sha256":"..."}
```

Run reconciliation only with explicit paths:

```bash
python3 scripts/reconcile_evidence.py \
  --evidence-dir /abs/fixture-evidence \
  --catalog governance/skill-catalog.json \
  --stale-seconds 3600
```

Findings include stale active state, stale or invalid locks, orphan-worktree markers, missing supervisor result, obsolete catalog revision, missing/invalid archive manifest, and checksum mismatches. Stale locks are classified `manual-reclaim`; the tool never removes them.
