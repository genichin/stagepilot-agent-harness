#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "record_lifecycle_claim.py"
NOW = "2026-07-18T12:00:00Z"


def overlay() -> dict:
    return {
        "schema_version": 1,
        "sources": [
            {"id": "repository", "category": "repository_baseline", "required": True, "collector_id": "git"},
            {"id": "lifecycle", "category": "lifecycle_documents", "required": True, "collector_id": "docs"},
            {"id": "tracker", "category": "external_work_tracker", "required": True, "collector_id": "tracker"},
            {"id": "operations", "category": "operational_evidence", "required": True, "collector_id": "ops"},
        ],
    }


def snapshot(kind: str = "release_readiness") -> dict:
    categories = ["repository_baseline", "lifecycle_documents", "external_work_tracker", "operational_evidence"]
    return {
        "schema_version": 1,
        "snapshot_id": "CPS-42",
        "assessment_at": "2026-07-18T11:50:00Z",
        "expires_at": "2026-07-18T12:30:00Z",
        "decision": {"kind": kind, "context_id": "REL-42", "requested_outcome": "ready"},
        "result": "PASS",
        "sources": [
            {"id": source, "category": category, "status": "available", "observed_at": "2026-07-18T11:55:00Z", "provenance": {"revision": f"REV-{index}", "recorded_at": "2026-07-18T11:55:00Z"}, "evidence_ref": f"EVID-{index}"}
            for index, (source, category) in enumerate(zip(("repository", "lifecycle", "tracker", "operations"), categories), start=1)
        ],
        "blockers": [],
    }


class LifecycleClaimGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.delivery_root = self.root / "delivery"
        self.delivery_root.mkdir()
        self.overlay_path = self.root / "overlay.json"
        self.snapshot_path = self.root / "snapshot.json"
        self.write(snapshot())

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write(self, data: dict) -> None:
        self.overlay_path.write_text(json.dumps(overlay()), encoding="utf-8")
        self.snapshot_path.write_text(json.dumps(data), encoding="utf-8")

    def run_gate(self, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            ["python3", str(GATE), "--delivery-root", str(self.delivery_root), "--claim-output", "claims/REL-42.json", "--overlay", str(self.overlay_path), "--snapshot", str(self.snapshot_path), "--claim-kind", "release_readiness", "--claim-context", "REL-42", "--now", NOW, *extra],
            text=True,
            capture_output=True,
            check=False,
        )
        return result, json.loads(result.stdout)

    def test_current_snapshot_records_claim_with_digest(self) -> None:
        result, payload = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        claim_path = self.delivery_root / "claims" / "REL-42.json"
        self.assertTrue(payload["claim_written"])
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        self.assertEqual(claim["status"], "accepted")
        self.assertEqual(claim["control_plane_snapshot"]["id"], "CPS-42")
        self.assertEqual(claim["control_plane_snapshot"]["artifact"], str(self.snapshot_path.resolve()))
        self.assertEqual(len(claim["control_plane_snapshot"]["sha256"]), 64)
        self.assertEqual(claim["control_plane_snapshot"]["source_revisions"], [
            {"id": "repository", "revision": "REV-1"},
            {"id": "lifecycle", "revision": "REV-2"},
            {"id": "tracker", "revision": "REV-3"},
            {"id": "operations", "revision": "REV-4"},
        ])

    def test_all_governed_claim_kinds_can_be_accepted(self) -> None:
        for kind in ("release_readiness", "release_completion", "milestone_completion", "deployment_readiness"):
            self.write(snapshot(kind))
            result, payload = self.run_gate("--claim-kind", kind, "--claim-output", f"claims/{kind}.json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(payload["claim_written"])

    def test_unsupported_claim_kind_is_blocked(self) -> None:
        result, payload = self.run_gate("--claim-kind", "manual_completion")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertEqual(payload["status"], "unverified")
        self.assertIn("unsupported_claim_kind", {item["code"] for item in payload["findings"]})

    def test_expired_snapshot_cannot_write_positive_claim(self) -> None:
        data = snapshot()
        data["expires_at"] = "2026-07-18T11:59:59Z"
        self.write(data)
        result, payload = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertIn("baseline_stale_or_unknown", {item["code"] for item in payload["findings"]})
        report = json.loads((self.delivery_root / "claims" / "REL-42.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "unverified")
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["control_plane_snapshot"]["artifact"], str(self.snapshot_path.resolve()))

    def test_absent_snapshot_writes_unverified_report(self) -> None:
        self.snapshot_path.unlink()
        result, payload = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertEqual(payload["status"], "unverified")
        self.assertIn("control_plane_snapshot_unreadable", {item["code"] for item in payload["findings"]})
        report = json.loads((self.delivery_root / "claims" / "REL-42.json").read_text(encoding="utf-8"))
        self.assertEqual(report["result"], "BLOCKED")
        self.assertNotIn("claim", report)

    def test_wrong_claim_context_cannot_write_positive_claim(self) -> None:
        result, payload = self.run_gate("--claim-context", "REL-999")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertIn("control_plane_decision_mismatch", {item["code"] for item in payload["findings"]})

    def test_unavailable_and_conflicting_sources_write_unverified_reports(self) -> None:
        for status, blocker in (("unavailable", "source_unavailable"), ("conflict", "source_conflict")):
            with self.subTest(status=status):
                data = snapshot()
                data["sources"][2]["status"] = status
                data["result"] = "BLOCKED"
                data["blockers"] = [{"code": blocker, "source_id": "tracker", "summary": "Required source cannot support this claim."}]
                self.write(data)
                result, payload = self.run_gate("--claim-output", f"claims/{status}.json")
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["claim_written"])
                self.assertEqual(payload["status"], "unverified")
                self.assertIn(blocker, {item["code"] for item in payload["findings"]})
                report = json.loads((self.delivery_root / "claims" / f"{status}.json").read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "unverified")
                self.assertNotIn("claim", report)

    def test_claim_output_cannot_escape_delivery_root(self) -> None:
        result, payload = self.run_gate("--claim-output", "../escape.json")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertIn("claim_output_invalid", {item["code"] for item in payload["findings"]})

    def test_existing_claim_is_not_overwritten(self) -> None:
        initial, _ = self.run_gate()
        result, payload = self.run_gate()
        self.assertEqual(initial.returncode, 0)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertIn("claim_already_exists", {item["code"] for item in payload["findings"]})

    def test_unverified_report_is_not_overwritten_by_later_positive_claim(self) -> None:
        data = snapshot()
        data["expires_at"] = "2026-07-18T11:59:59Z"
        self.write(data)
        initial, _ = self.run_gate()
        initial_report = (self.delivery_root / "claims" / "REL-42.json").read_text(encoding="utf-8")
        self.write(snapshot())
        result, payload = self.run_gate()
        self.assertEqual(initial.returncode, 1)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["claim_written"])
        self.assertIn("claim_already_exists", {item["code"] for item in payload["findings"]})
        self.assertEqual((self.delivery_root / "claims" / "REL-42.json").read_text(encoding="utf-8"), initial_report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
