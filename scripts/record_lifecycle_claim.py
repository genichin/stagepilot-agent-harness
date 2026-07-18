#!/usr/bin/env python3
"""Write a positive lifecycle claim only after a current control-plane PASS.

This is the fail-closed boundary for release/deployment/milestone claims. It
never treats a scope snapshot or a delivery `done` transition as release proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALIDATOR = Path(__file__).with_name("validate_control_plane_snapshot.py")
GOVERNED_CLAIM_KINDS = frozenset({
    "release_readiness",
    "release_completion",
    "milestone_completion",
    "deployment_readiness",
})


def validation(args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        str(VALIDATOR),
        "--overlay", str(args.overlay),
        "--snapshot", str(args.snapshot),
        "--decision-kind", args.claim_kind,
        "--decision-context", args.claim_context,
    ]
    if args.now:
        command.extend(["--now", args.now])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"valid": False, "result": "BLOCKED", "findings": [{"code": "control_plane_validator_failed"}]}
    if result.returncode != 0:
        payload["valid"] = False
        payload["result"] = "BLOCKED"
    return payload


def claim_target(delivery_root: Path, relative: str) -> Path | None:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    root = delivery_root.resolve()
    target = (root / candidate).resolve()
    if root != target and root not in target.parents:
        return None
    return target


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_report(snapshot: dict[str, Any] | None, artifact: Path, digest: str | None = None) -> dict[str, Any]:
    summary: dict[str, Any] = {"artifact": str(artifact)}
    if snapshot:
        summary.update({key: snapshot.get(key) for key in ("id", "assessment_at", "expires_at")})
    if digest is not None:
        summary["sha256"] = digest
    if snapshot and isinstance(snapshot.get("sources"), list):
        summary["source_revisions"] = snapshot["sources"]
    return summary


def write_unverified(
    target: Path | None,
    args: argparse.Namespace,
    findings: list[dict[str, Any]],
    snapshot: dict[str, Any] | None = None,
) -> int:
    report = {
        "schema_version": 1,
        "status": "unverified",
        "result": "BLOCKED",
        "requested_claim": {"kind": args.claim_kind, "context_id": args.claim_context},
        "recorded_at": args.now or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "control_plane_snapshot": snapshot_report(snapshot, args.snapshot),
        "findings": findings,
    }
    report_written = False
    if target is not None:
        if target.exists():
            if not any(item.get("code") == "claim_already_exists" for item in findings):
                report["findings"] = [*findings, {"code": "claim_already_exists"}]
        else:
            try:
                atomic_json(target, report)
                report_written = True
            except OSError:
                report["findings"] = [*findings, {"code": "claim_write_failed"}]
    print(json.dumps({"claim_written": False, "report_written": report_written, **report}, sort_keys=True))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery-root", required=True, type=Path)
    parser.add_argument("--claim-output", required=True, help="Relative claim path below --delivery-root")
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--claim-kind", required=True)
    parser.add_argument("--claim-context", required=True)
    parser.add_argument("--now", help="ISO-8601 UTC time for deterministic tests")
    args = parser.parse_args()

    target = claim_target(args.delivery_root, args.claim_output)
    if target is None:
        return write_unverified(None, args, [{"code": "claim_output_invalid"}])
    if args.claim_kind not in GOVERNED_CLAIM_KINDS:
        return write_unverified(target, args, [{"code": "unsupported_claim_kind", "field": "claim_kind"}])
    try:
        snapshot_sha256 = sha256(args.snapshot)
    except OSError:
        return write_unverified(target, args, [{"code": "control_plane_snapshot_unreadable"}])

    assessed = validation(args)
    if not assessed.get("valid"):
        return write_unverified(target, args, assessed.get("findings", []), assessed.get("snapshot"))
    try:
        if sha256(args.snapshot) != snapshot_sha256:
            return write_unverified(target, args, [{"code": "control_plane_snapshot_changed"}], assessed.get("snapshot"))
    except OSError:
        return write_unverified(target, args, [{"code": "control_plane_snapshot_unreadable"}], assessed.get("snapshot"))
    if target.exists():
        return write_unverified(target, args, [{"code": "claim_already_exists"}], assessed.get("snapshot"))

    snapshot = assessed["snapshot"]
    claim = {
        "schema_version": 1,
        "status": "accepted",
        "claim": {"kind": args.claim_kind, "context_id": args.claim_context},
        "recorded_at": args.now or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "control_plane_snapshot": snapshot_report(snapshot, args.snapshot, snapshot_sha256),
    }
    try:
        atomic_json(target, claim)
    except OSError:
        return write_unverified(target, args, [{"code": "claim_write_failed"}], snapshot)
    print(json.dumps({"claim_written": True, "result": "PASS", "claim": str(Path(args.claim_output)), "control_plane_snapshot": claim["control_plane_snapshot"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
