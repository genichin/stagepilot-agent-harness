#!/usr/bin/env python3
"""Run the bounded same-scope QC -> rework -> validation -> fresh-QC loop.

This controller is deliberately narrow: a QC verdict may trigger autonomous work only
when it explicitly identifies a same-scope implementation/evidence defect.  Every
other verdict class, launcher failure, malformed verdict, or exhausted retry budget
is persisted as a lead escalation instead of being retried.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_VERDICT_CYCLES = 3
REWORKABLE_FAILURE_CLASSES = {"implementation_defect", "evidence_gap"}
ESCALATION_REASON_CLASSES = {
    "scope_or_requirements",
    "approval_or_priority",
    "verification_or_release_risk",
}
SCOPE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@:-]{0,127}$")


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def fail(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, sort_keys=True))
    return 2


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


def relative_or_absolute(path: Path, state_dir: Path) -> str:
    try:
        return str(path.relative_to(state_dir))
    except ValueError:
        return str(path)


def validate_verdict(payload: dict[str, Any], scope: str) -> str | None:
    if payload.get("schema_version") != 1:
        return "qc_verdict_schema_invalid"
    if payload.get("acceptance_scope") != scope:
        return "qc_verdict_scope_mismatch"
    verdict = payload.get("verdict")
    if verdict not in {"pass", "fail"}:
        return "qc_verdict_invalid"
    if verdict == "pass":
        return None
    failure_class = payload.get("failure_class")
    allowed = REWORKABLE_FAILURE_CLASSES | ESCALATION_REASON_CLASSES
    if failure_class not in allowed:
        return "qc_failure_class_invalid"
    gaps = payload.get("gaps")
    if not isinstance(gaps, list) or not gaps or not all(isinstance(item, str) and item.strip() for item in gaps):
        return "qc_failure_gaps_invalid"
    return None


def handoff_text(kind: str, scope: str, cycle: int, original: Path, verdict: dict[str, Any] | None = None) -> str:
    lines = [
        f"# {kind} handoff: {scope} / cycle {cycle}",
        "",
        f"- Acceptance scope: `{scope}`",
        f"- Verdict cycle: `{cycle}` of `{MAX_VERDICT_CYCLES}`",
        f"- Original handoff: `{original}`",
        "- Scope boundary: make no change outside the bound approved acceptance scope.",
    ]
    if verdict:
        lines.extend(["", "## QC gap to address"])
        lines.extend(f"- {gap}" for gap in verdict["gaps"])
        lines.extend(["", f"- Required follow-up: {verdict.get('required_follow_up', 'Correct the listed same-scope gap and run the required validation.')} "])
    lines.extend(["", "## Original handoff content", "", original.read_text(encoding="utf-8").rstrip()])
    return "\n".join(lines) + "\n"


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def state_update(state_path: Path, state: dict[str, Any], loop: dict[str, Any], **changes: Any) -> None:
    state.update(changes)
    state["qc_rework_loop"] = loop
    state["updated_at"] = now()
    atomic_json(state_path, state)


def escalation(
    *, state_path: Path, state: dict[str, Any], loop: dict[str, Any], artifact_dir: Path,
    scope: str, code: str, reason_class: str, summary: str, evidence: list[str],
) -> int:
    artifact = artifact_dir / f"lead-escalation-{loop['verdict_count']:02d}.json"
    payload = {
        "schema_version": 1,
        "status": "blocked",
        "current_stage": "lead-escalation",
        "reason_class": reason_class,
        "blocker_code": code,
        "blocker_summary": summary,
        "affected_scope": scope,
        "verdict_count_for_scope": loop["verdict_count"],
        "evidence_paths": evidence,
        "options_considered": [
            "Stop autonomous rework and let lead decide the next approved action",
            "Resume only after a new approved scope/governance decision or corrected worker infrastructure",
        ],
        "recommended_next_action": "Lead reviews the persisted evidence and decides whether to re-scope, repair execution infrastructure, or authorize a new handoff.",
        "required_lead_decision": "Decide the next authorized action for this blocked acceptance scope.",
        "handoff_back_target": "lead",
        "recorded_at": now(),
    }
    atomic_json(artifact, payload)
    loop.update({"status": "blocked", "terminal_code": code, "escalation_artifact": relative_or_absolute(artifact, state_path.parent)})
    state_update(
        state_path, state, loop,
        status="blocked", current_stage="lead-escalation", owner_target="lead",
        reason_class=reason_class, blocker_code=code, blocker_detail=summary,
        verdict_count_for_scope=loop["verdict_count"],
        current_qc_verdict_artifact=loop.get("last_verdict_path"),
        current_handoff_artifact=relative_or_absolute(artifact, state_path.parent),
        evidence_paths=evidence + [relative_or_absolute(artifact, state_path.parent)],
        next_action="lead_review_qc_rework_escalation",
    )
    print(json.dumps({"ok": False, "status": "blocked", "blocker_code": code, "escalation_artifact": str(artifact)}, sort_keys=True))
    return 1


def run_command(command: list[str], *, label: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery-state", required=True, type=Path)
    parser.add_argument("--acceptance-scope", required=True)
    parser.add_argument("--impl-handoff", required=True, type=Path)
    parser.add_argument("--implementation-context", required=True, type=Path)
    parser.add_argument("--qc-handoff", required=True, type=Path)
    parser.add_argument("--validation-command", action="append", required=True, help="Command executed after each rework implementation; shell syntax is not supported.")
    parser.add_argument("--impl-launcher", type=Path, default=Path(__file__).with_name("runner-launch-impl.sh"))
    parser.add_argument("--qc-launcher", type=Path, default=Path(__file__).with_name("runner-launch-qc.sh"))
    parser.add_argument("--checkpoint-minutes", type=int, default=10)
    parser.add_argument("--max-minutes", type=int, default=60)
    parser.add_argument("--first-progress-minutes", type=int, default=5)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not SCOPE_PATTERN.fullmatch(args.acceptance_scope):
        return fail("--acceptance-scope must be a safe non-empty identifier")
    if min(args.checkpoint_minutes, args.max_minutes, args.first_progress_minutes) <= 0:
        return fail("supervision minute values must be positive")
    state_path = args.delivery_state.resolve()
    if not state_path.is_file():
        return fail(f"delivery state not found: {state_path}")
    lock_path = state_path.with_suffix(state_path.suffix + ".qc-rework.lock")
    lock_handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_handle.close()
        return fail("another QC rework controller already owns this delivery state")
    required = [args.impl_handoff, args.implementation_context, args.qc_handoff, args.impl_launcher, args.qc_launcher]
    missing = [str(item) for item in required if not item.resolve().is_file()]
    if missing:
        return fail("required artifact/launcher not found: " + ", ".join(missing))
    try:
        state = read_json(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return fail(f"delivery state is unreadable: {error}")
    if state.get("delivery_profile", "standard") == "fast":
        return fail("fast profile has no independent QC loop")
    state_dir = state_path.parent
    artifact_dir = state_dir / "qc-rework" / args.acceptance_scope
    event_path = artifact_dir / "events.jsonl"
    existing = state.get("qc_rework_loop")
    if existing is not None and not isinstance(existing, dict):
        return fail("delivery state qc_rework_loop must be an object")
    loop = dict(existing or {})
    if loop and loop.get("acceptance_scope") != args.acceptance_scope:
        return fail("delivery state already has a QC loop for a different acceptance scope")
    if loop.get("status") == "passed":
        print(json.dumps({"ok": True, "status": "passed", "verdict_count": loop.get("verdict_count", 0), "idempotent": True}, sort_keys=True))
        return 0
    if loop.get("status") == "blocked":
        print(json.dumps({"ok": False, "status": "blocked", "blocker_code": loop.get("terminal_code"), "idempotent": True}, sort_keys=True))
        return 1
    loop.setdefault("schema_version", 1)
    loop.setdefault("acceptance_scope", args.acceptance_scope)
    loop.setdefault("verdict_count", 0)
    if not isinstance(loop["verdict_count"], int) or loop["verdict_count"] < 0 or loop["verdict_count"] >= MAX_VERDICT_CYCLES:
        return fail("delivery state qc_rework_loop verdict_count is invalid")
    loop["status"] = "running"
    loop["max_verdict_cycles"] = MAX_VERDICT_CYCLES
    if existing and state.get("current_stage") == "impl-running":
        return escalation(
            state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir,
            scope=args.acceptance_scope, code="qc_rework_controller_interrupted",
            reason_class="tooling_or_access_blocker",
            summary="The controller was restarted while a rework implementation was in flight; it refuses to skip or duplicate that rework.",
            evidence=[str(artifact_dir)],
        )
    state_update(state_path, state, loop, status="running", current_stage="qc-review", owner_target="delivery-runner", next_action="launch_qc")

    original_impl = args.impl_handoff.resolve()
    original_qc = args.qc_handoff.resolve()
    implementation_context = args.implementation_context.resolve()
    impl_launcher = args.impl_launcher.resolve()
    qc_launcher = args.qc_launcher.resolve()
    delivery_profile = str(state.get("delivery_profile", "standard"))
    while loop["verdict_count"] < MAX_VERDICT_CYCLES:
        cycle = loop["verdict_count"] + 1
        verdict_path = artifact_dir / f"qc-verdict-{cycle:02d}.json"
        if verdict_path.exists():
            return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                code="qc_verdict_artifact_collision", reason_class="verification_or_release_risk",
                summary="The controller refuses to reuse a prior QC verdict artifact for a fresh review.", evidence=[str(verdict_path)])
        template = {"schema_version": 1, "acceptance_scope": args.acceptance_scope, "verdict": "REPLACE_WITH_pass_or_fail", "failure_class": "REPLACE_IF_FAIL", "gaps": ["REPLACE_IF_FAIL"], "required_follow_up": "REPLACE", "evidence_paths": [], "verdict_count_for_scope": cycle}
        atomic_json(verdict_path, template)
        fresh_qc_handoff = artifact_dir / f"qc-handoff-{cycle:02d}.md"
        atomic_text(fresh_qc_handoff, handoff_text("Fresh independent QC", args.acceptance_scope, cycle, original_qc))
        environment = os.environ.copy()
        environment.update({"STAGEPILOT_ACCEPTANCE_SCOPE": args.acceptance_scope, "STAGEPILOT_QC_VERDICT_OUTPUT": str(verdict_path), "STAGEPILOT_VERDICT_CYCLE": str(cycle)})
        qc_command = [str(qc_launcher), "--delivery-profile", delivery_profile, "--supervised", "--foreground-supervised", "--checkpoint-minutes", str(args.checkpoint_minutes), "--max-minutes", str(args.max_minutes), "--first-progress-minutes", str(args.first_progress_minutes), "--verdict-output", str(verdict_path), str(fresh_qc_handoff), str(state_path)]
        result = run_command(qc_command, label="qc", cwd=state_dir, env=environment)
        append_event(event_path, {"at": now(), "event": "qc_finished", "cycle": cycle, "returncode": result.returncode, "verdict_path": str(verdict_path)})
        loop["verdict_count"] = cycle
        loop["last_verdict_path"] = relative_or_absolute(verdict_path, state_dir)
        state_update(state_path, state, loop, status="running", current_stage="qc-review", owner_target="dev-qc", verdict_count_for_scope=cycle, current_qc_verdict_artifact=relative_or_absolute(verdict_path, state_dir), evidence_paths=[relative_or_absolute(verdict_path, state_dir)], next_action="evaluate_qc_verdict")
        if result.returncode != 0:
            return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                code="supervisor_integrity_failure", reason_class="tooling_or_access_blocker",
                summary="QC launcher/supervisor did not complete successfully; this is not an implementation acceptance verdict.", evidence=[str(verdict_path)])
        try:
            verdict = read_json(verdict_path)
            validation_error = validate_verdict(verdict, args.acceptance_scope)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            validation_error = f"qc_verdict_unreadable: {error}"
            verdict = {}
        if validation_error:
            return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                code="qc_verdict_integrity_failure", reason_class="tooling_or_access_blocker",
                summary=f"Fresh QC did not produce a valid canonical verdict: {validation_error}", evidence=[str(verdict_path)])
        append_event(event_path, {"at": now(), "event": "qc_verdict_recorded", "cycle": cycle, "verdict": verdict["verdict"], "failure_class": verdict.get("failure_class")})
        if verdict["verdict"] == "pass":
            loop["status"] = "passed"
            state_update(state_path, state, loop, status="running", current_stage="verification-complete", owner_target="delivery-runner", verdict_count_for_scope=cycle, current_qc_verdict_artifact=relative_or_absolute(verdict_path, state_dir), evidence_paths=[relative_or_absolute(verdict_path, state_dir)], next_action="confirm_batch_verification")
            print(json.dumps({"ok": True, "status": "passed", "verdict_count": cycle, "verdict_path": str(verdict_path)}, sort_keys=True))
            return 0
        failure_class = verdict["failure_class"]
        if failure_class not in REWORKABLE_FAILURE_CLASSES:
            return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                code="qc_non_reworkable_failure", reason_class=failure_class,
                summary="QC identified a scope, approval, or release-risk issue outside autonomous rework authority.", evidence=[str(verdict_path)])
        if cycle >= MAX_VERDICT_CYCLES:
            return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                code="qc_rework_budget_exhausted", reason_class="verification_or_release_risk",
                summary="The same acceptance scope remains unresolved after the maximum three QC verdict cycles.", evidence=[str(verdict_path)])
        rework_handoff = artifact_dir / f"rework-impl-{cycle:02d}.md"
        atomic_text(rework_handoff, handoff_text("Bounded implementation rework", args.acceptance_scope, cycle, original_impl, verdict))
        loop["last_rework_handoff"] = relative_or_absolute(rework_handoff, state_dir)
        state_update(state_path, state, loop, status="running", current_stage="impl-running", owner_target="dev-impl", verdict_count_for_scope=cycle, current_qc_verdict_artifact=relative_or_absolute(verdict_path, state_dir), current_handoff_artifact=relative_or_absolute(rework_handoff, state_dir), evidence_paths=[relative_or_absolute(verdict_path, state_dir), relative_or_absolute(rework_handoff, state_dir)], next_action="rework_impl")
        impl_command = [str(impl_launcher), "--delivery-profile", delivery_profile, "--supervised", "--foreground-supervised", "--checkpoint-minutes", str(args.checkpoint_minutes), "--max-minutes", str(args.max_minutes), "--first-progress-minutes", str(args.first_progress_minutes), "--implementation-context", str(implementation_context), str(rework_handoff), str(state_path)]
        result = run_command(impl_command, label="impl", cwd=state_dir, env=environment)
        append_event(event_path, {"at": now(), "event": "impl_finished", "cycle": cycle, "returncode": result.returncode, "rework_handoff": str(rework_handoff)})
        if result.returncode != 0:
            return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                code="supervisor_integrity_failure", reason_class="tooling_or_access_blocker",
                summary="Implementation launcher/supervisor did not complete successfully; no further QC verdict is inferred.", evidence=[str(rework_handoff), str(verdict_path)])
        for command_text in args.validation_command:
            try:
                command = shlex.split(command_text)
            except ValueError as error:
                return fail(f"invalid --validation-command: {error}")
            if not command:
                return fail("--validation-command cannot be empty")
            result = run_command(command, label="validation", cwd=state_dir, env=environment)
            append_event(event_path, {"at": now(), "event": "validation_finished", "cycle": cycle, "command": command, "returncode": result.returncode})
            if result.returncode != 0:
                return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
                    code="rework_validation_failed", reason_class="verification_or_release_risk",
                    summary="Required validation failed after autonomous implementation rework.", evidence=[str(rework_handoff), str(verdict_path)])
        state_update(state_path, state, loop, status="running", current_stage="qc-review", owner_target="dev-qc", next_action="launch_qc")
    return escalation(state_path=state_path, state=state, loop=loop, artifact_dir=artifact_dir, scope=args.acceptance_scope,
        code="qc_rework_budget_exhausted", reason_class="verification_or_release_risk",
        summary="The same acceptance scope exhausted its QC verdict budget.", evidence=[])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
