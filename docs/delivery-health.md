# Delivery health and harness observations

An adopter project keeps one explicit delivery evidence directory. The runner records each ordered stage there; users do not inspect raw worker logs.

## Runner: record transitions

Record a transition when its handoff/evidence artifact is written. `artifact` is a relative identifier, never a credential, remote URL, or raw worker log.

```bash
python3 /path/to/stagepilot-agent-harness/scripts/record_delivery_transition.py \
  --evidence-dir /abs/project/.stagepilot/delivery/<delivery-id> \
  --stage kickoff --actor lead --artifact kickoff.md
```

Record the profile path in order:

- `guarded`: `kickoff → impl-running → qc-review → merge-ready`
- `fast`: `kickoff → impl-running → targeted-validation → merge-ready`; root state must also record `qc_waiver_reason`, `validation_commands`, and `residual_risk`.
- `standard`: follows guarded, or may omit `qc-review` only with `qc_waiver_reason` and `residual_risk` in root state.

## User: one verification command

After delivery, run the health check once. It is read-only and returns exit `0` only when both reconciliation and sequence checks pass.

```bash
python3 /path/to/stagepilot-agent-harness/scripts/verify_delivery_trace.py \
  --evidence-dir /abs/project/.stagepilot/delivery/<delivery-id> \
  --catalog /path/to/stagepilot-agent-harness/governance/skill-catalog.json \
  > /abs/project/.stagepilot/delivery/<delivery-id>/delivery-health.json
```

- `valid: true`: harness evidence and expected sequence are healthy.
- `valid: false`: inspect only finding codes; do not paste raw worker logs into an issue.

## Failure report and optional publish

Create a local redacted issue draft first:

```bash
python3 /path/to/stagepilot-agent-harness/scripts/report_harness_observation.py \
  --verification-result /abs/project/.stagepilot/delivery/<delivery-id>/delivery-health.json \
  --delivery-id <delivery-id> \
  --harness-revision "$(git -C /path/to/stagepilot-agent-harness rev-parse HEAD)" \
  --output /abs/project/.stagepilot/delivery/<delivery-id>/harness-observation.md
```

Review the draft. It intentionally contains only profile, finding codes, transition count, and harness revision. To publish it, the user must explicitly opt in:

```bash
python3 /path/to/stagepilot-agent-harness/scripts/report_harness_observation.py \
  --verification-result /abs/project/.stagepilot/delivery/<delivery-id>/delivery-health.json \
  --delivery-id <delivery-id> \
  --harness-revision "$(git -C /path/to/stagepilot-agent-harness rev-parse HEAD)" \
  --output /abs/project/.stagepilot/delivery/<delivery-id>/harness-observation.md \
  --repo genichin/stagepilot-agent-harness --publish
```

`--publish` checks GitHub authentication and creates an issue only for a failed health result. Successful deliveries never create issues.
