#!/usr/bin/env python3
"""Validate an immutable, approved StagePilot delivery scope snapshot.

The validator is read-only.  When a delivery state is supplied it resolves only
that state's relative ``scope_snapshot`` path; absolute and parent-traversing
paths are refused so a kickoff cannot bind arbitrary host files as its scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
REF = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}@[1-9][0-9]*$")
DISALLOWED_VALUE = re.compile(r"(?:\x00|://|(?:token|password|secret|apikey|api_key)\s*[:=])", re.IGNORECASE)


def finding(code: str, field: str | None = None) -> dict[str, str]:
    item = {"code": code}
    if field:
        item["field"] = field
    return item


def is_safe_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not DISALLOWED_VALUE.search(value)


def load_json(path: Path, findings: list[dict[str, str]], code: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        findings.append(finding(code))
        return None
    if not isinstance(parsed, dict):
        findings.append(finding(code))
        return None
    return parsed


def validate_snapshot(snapshot: dict[str, Any], findings: list[dict[str, str]]) -> None:
    if snapshot.get("schema_version") != 1:
        findings.append(finding("scope_schema_version_invalid", "schema_version"))
    requirement_id = snapshot.get("requirement_id")
    if not isinstance(requirement_id, str) or not SAFE_ID.fullmatch(requirement_id):
        findings.append(finding("scope_requirement_id_invalid", "requirement_id"))
    revision = snapshot.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        findings.append(finding("scope_revision_invalid", "revision"))
    if snapshot.get("status") != "approved":
        findings.append(finding("scope_status_not_approved", "status"))
    if snapshot.get("change_policy") != "lead_approved_revision":
        findings.append(finding("scope_change_policy_invalid", "change_policy"))
    for field, code in (("approval_ref", "scope_approval_ref_invalid"), ("risk_assessment", "scope_risk_assessment_invalid")):
        value = snapshot.get(field)
        if (field == "approval_ref" and (not isinstance(value, str) or not SAFE_ID.fullmatch(value))) or (field == "risk_assessment" and not is_safe_text(value)):
            findings.append(finding(code, field))
    if not isinstance(snapshot.get("evidence_refs"), list) or not snapshot["evidence_refs"] or any(not is_safe_text(item) for item in snapshot["evidence_refs"]):
        findings.append(finding("scope_evidence_refs_invalid", "evidence_refs"))
    if isinstance(revision, int) and not isinstance(revision, bool) and revision > 1:
        change_ref = snapshot.get("change_request_ref")
        expected_supersedes = f"{requirement_id}@{revision - 1}"
        if not isinstance(change_ref, str) or not SAFE_ID.fullmatch(change_ref):
            findings.append(finding("scope_change_request_ref_invalid", "change_request_ref"))
        if snapshot.get("supersedes") != expected_supersedes:
            findings.append(finding("scope_supersedes_invalid", "supersedes"))
    refs = snapshot.get("source_refs")
    if not isinstance(refs, list) or not refs or any(not is_safe_text(item) for item in refs):
        findings.append(finding("scope_source_refs_invalid", "source_refs"))
    if not is_safe_text(snapshot.get("scope_summary")):
        findings.append(finding("scope_summary_invalid", "scope_summary"))
    acceptance = snapshot.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance or any(not is_safe_text(item) for item in acceptance):
        findings.append(finding("scope_acceptance_criteria_invalid", "acceptance_criteria"))
    non_goals = snapshot.get("non_goals")
    if not isinstance(non_goals, list) or any(not is_safe_text(item) for item in non_goals):
        findings.append(finding("scope_non_goals_invalid", "non_goals"))
    decisions = snapshot.get("locked_decisions")
    if not isinstance(decisions, list):
        findings.append(finding("scope_locked_decisions_invalid", "locked_decisions"))
    else:
        for decision in decisions:
            if not isinstance(decision, dict) or not isinstance(decision.get("id"), str) or not SAFE_ID.fullmatch(decision["id"]) or not is_safe_text(decision.get("rule")):
                findings.append(finding("scope_locked_decisions_invalid", "locked_decisions"))
                break


def resolve_state_snapshot(state_path: Path, state: dict[str, Any], findings: list[dict[str, str]]) -> Path | None:
    declared = state.get("scope_snapshot")
    if not isinstance(declared, str) or not declared.strip():
        findings.append(finding("scope_snapshot_missing", "scope_snapshot"))
        return None
    candidate = Path(declared)
    if candidate.is_absolute() or ".." in candidate.parts:
        findings.append(finding("scope_snapshot_path_unsafe", "scope_snapshot"))
        return None
    resolved = (state_path.parent / candidate).resolve()
    try:
        resolved.relative_to(state_path.parent.resolve())
    except ValueError:
        findings.append(finding("scope_snapshot_path_unsafe", "scope_snapshot"))
        return None
    if not resolved.is_file():
        findings.append(finding("scope_snapshot_not_found", "scope_snapshot"))
        return None
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="scope snapshot JSON path (standalone validation)")
    parser.add_argument("--state", help="root delivery state JSON path")
    parser.add_argument("--kickoff", help="optional kickoff artifact to bind to the same scope")
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()
    if not args.snapshot and not args.state:
        parser.error("one of --snapshot or --state is required")

    findings: list[dict[str, str]] = []
    state: dict[str, Any] | None = None
    state_path: Path | None = None
    snapshot_path: Path | None = Path(args.snapshot).resolve() if args.snapshot else None
    if args.state:
        state_path = Path(args.state).resolve()
        state = load_json(state_path, findings, "scope_state_invalid")
        if state is not None:
            bound_path = resolve_state_snapshot(state_path, state, findings)
            if snapshot_path is not None and bound_path is not None and snapshot_path != bound_path:
                findings.append(finding("scope_snapshot_binding_mismatch", "scope_snapshot"))
            snapshot_path = bound_path or snapshot_path

    snapshot: dict[str, Any] | None = None
    digest = None
    if snapshot_path is not None:
        snapshot = load_json(snapshot_path, findings, "scope_snapshot_invalid")
        if snapshot is not None:
            digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
            validate_snapshot(snapshot, findings)

    if state is not None and snapshot is not None and digest is not None:
        if state.get("scope_revision") != snapshot.get("revision"):
            findings.append(finding("scope_revision_mismatch", "scope_revision"))
        if state.get("scope_snapshot_sha256") != digest:
            findings.append(finding("scope_digest_mismatch", "scope_snapshot_sha256"))
        expected_ref = f"{snapshot.get('requirement_id')}@{snapshot.get('revision')}"
        refs = state.get("approved_refs")
        if not isinstance(refs, list) or expected_ref not in refs or any(not isinstance(item, str) or not REF.fullmatch(item) for item in refs):
            findings.append(finding("scope_approved_ref_missing", "approved_refs"))
        if args.kickoff:
            try:
                kickoff_text = Path(args.kickoff).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                findings.append(finding("scope_kickoff_invalid", "kickoff"))
            else:
                declared = str(state.get("scope_snapshot", ""))
                if expected_ref not in kickoff_text and declared not in kickoff_text:
                    findings.append(finding("scope_kickoff_binding_missing", "kickoff"))

    result: dict[str, Any] = {"valid": not findings, "findings": findings}
    if snapshot is not None:
        result["scope"] = {"requirement_id": snapshot.get("requirement_id"), "revision": snapshot.get("revision"), "status": snapshot.get("status"), "sha256": digest}
    print(json.dumps(result, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
