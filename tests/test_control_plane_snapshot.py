#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_control_plane_snapshot.py"
NOW = "2026-07-18T12:00:00Z"
CATEGORIES = (
    "repository_baseline",
    "lifecycle_documents",
    "external_work_tracker",
    "operational_evidence",
)


def overlay() -> dict:
    return {
        "schema_version": 1,
        "sources": [
            {"id": f"source-{index}", "category": category, "required": True, "collector_id": f"collector-{index}"}
            for index, category in enumerate(CATEGORIES, start=1)
        ],
    }


def snapshot() -> dict:
    return {
        "schema_version": 1,
        "snapshot_id": "CPS-42",
        "assessment_at": "2026-07-18T11:55:00Z",
        "expires_at": "2026-07-18T12:30:00Z",
        "decision": {"kind": "release_readiness", "context_id": "REL-42", "requested_outcome": "ready"},
        "result": "PASS",
        "sources": [
            {
                "id": f"source-{index}",
                "category": category,
                "status": "available",
                "observed_at": "2026-07-18T11:54:00Z",
                "provenance": {"revision": f"REV-{index}", "recorded_at": "2026-07-18T11:54:00Z"},
                "evidence_ref": f"EVID-{index}",
            }
            for index, category in enumerate(CATEGORIES, start=1)
        ],
        "blockers": [],
    }


class ControlPlaneSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.overlay_path = self.root / "overlay.json"
        self.snapshot_path = self.root / "snapshot.json"
        self.write(overlay(), snapshot())

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write(self, overlay_data: dict, snapshot_data: dict) -> None:
        self.overlay_path.write_text(json.dumps(overlay_data), encoding="utf-8")
        self.snapshot_path.write_text(json.dumps(snapshot_data), encoding="utf-8")

    def run_validator(self, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            ["python3", str(VALIDATOR), "--overlay", str(self.overlay_path), "--snapshot", str(self.snapshot_path), "--now", NOW, *extra],
            text=True,
            capture_output=True,
            check=False,
        )
        return result, json.loads(result.stdout)

    def test_current_matching_pass_snapshot_succeeds(self) -> None:
        result, payload = self.run_validator("--decision-kind", "release_readiness", "--decision-context", "REL-42")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["result"], "PASS")
        self.assertEqual(payload["snapshot"]["id"], "CPS-42")

    def test_example_overlay_and_snapshot_are_valid(self) -> None:
        example = ROOT / "examples" / "control-plane-overlay"
        result = subprocess.run(
            ["python3", str(VALIDATOR), "--overlay", str(example / "control-plane-overlay.json"), "--snapshot", str(example / "snapshot.json"), "--now", NOW, "--decision-kind", "release_readiness", "--decision-context", "REL-EXAMPLE-1"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_missing_required_source_is_blocked(self) -> None:
        data = snapshot()
        data["sources"].pop()
        self.write(overlay(), data)
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["result"], "BLOCKED")
        self.assertIn("evidence_missing", {item["code"] for item in payload["findings"]})

    def test_expired_snapshot_is_blocked(self) -> None:
        data = snapshot()
        data["expires_at"] = "2026-07-18T11:59:59Z"
        self.write(overlay(), data)
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("baseline_stale_or_unknown", {item["code"] for item in payload["findings"]})

    def test_unavailable_source_is_blocked(self) -> None:
        data = snapshot()
        data["sources"][2]["status"] = "unavailable"
        data["result"] = "BLOCKED"
        data["blockers"] = [{"code": "source_unavailable", "source_id": "source-3", "summary": "Tracker query unavailable."}]
        self.write(overlay(), data)
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("source_unavailable", {item["code"] for item in payload["findings"]})

    def test_conflicting_source_is_blocked(self) -> None:
        data = snapshot()
        data["sources"][1]["status"] = "conflict"
        data["result"] = "BLOCKED"
        data["blockers"] = [{"code": "source_conflict", "source_id": "source-2", "summary": "Lifecycle records disagree."}]
        self.write(overlay(), data)
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("source_conflict", {item["code"] for item in payload["findings"]})

    def test_unknown_blocker_and_context_mismatch_are_rejected(self) -> None:
        data = snapshot()
        data["result"] = "BLOCKED"
        data["blockers"] = [{"code": "made_up", "source_id": "source-1", "summary": "Invalid fixture."}]
        self.write(overlay(), data)
        result, payload = self.run_validator("--decision-kind", "release_completion", "--decision-context", "REL-999")
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in payload["findings"]}
        self.assertTrue({"control_plane_blocker_invalid", "control_plane_decision_mismatch"}.issubset(codes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
