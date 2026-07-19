#!/usr/bin/env python3
"""Observe one detached root runner and durably mirror its terminal transition.

The root delivery-state remains authoritative.  This watcher only turns the
runner's detached-process outcome into an auditable event and optional
structured notification.  Missing exit/status artifacts after the runner
session disappears are fail-closed supervisor integrity failures.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TERMINAL_STATES = {"done", "blocked", "archived"}
SUPPORTED_EVENTS = {"done", "blocked", "archived", "incomplete", "supervisor_integrity_failure"}
MANIFEST_PATH_FIELDS = {
    "delivery_state",
    "exit_file",
    "status_file",
    "log_file",
    "event_file",
    "dispatch_cursor_file",
}


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    return payload


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def resolve_manifest_paths(manifest: dict[str, Any]) -> dict[str, Any]:
    """Resolve only manifest-relative artifact paths under one trusted root."""
    root = Path(str(manifest["path_root"])).resolve()
    if not root.is_dir():
        raise ValueError("manifest path_root is not a directory")
    resolved = dict(manifest)
    for field in MANIFEST_PATH_FIELDS:
        raw = Path(str(manifest[field]))
        if raw.is_absolute() or ".." in raw.parts:
            raise ValueError(f"manifest {field} must be a safe relative path")
        candidate = (root / raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(f"manifest {field} escapes path_root") from error
        resolved[field] = str(candidate)
    return resolved


def session_alive(session_name: str) -> bool:
    return subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def parse_status(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if not values.get("exit_code") or not values.get("state_summary"):
        raise ValueError("status artifact lacks exit_code or state_summary")
    int(values["exit_code"])
    return values


def failure_transition(state_path: Path, state: dict[str, Any], *, code: str, detail: str, evidence: list[str]) -> dict[str, Any]:
    state.update({
        "status": "blocked",
        "state": "blocked",
        "current_stage": "lead-escalation",
        "owner_target": "lead",
        "reason_class": "tooling_or_access_blocker",
        "blocker_code": code,
        "blocker_detail": detail,
        "evidence_paths": evidence,
        "next_action": "lead_review_runner_terminal_failure",
        "updated_at": now(),
    })
    atomic_json(state_path, state)
    return state


def terminal_observation(manifest: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, str] | None]:
    state_path = Path(manifest["delivery_state"])
    exit_path = Path(manifest["exit_file"])
    status_path = Path(manifest["status_file"])
    try:
        state = read_json(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return "supervisor_integrity_failure", {"read_error": f"delivery_state_unreadable:{type(error).__name__}"}, None
    if not exit_path.is_file() or not status_path.is_file():
        return "missing_artifacts", state, None
    try:
        exit_code = int(exit_path.read_text(encoding="utf-8").strip())
        status = parse_status(status_path)
    except (OSError, ValueError) as error:
        return "supervisor_integrity_failure", state, {"artifact_error": type(error).__name__}
    root_state = str(state.get("state", state.get("status", "missing")))
    status_exit_code = int(status["exit_code"])
    status_state = status["state_summary"].split(":", 1)[0]
    expected_status_state = root_state if root_state in TERMINAL_STATES else "incomplete"
    if status_exit_code != exit_code or status_state != expected_status_state:
        return "supervisor_integrity_failure", state, {**status, "artifact_error": "exit_or_state_summary_mismatch"}
    if root_state == "done" and exit_code == 0:
        return "done", state, status
    if root_state in {"blocked", "archived"}:
        return root_state, state, status
    return "incomplete", state, status


def event_id(manifest: dict[str, Any], event: str) -> str:
    stable = {"launch_id": manifest["launch_id"], "event": event}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()


def dispatch(event: dict[str, Any], targets: Any) -> list[dict[str, Any]]:
    if not isinstance(targets, list) or not targets:
        return [{"status": "not_configured"}]
    results: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            results.append({"status": "invalid_target"})
            continue
        target_id = str(target.get("id", "unnamed"))
        kind = target.get("kind")
        events = target.get("events", sorted(SUPPORTED_EVENTS))
        argv = target.get("argv")
        if kind not in {"command", "lead-session"} or not isinstance(events, list) or event["event"] not in events:
            results.append({"id": target_id, "status": "skipped"})
            continue
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            results.append({"id": target_id, "status": "invalid_target"})
            continue
        try:
            completed = subprocess.run(argv, input=json.dumps(event, sort_keys=True) + "\n", text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=30)
            results.append({"id": target_id, "kind": kind, "status": "sent" if completed.returncode == 0 else "delivery_failed", "returncode": completed.returncode})
        except (OSError, subprocess.TimeoutExpired) as error:
            results.append({"id": target_id, "kind": kind, "status": "delivery_failed", "error_type": type(error).__name__})
    return results


def reconcile(manifest: dict[str, Any]) -> dict[str, Any] | None:
    state_path = Path(manifest["delivery_state"])
    event_name, state, status = terminal_observation(manifest)
    alive = session_alive(str(manifest["tmux_session"]))
    if event_name == "missing_artifacts":
        if alive or time.time() < float(manifest["missing_artifact_deadline_epoch"]):
            return None
        state = failure_transition(state_path, state, code="supervisor_integrity_failure", detail="root_runner_exit_or_status_artifact_missing", evidence=[manifest["exit_file"], manifest["status_file"], manifest["log_file"]])
        event_name = "supervisor_integrity_failure"
    elif event_name == "supervisor_integrity_failure":
        if alive:
            return None
        if isinstance(state, dict) and "read_error" not in state:
            state = failure_transition(state_path, state, code="supervisor_integrity_failure", detail="root_runner_exit_or_status_artifact_invalid", evidence=[manifest["exit_file"], manifest["status_file"], manifest["log_file"]])
    elif event_name == "incomplete":
        if alive:
            return None
        state = failure_transition(state_path, state, code="runner_incomplete", detail="root_runner_exited_without_terminal_delivery_state", evidence=[manifest["exit_file"], manifest["status_file"], manifest["log_file"]])
    elif event_name not in TERMINAL_STATES:
        return None
    payload = {
        "schema_version": 1,
        "event_id": event_id(manifest, event_name),
        "at": now(),
        "event": event_name,
        "launch_id": manifest["launch_id"],
        "tmux_session": manifest["tmux_session"],
        "delivery_state": manifest["delivery_state"],
        "root_state": state.get("state", state.get("status")) if isinstance(state, dict) else None,
        "current_stage": state.get("current_stage") if isinstance(state, dict) else None,
        "owner_target": state.get("owner_target") if isinstance(state, dict) else None,
        "blocker_code": state.get("blocker_code") if isinstance(state, dict) else None,
        "exit_file": manifest["exit_file"],
        "status_file": manifest["status_file"],
        "log_file": manifest["log_file"],
        "exit_code": status.get("exit_code") if status else None,
        "state_summary": status.get("state_summary") if status else None,
    }
    return payload


def record_and_dispatch(manifest: dict[str, Any], event: dict[str, Any]) -> bool:
    cursor_path = Path(manifest["dispatch_cursor_file"])
    lock_path = cursor_path.with_suffix(cursor_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            cursor = read_json(cursor_path) if cursor_path.is_file() else {"schema_version": 1, "claimed_event_ids": [], "next_event_sequence": 1}
            claimed = cursor.get("claimed_event_ids", cursor.get("dispatched_event_ids", []))
            if event["event_id"] in claimed:
                return False
            sequence = cursor.get("next_event_sequence", 1)
            if not isinstance(sequence, int) or sequence < 1:
                raise ValueError("dispatch cursor next_event_sequence is invalid")
            claimed.append(event["event_id"])
            cursor["claimed_event_ids"] = claimed
            cursor["next_event_sequence"] = sequence + 1
            cursor["updated_at"] = now()
            atomic_json(cursor_path, cursor)
            event["sequence"] = sequence
            event["notifications"] = dispatch(event, manifest.get("notification_targets"))
            append_jsonl(Path(manifest["event_file"]), event)
            return True
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--max-polls", type=int, default=0, help="0 means continue until a terminal transition is observed")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.poll_seconds <= 0 or args.max_polls < 0:
        raise SystemExit("poll values must be positive (max-polls may be zero)")
    manifest = read_json(args.manifest.resolve())
    required = {"launch_id", "path_root", "delivery_state", "exit_file", "status_file", "log_file", "tmux_session", "event_file", "dispatch_cursor_file", "missing_artifact_deadline_epoch"}
    if manifest.get("schema_version") != 2 or not required.issubset(manifest):
        raise SystemExit("invalid runner watcher manifest")
    try:
        manifest = resolve_manifest_paths(manifest)
    except (OSError, ValueError) as error:
        raise SystemExit(f"invalid runner watcher manifest paths: {error}") from error
    if args.ready_file:
        atomic_json(args.ready_file.resolve(), {"schema_version": 1, "pid": os.getpid(), "ready_at": now()})
    polls = 0
    while True:
        event = reconcile(manifest)
        if event is not None:
            dispatched = record_and_dispatch(manifest, event)
            print(json.dumps({"event": event["event"], "event_id": event["event_id"], "dispatched": dispatched}, sort_keys=True))
            return 0
        polls += 1
        if args.once or (args.max_polls and polls >= args.max_polls):
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))