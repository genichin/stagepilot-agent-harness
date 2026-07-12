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
    'timeout_no_progress_read_loop': 124,
    'timeout_no_progress_progress_artifact_missing': 124,
    'timeout_with_progress': 125,
    'max_runtime_exceeded': 126,
    'first_progress_deadline_exceeded': 127,
    'early_context_compaction_loop': 128,
    'early_read_loop_no_diff': 129,
    'supervisor_interrupted': 130,
}


@dataclass
class EvidenceState:
    git_status: str
    git_diff_stat: str
    progress_mtimes: dict[str, float]


@dataclass
class LogSignals:
    compact_hits: int
    read_hits: int
    search_hits: int
    write_hits: int



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



def analyze_log(path: Path, max_chars: int = 32000) -> LogSignals:
    log_text = log_tail(path, max_chars=max_chars)
    lowered = log_text.lower()
    compact_hits = (
        lowered.count('context compact')
        + lowered.count('context compaction')
        + lowered.count('compacting context')
        + lowered.count('compacting conversation')
        + lowered.count('session compressed')
    )
    read_hits = (
        log_text.count('📖 read')
        + lowered.count('read_file(')
        + lowered.count('read file')
    )
    search_hits = (
        log_text.count('🔎 search')
        + log_text.count('🔎 grep')
        + log_text.count('🔎 find')
        + lowered.count('search_files(')
    )
    write_hits = (
        log_text.count('✏️ write')
        + log_text.count('✍️  write')
        + log_text.count('✍️ write')
        + log_text.count('🩹 patch')
        + log_text.count('🔧 patch')
        + lowered.count('write_file(')
        + lowered.count('patch(')
    )
    return LogSignals(
        compact_hits=compact_hits,
        read_hits=read_hits,
        search_hits=search_hits,
        write_hits=write_hits,
    )


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



