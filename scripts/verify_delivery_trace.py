#!/usr/bin/env python3
"""One-command, read-only verification of a StagePilot delivery's evidence and order."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reconcile_evidence import digest, reconcile

STAGES = {
    'fast': ('kickoff', 'impl-running', 'targeted-validation', 'merge-ready'),
    'standard': ('kickoff', 'impl-running', 'qc-review', 'merge-ready'),
    'guarded': ('kickoff', 'impl-running', 'qc-review', 'merge-ready'),
}


def load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'expected JSON object: {path}')
    return payload


def load_trace(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not path.is_file():
        return [], [{'class': 'missing-transition-trace', 'path': str(path), 'action': 'escalate'}]
    events: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    expected_sequence = 1
    for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            findings.append({'class': 'invalid-transition-event', 'path': f'{path}:{line_no}', 'action': 'escalate'}); continue
        fields = ('seq', 'at', 'stage', 'actor', 'artifact')
        if not isinstance(event, dict) or any(not event.get(field) for field in fields) or not isinstance(event.get('seq'), int):
            findings.append({'class': 'invalid-transition-event', 'path': f'{path}:{line_no}', 'action': 'escalate'}); continue
        if event['seq'] != expected_sequence:
            findings.append({'class': 'non-monotonic-transition-sequence', 'path': f'{path}:{line_no}', 'action': 'escalate'})
        expected_sequence += 1
        events.append(event)
    if not events and not findings:
        findings.append({'class': 'empty-transition-trace', 'path': str(path), 'action': 'escalate'})
    return events, findings


def validate_order(state: dict[str, Any], events: list[dict[str, Any]], trace: Path) -> list[dict[str, str]]:
    profile = state.get('delivery_profile')
    if profile not in STAGES:
        return [{'class': 'invalid-delivery-profile', 'path': str(trace.parent / 'state.json'), 'action': 'escalate'}]
    required = list(STAGES[profile])
    stages = [event['stage'] for event in events]
    findings: list[dict[str, str]] = []
    if profile == 'standard' and 'qc-review' not in stages:
        required.remove('qc-review')
        if not state.get('qc_waiver_reason'):
            findings.append({'class': 'standard-qc-waiver-missing', 'path': str(trace.parent / 'state.json'), 'action': 'escalate'})
        if not state.get('residual_risk'):
            findings.append({'class': 'standard-residual-risk-missing', 'path': str(trace.parent / 'state.json'), 'action': 'escalate'})
    if profile == 'fast':
        for key, code in (('qc_waiver_reason', 'fast-qc-waiver-missing'), ('validation_commands', 'fast-validation-missing'), ('residual_risk', 'fast-residual-risk-missing')):
            if not state.get(key):
                findings.append({'class': code, 'path': str(trace.parent / 'state.json'), 'action': 'escalate'})
    if stages != required[:len(stages)]:
        findings.append({'class': 'invalid-stage-order', 'path': str(trace), 'action': 'escalate'})
    if state.get('status') == 'done' and stages != required:
        findings.append({'class': 'incomplete-completion-trace', 'path': str(trace), 'action': 'escalate'})
    return findings


def verify(evidence: Path, catalog: Path, now: datetime, stale_seconds: int) -> dict[str, Any]:
    base = reconcile(evidence, digest(catalog), now, stale_seconds)
    findings = list(base['findings'])
    try:
        state = load_object(evidence / 'state.json')
    except (OSError, ValueError, json.JSONDecodeError):
        state = {}
    events, trace_findings = load_trace(evidence / 'state-transitions.jsonl')
    findings.extend(trace_findings)
    if state and not trace_findings:
        findings.extend(validate_order(state, events, evidence / 'state-transitions.jsonl'))
    return {'valid': not findings, 'evidence': str(evidence), 'delivery_profile': state.get('delivery_profile'), 'checked_transitions': len(events), 'findings': findings, 'purge_performed': False, 'reporting_requires_explicit_publish': True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--catalog', required=True, type=Path)
    parser.add_argument('--now')
    parser.add_argument('--stale-seconds', default=3600, type=int)
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now.replace('Z', '+00:00')) if args.now else datetime.now(timezone.utc)
    result = verify(args.evidence_dir.expanduser().resolve(), args.catalog.expanduser().resolve(), now, args.stale_seconds)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
