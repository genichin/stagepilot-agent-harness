# Supervised worker lifecycle

Use this reference when diagnosing or operating runner-owned supervised `dev-impl` / `dev-qc` workers.

## Core rule

Supervised child work should run as a launcher-managed background/tmux execution by default. The supervisor budget (`checkpoint_minutes`, `max_minutes`) must not be nested inside a shorter LLM terminal timeout. Foreground supervised execution is only valid for deliberately short runs where the caller timeout comfortably exceeds the supervised max runtime.

## Integrity contract

The canonical supervised completion signal is `worker-supervision/<session>/final-result.json`. Runner must poll:

- launcher `exit_file`;
- worker launcher log;
- supervisor `final-result.json`;
- progress artifact and git diff as secondary evidence.

If `final-result.json` is missing, or if it reports `result_class=supervisor_interrupted`, classify the issue as `supervisor_integrity_failure` / harness execution failure. Do not treat child-log test success alone as canonical implementation completion, and do not conflate supervisor integrity failure with an implementation acceptance defect.

## Signal handling

`supervise_worker.py` writes `result_class=supervisor_interrupted` when it receives SIGTERM/SIGINT before child completion. It should terminate the child and preserve metadata including `child_pid`, log path, progress evidence, and signal name.

## Bounded rework autonomy

When implementation output is close but violates explicit same-scope implementation-context details, such as section labels, CTA wording, metric labels, or required visible strings, runner may create a fresh bounded rework handoff without lead escalation. Escalate only for contract ambiguity, scope change, data-source uncertainty, governance/product decision, or repeated rework loop exhaustion.

## Machine-checkable acceptance

For UI/copy-sensitive slices, implementation-context should include machine-checkable assertions:

```yaml
required_visible_strings:
  - Example CTA
forbidden_visible_strings:
  - /home/
  - raw_payload
required_metric_labels:
  - Example metric
```

Runner should check these before QC so known implementation mismatches do not consume independent QC cycles.