def classify_stall(*, child_log: Path, progress_artifact: Path | None, progress_dir: Path | None,
                   current: EvidenceState, evidence: bool, elapsed: float, max_seconds: float,
                   checkpoint_seconds: float) -> tuple[str, str, str | None, list[str]]:
    log_text = log_tail(child_log, max_chars=16000)
    lowered = log_text.lower()
    reasons: list[str] = []
    stall_subtype: str | None = None

    hard_cap_reached = elapsed >= max_seconds - 1e-9 or elapsed + checkpoint_seconds > max_seconds + 1e-9
    tracked_progress_files = collect_progress_files(progress_artifact, progress_dir)
    progress_artifact_missing = not any(path.exists() for path in tracked_progress_files)

    signals = analyze_log(child_log)
    compact_hits = signals.compact_hits
    read_hits = signals.read_hits
    search_hits = signals.search_hits
    write_hits = signals.write_hits
    if compact_hits:
        reasons.append(f'context_compaction_markers={compact_hits}')

    if read_hits or search_hits:
        reasons.append(f'read_markers={read_hits}')
        reasons.append(f'search_markers={search_hits}')
    if write_hits:
        reasons.append(f'write_markers={write_hits}')
    if progress_artifact_missing:
        reasons.append('progress_artifact_missing')

    if not evidence:
        if compact_hits >= 2:
            stall_subtype = 'context_compaction_loop'
        elif (read_hits + search_hits) >= 3 and write_hits == 0 and not current.git_diff_stat.strip():
            stall_subtype = 'read_loop_no_diff'
        elif progress_artifact_missing:
            stall_subtype = 'progress_artifact_missing'

    if evidence:
        return (
            'max_runtime_exceeded' if hard_cap_reached else 'timeout_with_progress',
            'progress evidence existed but supervisor refused further extension at hard cap',
            stall_subtype,
            reasons,
        )

    if stall_subtype == 'read_loop_no_diff':
        return (
            'timeout_no_progress_read_loop',
            'no concrete progress evidence at checkpoint; child log suggests a repeated read/search loop without diff or artifact output',
            stall_subtype,
            reasons,
        )
    if stall_subtype == 'progress_artifact_missing':
        return (
            'timeout_no_progress_progress_artifact_missing',
            'no concrete progress evidence at checkpoint; expected progress artifact was never produced',
            stall_subtype,
            reasons,
        )
    if stall_subtype == 'context_compaction_loop':
        return (
            'timeout_no_progress',
            'no concrete progress evidence at checkpoint; child log suggests repeated context compaction without shipped progress',
            stall_subtype,
            reasons,
        )
    return (
        'timeout_no_progress',
        'no concrete progress evidence at checkpoint',
        stall_subtype,
        reasons,
    )



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
    parser.add_argument('--first-progress-minutes', type=float, default=2.0,
                        help='Stop early if no git/progress evidence appears before this deadline. Set 0 to disable.')
    parser.add_argument('--early-compaction-threshold', type=int, default=2,
                        help='Stop early when log compaction markers reach this threshold without evidence. Set 0 to disable.')
    parser.add_argument('--early-read-search-threshold', type=int, default=20,
                        help='Stop early when read/search markers reach this threshold without evidence/diff. Set 0 to disable.')
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
    if args.first_progress_minutes < 0:
        parser.error('first-progress-minutes must be >= 0')
    if args.early_compaction_threshold < 0 or args.early_read_search_threshold < 0:
        parser.error('early guard thresholds must be >= 0')

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
        'first_progress_minutes': args.first_progress_minutes,
        'early_compaction_threshold': args.early_compaction_threshold,
        'early_read_search_threshold': args.early_read_search_threshold,
        'command': command,
        'command_display': shlex.join(command),
        'started_at': iso_now(),
        'child_pid': None,
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

    metadata['child_pid'] = proc.pid
    write_json(run_dir / 'metadata.json', metadata)

    interrupted_signal: str | None = None

    def request_interrupt(signum: int, _frame: object) -> None:
        nonlocal interrupted_signal
        interrupted_signal = signal.Signals(signum).name

    old_sigterm = signal.signal(signal.SIGTERM, request_interrupt)
    old_sigint = signal.signal(signal.SIGINT, request_interrupt)

    start = time.monotonic()
    previous = snapshot_state(workdir, progress_artifact, progress_dir)
    checkpoints_taken = 0
    extensions_granted = 0
    observed_progress = False
    first_progress_seconds = args.first_progress_minutes * 60.0

    def current_evidence(prev: EvidenceState) -> tuple[EvidenceState, list[dict[str, object]], list[str], bool]:
        cur = snapshot_state(workdir, progress_artifact, progress_dir)
        updates_ = progress_changes(prev, cur)
        reasons_: list[str] = []
        if cur.git_status != prev.git_status and cur.git_status.strip():
            reasons_.append('git_status_changed')
        if cur.git_diff_stat != prev.git_diff_stat and cur.git_diff_stat.strip():
            reasons_.append('git_diff_stat_changed')
        if updates_:
            reasons_.append('progress_artifact_updated')
        return cur, updates_, reasons_, bool(reasons_)

    result_class: str | None = None
    result_reason = ''
    stall_subtype: str | None = None
    stall_classification_reasons: list[str] = []
    last_progress_updates: list[dict[str, object]] = []
    last_evidence_reasons: list[str] = []

    while True:
        rc = proc.poll()
        elapsed = time.monotonic() - start
        if interrupted_signal is not None:
            terminated_rc = terminate_process(proc)
            if terminated_rc is not None:
                child_exit_file.write_text(f'{terminated_rc}\n', encoding='utf-8')
            current = snapshot_state(workdir, progress_artifact, progress_dir)
            _signals = analyze_log(child_log)
            result_class = 'supervisor_interrupted'
            result_reason = f'supervisor received {interrupted_signal} before child completion'
            stall_subtype = 'supervisor_interrupted'
            stall_classification_reasons = [
                f'context_compaction_markers={_signals.compact_hits}',
                f'read_markers={_signals.read_hits}',
                f'search_markers={_signals.search_hits}',
                f'write_markers={_signals.write_hits}',
                f'interrupted_signal={interrupted_signal}',
            ]
            last_progress_updates = progress_changes(previous, current)
            last_evidence_reasons = []
            if current.git_status != previous.git_status and current.git_status.strip():
                last_evidence_reasons.append('git_status_changed')
            if current.git_diff_stat != previous.git_diff_stat and current.git_diff_stat.strip():
                last_evidence_reasons.append('git_diff_stat_changed')
            if last_progress_updates:
                last_evidence_reasons.append('progress_artifact_updated')
            observed_progress = observed_progress or bool(last_evidence_reasons)
            previous = current
            break
        if rc is not None:
            child_exit_file.write_text(f'{rc}\n', encoding='utf-8')
            if rc == 0:
                result_class = 'done'
                result_reason = 'child exited 0 before supervisor stop'
            else:
                result_class = 'worker_exit_nonzero'
                result_reason = f'child exited non-zero: {rc}'
            break

        current, updates, reasons, evidence = current_evidence(previous)
        if evidence:
            observed_progress = True
            last_progress_updates = updates
            last_evidence_reasons = reasons

        signals = analyze_log(child_log)
        early_result: tuple[str, str, str | None] | None = None
        if not observed_progress and not evidence:
            if args.early_compaction_threshold and signals.compact_hits >= args.early_compaction_threshold:
                early_result = (
                    'early_context_compaction_loop',
                    'early stop: context compaction markers exceeded threshold before first concrete progress',
                    'context_compaction_loop',
                )
            elif (
                args.early_read_search_threshold
                and signals.read_hits + signals.search_hits >= args.early_read_search_threshold
                and signals.write_hits == 0
                and not current.git_diff_stat.strip()
            ):
                early_result = (
                    'early_read_loop_no_diff',
                    'early stop: read/search markers exceeded threshold before first concrete progress',
                    'read_loop_no_diff',
                )
            elif first_progress_seconds > 0 and elapsed >= first_progress_seconds:
                early_result = (
                    'first_progress_deadline_exceeded',
                    'early stop: first progress deadline elapsed without git/progress evidence',
                    'progress_artifact_missing',
                )

        if early_result is not None:
            terminated_rc = terminate_process(proc)
            if terminated_rc is not None:
                child_exit_file.write_text(f'{terminated_rc}\n', encoding='utf-8')
            result_class, result_reason, stall_subtype = early_result
            stall_classification_reasons = [
                f'context_compaction_markers={signals.compact_hits}',
                f'read_markers={signals.read_hits}',
                f'search_markers={signals.search_hits}',
                f'write_markers={signals.write_hits}',
                'first_progress_not_observed',
            ]
            last_progress_updates = updates
            last_evidence_reasons = reasons
            previous = current
            break

        next_checkpoint_at = (checkpoints_taken + 1) * checkpoint_seconds
        if elapsed < next_checkpoint_at:
            time.sleep(min(0.5, next_checkpoint_at - elapsed))
            continue

        checkpoints_taken += 1
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
        result_class, result_reason, stall_subtype, stall_classification_reasons = classify_stall(
            child_log=child_log,
            progress_artifact=progress_artifact,
            progress_dir=progress_dir,
            current=current,
            evidence=evidence,
            elapsed=elapsed,
            max_seconds=max_seconds,
            checkpoint_seconds=checkpoint_seconds,
        )
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
        'stall_subtype': stall_subtype,
        'stall_classification_reasons': stall_classification_reasons,
        'last_evidence_reasons': last_evidence_reasons,
        'last_progress_updates': last_progress_updates,
        'run_dir': str(run_dir),
        'log_file': str(child_log),
        'child_exit_file': str(child_exit_file),
        'child_pid': proc.pid,
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
    signal.signal(signal.SIGTERM, old_sigterm)
    signal.signal(signal.SIGINT, old_sigint)
    return shell_exit_code


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
