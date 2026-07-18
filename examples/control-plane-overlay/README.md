# Example control-plane overlay

This is a project-owned declaration of required source categories. `collector_id` names the local collector implementation but is never executed by the core harness.

A project invokes its collectors, combines redacted source records into a snapshot under its delivery root, and then validates the snapshot with:

```bash
python3 scripts/validate_control_plane_snapshot.py \
  --overlay examples/control-plane-overlay/control-plane-overlay.json \
  --snapshot examples/control-plane-overlay/snapshot.json \
  --now 2026-07-18T12:00:00Z
```

`snapshot.json` is a redacted valid output fixture. Replace it with a project collector output at adoption time; do not put collector commands, credentials, or remote URLs in this overlay.

After a current `PASS`, a lifecycle owner records—not merely narrates—a positive claim through the gate. The output path is relative to the project's delivery root and remains immutable:

```bash
python3 scripts/record_lifecycle_claim.py \
  --delivery-root . \
  --claim-output .stagepilot/claims/REL-EXAMPLE-1.json \
  --overlay examples/control-plane-overlay/control-plane-overlay.json \
  --snapshot examples/control-plane-overlay/snapshot.json \
  --claim-kind release_readiness \
  --claim-context REL-EXAMPLE-1
```

The claim gate always uses the system clock; it deliberately does not provide a caller-controlled freshness override. Without a current matching `PASS`, this writes only an `unverified` / `BLOCKED` report and exits non-zero; it never emits a positive claim.

See [`docs/control-plane-snapshots.md`](../../docs/control-plane-snapshots.md) for the artifact contract and safe Markdown rendering convention.
