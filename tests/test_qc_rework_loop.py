#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "run_qc_rework_loop.py"


class QcReworkLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.state_path = self.root / "delivery-state.json"
        self.state_path.write_text(json.dumps({"delivery_profile": "guarded", "status": "running", "current_stage": "qc-review"}), encoding="utf-8")
        self.impl_handoff = self.write("impl.md", "# implementation\n")
        self.impl_context = self.write("impl-context.md", "# context\n")
        self.qc_handoff = self.write("qc.md", "# QC\n")
        self.log_path = self.root / "launcher-log.jsonl"
        self.scenario_path = self.root / "scenario.json"
        self.impl_launcher = self.write_launcher("impl-launcher.py", "impl")
        self.qc_launcher = self.write_launcher("qc-launcher.py", "qc")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def write_launcher(self, name: str, kind: str) -> Path:
        path = self.root / name
        path.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env python3
            import json
            import os
            import sys
            from pathlib import Path

            kind = {kind!r}
            root = Path(os.environ['QC_LOOP_FIXTURE_ROOT'])
            with (root / 'launcher-log.jsonl').open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({{'kind': kind, 'argv': sys.argv[1:], 'cycle': os.environ.get('STAGEPILOT_VERDICT_CYCLE')}}) + '\\n')
            if kind == 'qc':
                scenario = json.loads((root / 'scenario.json').read_text(encoding='utf-8'))
                cycle = int(os.environ['STAGEPILOT_VERDICT_CYCLE'])
                outcomes = scenario.get('outcomes', scenario) if isinstance(scenario, dict) else scenario
                outcome = outcomes[cycle - 1]
                if outcome == 'qc_error':
                    raise SystemExit(7)
                if outcome == 'missing':
                    raise SystemExit(0)
                output = Path(sys.argv[sys.argv.index('--verdict-output') + 1])
                payload = {{'schema_version': 1, 'acceptance_scope': os.environ['STAGEPILOT_ACCEPTANCE_SCOPE'], 'verdict': outcome}}
                if outcome == 'fail':
                    failure_class = scenario.get('failure_class', 'implementation_defect') if isinstance(scenario, dict) else 'implementation_defect'
                    payload.update({{'failure_class': failure_class, 'gaps': ['The approved behavior is still incorrect.'], 'required_follow_up': 'Correct the approved behavior.', 'evidence_paths': ['focused-test']}})
                output.write_text(json.dumps(payload), encoding='utf-8')
            raise SystemExit(0)
        """), encoding="utf-8")
        path.chmod(0o755)
        return path

    def run_controller(
        self,
        outcomes: list[str] | dict[str, object],
        *,
        validation_command: str = "true",
    ) -> subprocess.CompletedProcess[str]:
        data = outcomes if isinstance(outcomes, dict) else list(outcomes)
        self.scenario_path.write_text(json.dumps(data), encoding="utf-8")
        environment = os.environ.copy()
        environment["QC_LOOP_FIXTURE_ROOT"] = str(self.root)
        return subprocess.run([
            "python3", str(CONTROLLER),
            "--delivery-state", str(self.state_path),
            "--acceptance-scope", "REQ-42@3:checkout",
            "--impl-handoff", str(self.impl_handoff),
            "--implementation-context", str(self.impl_context),
            "--qc-handoff", str(self.qc_handoff),
            "--validation-command", validation_command,
            "--impl-launcher", str(self.impl_launcher),
            "--qc-launcher", str(self.qc_launcher),
        ], text=True, capture_output=True, check=False, env=environment)

    def state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def launches(self) -> list[dict]:
        return [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines()]

    def test_first_qc_passes_without_rework(self) -> None:
        result = self.run_controller(["pass"])
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertEqual(state["qc_rework_loop"]["status"], "passed")
        self.assertEqual(state["qc_rework_loop"]["verdict_count"], 1)
        self.assertEqual(state["verdict_count_for_scope"], 1)
        self.assertTrue(state["current_qc_verdict_artifact"].endswith("qc-verdict-01.json"))
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc"])
        rerun = self.run_controller(["fail"])
        self.assertEqual(rerun.returncode, 0)
        self.assertTrue(json.loads(rerun.stdout)["idempotent"])
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc"])

    def test_same_scope_failure_reworks_then_fresh_qc_passes(self) -> None:
        result = self.run_controller(["fail", "pass"], validation_command='python3 -c "import sys; sys.exit(0)"')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertEqual(state["qc_rework_loop"]["verdict_count"], 2)
        self.assertEqual(state["qc_rework_loop"]["status"], "passed")
        self.assertEqual(state["verdict_count_for_scope"], 2)
        self.assertTrue(state["current_qc_verdict_artifact"].endswith("qc-verdict-02.json"))
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc", "impl", "qc"])
        rework = self.root / state["qc_rework_loop"]["last_rework_handoff"]
        self.assertIn("Bounded implementation rework", rework.read_text(encoding="utf-8"))

    def test_third_unresolved_verdict_stops_and_escalates(self) -> None:
        result = self.run_controller(["fail", "fail", "fail"])
        self.assertEqual(result.returncode, 1)
        state = self.state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["current_stage"], "lead-escalation")
        self.assertEqual(state["blocker_code"], "qc_rework_budget_exhausted")
        self.assertEqual(state["reason_class"], "verification_or_release_risk")
        self.assertEqual(state["qc_rework_loop"]["verdict_count"], 3)
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc", "impl", "qc", "impl", "qc"])
        escalation = self.root / state["qc_rework_loop"]["escalation_artifact"]
        self.assertEqual(json.loads(escalation.read_text(encoding="utf-8"))["reason_class"], "verification_or_release_risk")

    def test_governance_failure_escalates_without_impl_retry(self) -> None:
        result = self.run_controller({"outcomes": ["fail"], "failure_class": "scope_or_requirements"})
        self.assertEqual(result.returncode, 1)
        state = self.state()
        self.assertEqual(state["blocker_code"], "qc_non_reworkable_failure")
        self.assertEqual(state["qc_rework_loop"]["verdict_count"], 1)
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc"])

    def test_interrupted_rework_blocks_instead_of_skipping_or_duplicating_work(self) -> None:
        state = self.state()
        state.update({
            "current_stage": "impl-running",
            "qc_rework_loop": {
                "schema_version": 1,
                "acceptance_scope": "REQ-42@3:checkout",
                "verdict_count": 1,
                "status": "running",
            },
        })
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_controller(["pass"])
        self.assertEqual(result.returncode, 1)
        state = self.state()
        self.assertEqual(state["blocker_code"], "qc_rework_controller_interrupted")
        self.assertFalse(self.log_path.exists())

    def test_missing_canonical_qc_verdict_is_integrity_failure(self) -> None:
        result = self.run_controller(["missing"])
        self.assertEqual(result.returncode, 1)
        state = self.state()
        self.assertEqual(state["blocker_code"], "qc_verdict_integrity_failure")
        self.assertEqual(state["qc_rework_loop"]["verdict_count"], 1)
        self.assertTrue(state["current_qc_verdict_artifact"].endswith("qc-verdict-01.json"))
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc"])

    def test_failed_qc_launcher_keeps_the_fresh_verdict_trail(self) -> None:
        result = self.run_controller(["qc_error"])
        self.assertEqual(result.returncode, 1)
        state = self.state()
        self.assertEqual(state["blocker_code"], "supervisor_integrity_failure")
        self.assertEqual(state["qc_rework_loop"]["verdict_count"], 1)
        self.assertTrue(state["current_qc_verdict_artifact"].endswith("qc-verdict-01.json"))
        self.assertEqual([launch["kind"] for launch in self.launches()], ["qc"])

    def test_second_controller_is_rejected_while_state_lock_is_held(self) -> None:
        lock_path = self.state_path.with_suffix(self.state_path.suffix + '.qc-rework.lock')
        with lock_path.open('a+', encoding='utf-8') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_controller(["pass"])
        self.assertEqual(result.returncode, 2)
        self.assertIn('already owns this delivery state', result.stdout)
        self.assertFalse(self.log_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
