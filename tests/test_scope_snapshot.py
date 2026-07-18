#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_scope_snapshot.py"


def snapshot() -> dict:
    return {
        "schema_version": 1,
        "requirement_id": "REQ-42",
        "revision": 3,
        "status": "approved",
        "approval_ref": "APR-42-R3",
        "risk_assessment": "Checkout behavior remains within the approved provider boundary.",
        "evidence_refs": ["EVID-42-TEST"],
        "change_request_ref": "CR-42-R3",
        "supersedes": "REQ-42@2",
        "source_refs": ["DISC-17", "DEC-08"],
        "scope_summary": "Implement the approved checkout adjustment.",
        "acceptance_criteria": ["The defined checkout behavior passes its focused test."],
        "non_goals": ["Do not alter the payment provider."],
        "locked_decisions": [{"id": "DEC-08", "rule": "Retain the approved callback format."}],
        "change_policy": "lead_approved_revision",
    }


class ScopeSnapshotValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.snapshot_path = self.root / "scope.json"
        self.snapshot_path.write_text(json.dumps(snapshot(), indent=2) + "\n", encoding="utf-8")
        digest = hashlib.sha256(self.snapshot_path.read_bytes()).hexdigest()
        self.state_path = self.root / "state.json"
        self.state_path.write_text(json.dumps({
            "scope_snapshot": "scope.json",
            "scope_revision": 3,
            "scope_snapshot_sha256": digest,
            "approved_refs": ["REQ-42@3"],
        }), encoding="utf-8")
        self.kickoff_path = self.root / "kickoff.md"
        self.kickoff_path.write_text("# kickoff\nApproved scope: REQ-42@3\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_validator(self) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [str(VALIDATOR), "--state", str(self.state_path), "--kickoff", str(self.kickoff_path)],
            text=True, capture_output=True, check=False,
        )
        return result, json.loads(result.stdout)

    def test_valid_bound_scope(self) -> None:
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["scope"]["requirement_id"], "REQ-42")
        self.assertEqual(payload["scope"]["revision"], 3)

    def test_rejects_stale_digest_and_revision(self) -> None:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["scope_revision"] = 2
        state["scope_snapshot_sha256"] = "0" * 64
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertEqual({item["code"] for item in payload["findings"]}, {"scope_revision_mismatch", "scope_digest_mismatch"})

    def test_rejects_missing_current_approved_ref(self) -> None:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["approved_refs"] = ["REQ-42@2"]
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("scope_approved_ref_missing", {item["code"] for item in payload["findings"]})

    def test_rejects_revision_without_approval_or_change_trace(self) -> None:
        invalid = snapshot()
        invalid.pop("approval_ref")
        invalid.pop("change_request_ref")
        invalid.pop("supersedes")
        self.snapshot_path.write_text(json.dumps(invalid), encoding="utf-8")
        digest = hashlib.sha256(self.snapshot_path.read_bytes()).hexdigest()
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["scope_snapshot_sha256"] = digest
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in payload["findings"]}
        self.assertTrue({"scope_approval_ref_invalid", "scope_change_request_ref_invalid", "scope_supersedes_invalid"}.issubset(codes))

    def test_rejects_unsafe_snapshot_path(self) -> None:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["scope_snapshot"] = "../scope.json"
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result, payload = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("scope_snapshot_path_unsafe", {item["code"] for item in payload["findings"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
