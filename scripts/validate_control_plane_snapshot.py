#!/usr/bin/env python3
"""Validate a project-neutral, evidence-backed control-plane snapshot.

The core is read-only: project overlays declare required sources and optional
collector identities, while project-owned collectors write the durable snapshot.
No provider endpoint, credential, or project-specific command is executed here.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
DISALLOWED_VALUE = re.compile(r"(?:\x00|://|(?:token|password|secret|apikey|api_key)\s*[:=])", re.IGNORECASE)
CATEGORIES = {"repository_baseline", "lifecycle_documents", "external_work_tracker", "operational_evidence"}
BLOCKERS = {"source_unavailable", "baseline_stale_or_unknown", "source_conflict", "evidence_missing"}
SOURCE_STATUSES = {"available", "unavailable", "conflict"}


def finding(code: str, field: str | None = None) -> dict[str, str]:
    item = {"code": code}
    if field:
        item["field"] = field
    return item


def add(findings: list[dict[str, str]], code: str, field: str | None = None) -> None:
    item = finding(code, field)
    if item not in findings:
        findings.append(item)


def safe_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not DISALLOWED_VALUE.search(value)


def load(path: Path, findings: list[dict[str, str]], code: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        add(findings, code)
        return None
    if not isinstance(payload, dict):
        add(findings, code)
        return None
    return payload


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def overlay_sources(overlay: dict[str, Any], findings: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    if overlay.get("schema_version") != 1:
        add(findings, "control_plane_overlay_invalid", "schema_version")
    declared = overlay.get("sources")
    if not isinstance(declared, list) or not declared:
        add(findings, "control_plane_overlay_invalid", "sources")
        return {}
    sources: dict[str, dict[str, Any]] = {}
    for source in declared:
        if not isinstance(source, dict):
            add(findings, "control_plane_overlay_invalid", "sources")
            continue
        source_id = source.get("id")
        category = source.get("category")
        if not isinstance(source_id, str) or not SAFE_ID.fullmatch(source_id) or category not in CATEGORIES or not isinstance(source.get("required"), bool):
            add(findings, "control_plane_overlay_invalid", "sources")
            continue
        collector_id = source.get("collector_id")
        if collector_id is not None and (not isinstance(collector_id, str) or not SAFE_ID.fullmatch(collector_id)):
            add(findings, "control_plane_overlay_invalid", "sources")
            continue
        if source_id in sources:
            add(findings, "control_plane_overlay_invalid", "sources")
            continue
        sources[source_id] = source
    return sources


def validate_snapshot(snapshot: dict[str, Any], declared: dict[str, dict[str, Any]], now: datetime, expected_kind: str | None, expected_context: str | None, findings: list[dict[str, str]]) -> None:
    if snapshot.get("schema_version") != 1:
        add(findings, "control_plane_snapshot_invalid", "schema_version")
    if not isinstance(snapshot.get("snapshot_id"), str) or not SAFE_ID.fullmatch(snapshot["snapshot_id"]):
        add(findings, "control_plane_snapshot_invalid", "snapshot_id")
    assessment_at = parse_time(snapshot.get("assessment_at"))
    expires_at = parse_time(snapshot.get("expires_at"))
    if assessment_at is None or expires_at is None or expires_at <= assessment_at or expires_at <= now:
        add(findings, "baseline_stale_or_unknown", "expires_at")

    decision = snapshot.get("decision")
    if not isinstance(decision, dict) or not isinstance(decision.get("kind"), str) or not SAFE_ID.fullmatch(decision["kind"]) or not isinstance(decision.get("context_id"), str) or not SAFE_ID.fullmatch(decision["context_id"]) or not safe_text(decision.get("requested_outcome")):
        add(findings, "control_plane_decision_invalid", "decision")
    elif (expected_kind is not None and decision["kind"] != expected_kind) or (expected_context is not None and decision["context_id"] != expected_context):
        add(findings, "control_plane_decision_mismatch", "decision")

    observed = snapshot.get("sources")
    if not isinstance(observed, list):
        add(findings, "evidence_missing", "sources")
        observed = []
    actual: dict[str, dict[str, Any]] = {}
    for source in observed:
        if not isinstance(source, dict):
            add(findings, "evidence_missing", "sources")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not SAFE_ID.fullmatch(source_id) or source_id in actual:
            add(findings, "evidence_missing", "sources")
            continue
        actual[source_id] = source

    for source_id, required in declared.items():
        if not required["required"]:
            continue
        source = actual.get(source_id)
        if source is None:
            add(findings, "evidence_missing", source_id)
            continue
        if source.get("category") != required["category"]:
            add(findings, "source_conflict", source_id)
        status = source.get("status")
        if status not in SOURCE_STATUSES:
            add(findings, "source_unavailable", source_id)
        elif status == "unavailable":
            add(findings, "source_unavailable", source_id)
        elif status == "conflict":
            add(findings, "source_conflict", source_id)
        observed_at = parse_time(source.get("observed_at"))
        if observed_at is None or observed_at > now:
            add(findings, "baseline_stale_or_unknown", source_id)
        provenance = source.get("provenance")
        if not isinstance(provenance, dict) or not safe_text(provenance.get("revision")) or parse_time(provenance.get("recorded_at")) is None:
            add(findings, "evidence_missing", source_id)
        if not safe_text(source.get("evidence_ref")):
            add(findings, "evidence_missing", source_id)

    blockers = snapshot.get("blockers")
    if not isinstance(blockers, list):
        add(findings, "control_plane_blocker_invalid", "blockers")
        blockers = []
    for blocker in blockers:
        if not isinstance(blocker, dict) or blocker.get("code") not in BLOCKERS or not isinstance(blocker.get("source_id"), str) or blocker["source_id"] not in declared or not safe_text(blocker.get("summary")):
            add(findings, "control_plane_blocker_invalid", "blockers")
            continue
        add(findings, blocker["code"], blocker["source_id"])

    claimed_result = snapshot.get("result")
    if claimed_result not in {"PASS", "BLOCKED"}:
        add(findings, "control_plane_result_invalid", "result")
    elif claimed_result == "PASS" and findings:
        add(findings, "control_plane_result_invalid", "result")
    elif claimed_result == "BLOCKED" and not findings:
        add(findings, "control_plane_result_invalid", "result")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--now", help="ISO-8601 UTC time for deterministic freshness checks")
    parser.add_argument("--decision-kind")
    parser.add_argument("--decision-context")
    args = parser.parse_args()

    findings: list[dict[str, str]] = []
    now = parse_time(args.now) if args.now else datetime.now(UTC)
    if now is None:
        parser.error("--now must be an ISO-8601 timestamp with timezone")
    overlay = load(args.overlay, findings, "control_plane_overlay_invalid")
    snapshot = load(args.snapshot, findings, "control_plane_snapshot_invalid")
    declared = overlay_sources(overlay, findings) if overlay is not None else {}
    if snapshot is not None:
        validate_snapshot(snapshot, declared, now, args.decision_kind, args.decision_context, findings)

    valid = not findings and snapshot is not None
    result = "PASS" if valid else "BLOCKED"
    payload: dict[str, Any] = {"valid": valid, "result": result, "findings": findings}
    if snapshot is not None:
        decision: dict[str, Any] = {}
        raw_decision = snapshot.get("decision")
        if isinstance(raw_decision, dict):
            decision = raw_decision
        payload["snapshot"] = {
            "id": snapshot.get("snapshot_id"),
            "assessment_at": snapshot.get("assessment_at"),
            "expires_at": snapshot.get("expires_at"),
            "decision": {"kind": decision.get("kind"), "context_id": decision.get("context_id")},
            "sources": [
                {"id": source.get("id"), "revision": source.get("provenance", {}).get("revision") if isinstance(source.get("provenance"), dict) else None}
                for source in snapshot.get("sources", []) if isinstance(source, dict)
            ],
        }
    print(json.dumps(payload, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
