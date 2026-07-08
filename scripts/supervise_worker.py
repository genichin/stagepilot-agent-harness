#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


RESULT_EXIT_CODES = {
    'done': 0,
    'blocked': 3,
    'worker_exit_nonzero': 10,
    'timeout_no_progress': 124,
    'timeout_with_progress': 125,
    'max_runtime_exceeded': 126,
}


@dataclass
class EvidenceState:
    git_status: str
    git_diff_stat: str
    progress_mtimes: dict[str, float]



def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()



def run_git(workdir: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ['git', '-C', str(workdir), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ''
    return proc.stdout.strip()



def log_tail(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ''
    data = path.read_text(encoding='utf-8', errors='replace')
    if len(data) <= max_chars:
        return data
    return data[-max_chars:]



def collect_progress_files(progress_artifact: Path | None, progress_dir: Path | None) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    if progress_artifact is not None:
        seen.add(progress_artifact)
        files.append(progress_artifact)
    if progress_dir is not None and progress_dir.exists():
        for path in sorted(progress_dir.glob('*.md')):
            if path not in seen:
                files.append(path)
                seen.add(path)
    return files



def snapshot_state(workdir: Path, progress_artifact: Path | None, progress_dir: Path | None) -> EvidenceState:
    progress_mtimes: dict[str, float] = {}
    for path in collect_progress_files(progress_artifact, progress_dir):
        if path.exists():
            progress_mtimes[str(path.resolve())] = path.stat().st_mtime
    return EvidenceState(
        git_status=run_git(workdir, ['status', '--short']),
        git_diff_stat=run_git(workdir, ['diff', '--stat']),
        progress_mtimes=progress_mtimes,
    )



def progress_changes(previous: EvidenceState, current: EvidenceState) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    all_paths = sorted(set(previous.progress_mtimes) | set(current.progress_mtimes))
    for path in all_paths:
        before = previous.progress_mtimes.get(path)
        after = current.progress_mtimes.get(path)
        if before is None and after is not None:
            changes.append({'path': path, 'change': 'created', 'mtime': after})
        elif before is not None and after is None:
            changes.append({'path': path, 'change': 'removed'})
        elif before is not None and after is not None and after > before + 1e-9:
            changes.append({'path': path, 'change': 'updated', 'mtime': after})
    return changes



def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')



def terminate_process(proc: subprocess.Popen[str], grace_seconds: float = 5.0) -> int | None:
    if proc.poll() is not None:
        return proc.returncode
    proc.terminate()
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return proc.returncode
        time.sleep(0.1)
    if proc.poll() is None:
        proc.kill()
    return proc.wait(timeout=5)



def checkpoint_payload(*, index: int, elapsed_seconds: float, evidence_reasons: list[str], extension_granted: bool,
                       current: EvidenceState, progress_updates: list[dict[str, object]], child_log: Path,
                       child_completed: bool, child_exit_code: int | None, decision: str) -> dict[str, object]:
    return {
        'checkpoint_index': index,
        'timestamp': iso_now(),
        'elapsed_seconds': round(elapsed_seconds, 3),
        'decision': decision,
        'extension_granted': extension_granted,
        'evidence_reasons': evidence_reasons,
        'git_status_short': current.git_status,
        'git_diff_stat': current.git_diff_stat,
        'progress_artifacts_modified': progress_updates,
        'child_completed': child_completed,
        'child_exit_code': child_exit_code,
        'child_log_tail': log_tail(child_log),
    }



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Supervise a bounded child worker with evidence-based checkpoint extension.')
    parser.add_argument('--label', required=True)
    parser.add_argument('--workdir', required=True)
    parser.add_argument('--handoff-artifact')
    parser.add_argument('--delivery-state')
    parser.add_argument('--profile')
    parser.add_argument('--progress-artifact')
    parser.add_argument('--progress-dir', default='.stagepilot/worker-progress')
    parser.add_argument('--output-root', default='.stagepilot/worker-supervision')
    parser.add_argument('--checkpoint-minutes', type=float, default=10.0)
    parser.add_argument('--max-minutes', type=float, default=60.0)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    return parser



def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = list(args.command)
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('missing child command')
    if args.checkpoint_minutes <= 0 or args.max_minutes <= 0:
        parser.error('checkpoint and max minutes must be positive')
    if args.max_minutes < args.checkpoint_minutes:
        parser.error('max-minutes must be >= checkpoint-minutes')

    workdir = Path(args.workdir).resolve()
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (workdir / output_root).resolve()
    progress_dir = Path(args.progress_dir)
    if not progress_dir.is_absolute():
        progress_dir = (workdir / progress_dir).resolve()
    progress_dir.mkdir(parents=True, exist_ok=True)

    progress_artifact: Path | None = None
    if args.progress_artifact:
        progress_artifact = Path(args.progress_artifact)
        if not progress_artifact.is_absolute():
            progress_artifact = (workdir / progress_artifact).resolve()
        progress_artifact.parent.mkdir(parents=True, exist_ok=True)

    session_id = f"{args.label}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = output_root / session_id
    checkpoints_dir = run_dir / 'checkpoints'
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    child_log = run_dir / 'child.log'
    child_exit_file = run_dir / 'child.exit'
    final_result_file = run_dir / 'final-result.json'
    summary_file = run_dir / 'summary.txt'

    checkpoint_seconds = args.checkpoint_minutes * 60.0
    max_seconds = args.max_minutes * 60.0

    metadata = {
        'session_id': session_id,
        'label': args.label,
        'profile': args.profile,
        'workdir': str(workdir),
        'handoff_artifact': args.handoff_artifact,
        'delivery_state': args.delivery_state,
        'progress_artifact': str(progress_artifact) if progress_artifact else None,
        'progress_dir': str(progress_dir),
        'output_root': str(output_root),
        'run_dir': str(run_dir),
        'checkpoint_minutes': args.checkpoint_minutes,
        'max_minutes': args.max_minutes,
        'command': command,
        'command_display': shlex.join(command),
        'started_at': iso_now(),
    }
    write_json(run_dir / 'metadata.json', metadata)

    with child_log.open('w', encoding='utf-8') as log_handle:
        proc = subprocess.Popen(
            command,
            cwd=str(workdir),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

    start = time.monotonic()
    previous = snapshot_state(workdir, progress_artifact, progress_dir)
    checkpoints_taken = 0
    extensions_granted = 0
    observed_progress = False
    result_class: str | None = None
    result_reason = ''
    last_progress_updates: list[dict[str, object]] = []
    last_evidence_reasons: list[str] = []

    while True:
        rc = proc.poll()
        elapsed = time.monotonic() - start
        if rc is not None:
            child_exit_file.write_text(f'{rc}\n', encoding='utf-8')
            if rc == 0:
                result_class = 'done'
                result_reason = 'child exited 0 before supervisor stop'
            else:
                result_class = 'worker_exit_nonzero'
                result_reason = f'child exited non-zero: {rc}'
            break

        next_checkpoint_at = (checkpoints_taken + 1) * checkpoint_seconds
        if elapsed < next_checkpoint_at:
            time.sleep(min(0.5, next_checkpoint_at - elapsed))
            continue

        checkpoints_taken += 1
        current = snapshot_state(workdir, progress_artifact, progress_dir)
        updates = progress_changes(previous, current)
        reasons: list[str] = []
        if current.git_status != previous.git_status and current.git_status.strip():
            reasons.append('git_status_changed')
        if current.git_diff_stat != previous.git_diff_stat and current.git_diff_stat.strip():
            reasons.append('git_diff_stat_changed')
        if updates:
            reasons.append('progress_artifact_updated')
        evidence = bool(reasons)
        observed_progress = observed_progress or evidence
        last_progress_updates = updates
        last_evidence_reasons = reasons

        child_completed = proc.poll() is not None
        decision = 'extend' if evidence else 'stop_no_progress'
        extension_granted = False
        if child_completed:
            rc = proc.returncode
            child_exit_file.write_text(f'{rc}\n', encoding='utf-8')
            payload = checkpoint_payload(
                index=checkpoints_taken,
                elapsed_seconds=elapsed,
                evidence_reasons=reasons,
                extension_granted=False,
                current=current,
                progress_updates=updates,
                child_log=child_log,
                child_completed=True,
                child_exit_code=rc,
                decision='child_completed',
            )
            write_json(checkpoints_dir / f'checkpoint-{checkpoints_taken:03d}.json', payload)
            if rc == 0:
                result_class = 'done'
                result_reason = 'child exited 0 at checkpoint boundary'
            else:
                result_class = 'worker_exit_nonzero'
                result_reason = f'child exited non-zero at checkpoint boundary: {rc}'
            previous = current
            break

        if elapsed + checkpoint_seconds > max_seconds + 1e-9:
            decision = 'stop_max_runtime' if evidence else 'stop_no_progress'
        elif evidence:
            extension_granted = True
            extensions_granted += 1
            decision = 'extend'

        payload = checkpoint_payload(
            index=checkpoints_taken,
            elapsed_seconds=elapsed,
            evidence_reasons=reasons,
            extension_granted=extension_granted,
            current=current,
            progress_updates=updates,
            child_log=child_log,
            child_completed=False,
            child_exit_code=None,
            decision=decision,
        )
        write_json(checkpoints_dir / f'checkpoint-{checkpoints_taken:03d}.json', payload)

        if extension_granted:
            previous = current
            continue

        terminated_rc = terminate_process(proc)
        if terminated_rc is not None:
            child_exit_file.write_text(f'{terminated_rc}\n', encoding='utf-8')
        if evidence:
            result_class = 'max_runtime_exceeded' if elapsed >= max_seconds - 1e-9 or elapsed + checkpoint_seconds > max_seconds + 1e-9 else 'timeout_with_progress'
            result_reason = 'progress evidence existed but supervisor refused further extension at hard cap'
        else:
            result_class = 'timeout_no_progress'
            result_reason = 'no concrete progress evidence at checkpoint'
        previous = current
        break

    finished_at = iso_now()
    total_elapsed = time.monotonic() - start
    child_exit_code: int | None = None
    if child_exit_file.exists():
        try:
            child_exit_code = int(child_exit_file.read_text(encoding='utf-8').strip())
        except ValueError:
            child_exit_code = None

    if result_class is None:
        result_class = 'worker_exit_nonzero'
        result_reason = 'supervisor ended without explicit result class'

    shell_exit_code = RESULT_EXIT_CODES[result_class]
    final_payload = {
        'session_id': session_id,
        'label': args.label,
        'result_class': result_class,
        'result_reason': result_reason,
        'shell_exit_code': shell_exit_code,
        'child_exit_code': child_exit_code,
        'elapsed_seconds': round(total_elapsed, 3),
        'checkpoints_taken': checkpoints_taken,
        'extensions_granted': extensions_granted,
        'observed_progress': observed_progress,
        'last_evidence_reasons': last_evidence_reasons,
        'last_progress_updates': last_progress_updates,
        'run_dir': str(run_dir),
        'log_file': str(child_log),
        'child_exit_file': str(child_exit_file),
        'finished_at': finished_at,
    }
    write_json(final_result_file, final_payload)
    summary_file.write_text(
        '\n'.join([
            f'result_class: {result_class}',
            f'shell_exit_code: {shell_exit_code}',
            f'child_exit_code: {child_exit_code}',
            f'checkpoints_taken: {checkpoints_taken}',
            f'extensions_granted: {extensions_granted}',
            f'elapsed_seconds: {round(total_elapsed, 3)}',
            f'run_dir: {run_dir}',
            f'log_file: {child_log}',
        ]) + '\n',
        encoding='utf-8',
    )

    print(f'session_id: {session_id}')
    print(f'result_class: {result_class}')
    print(f'shell_exit_code: {shell_exit_code}')
    print(f'child_exit_code: {child_exit_code}')
    print(f'checkpoints_taken: {checkpoints_taken}')
    print(f'extensions_granted: {extensions_granted}')
    print(f'run_dir: {run_dir}')
    print(f'log_file: {child_log}')
    print(f'final_result_file: {final_result_file}')
    return shell_exit_code


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
