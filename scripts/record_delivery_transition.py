#!/usr/bin/env python3
"""Append one auditable, fixture-safe StagePilot delivery transition."""
from __future__ import annotations

import argparse
import fcntl
import json
from datetime import UTC, datetime
from pathlib import Path

TRACE_NAME = 'state-transitions.jsonl'
VALID_STAGES = {'kickoff', 'impl-running', 'targeted-validation', 'qc-review', 'merge-ready'}


def append_transition(evidence: Path, stage: str, actor: str, artifact: str, timestamp: str | None = None) -> dict[str, object]:
    if stage not in VALID_STAGES:
        raise ValueError(f'unknown stage: {stage}')
    artifact_path = Path(artifact)
    if not actor or not artifact:
        raise ValueError('actor and artifact are required')
    if artifact_path.is_absolute() or '..' in artifact_path.parts:
        raise ValueError('artifact must be a relative identifier without traversal')
    evidence.mkdir(parents=True, exist_ok=True)
    trace = evidence / TRACE_NAME
    with trace.open('a+', encoding='utf-8') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        sequence = sum(1 for line in handle if line.strip()) + 1
        event = {
            'seq': sequence,
            'at': timestamp or datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            'stage': stage,
            'actor': actor,
            'artifact': artifact,
        }
        handle.write(json.dumps(event, sort_keys=True) + '\n')
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return {'trace': str(trace), 'event': event}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--stage', required=True, choices=sorted(VALID_STAGES))
    parser.add_argument('--actor', required=True)
    parser.add_argument('--artifact', required=True, help='Relative evidence identifier; never pass credentials or raw logs.')
    parser.add_argument('--timestamp')
    args = parser.parse_args()
    try:
        print(json.dumps(append_transition(args.evidence_dir.expanduser().resolve(), args.stage, args.actor, args.artifact, args.timestamp), sort_keys=True))
    except (OSError, ValueError) as error:
        print(f'ERROR: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
