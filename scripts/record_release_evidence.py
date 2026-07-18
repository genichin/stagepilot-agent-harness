#!/usr/bin/env python3
"""Write an explicit, fixture-safe release evidence record after successful parity verification."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'expected JSON object: {path}')
    return payload


def build_record(manifest_path: Path, parity_path: Path, verifier_version: str, timestamp: str | None = None) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    parity = load_json(parity_path)
    required = ('source_revision', 'catalog_version', 'catalog_sha256')
    missing = [field for field in required if not isinstance(manifest.get(field), str) or not manifest[field]]
    if missing:
        raise ValueError(f'manifest missing provenance: {", ".join(missing)}')
    if parity.get('valid') is not True:
        raise ValueError('parity result must be valid before evidence is recorded')
    return {
        'schema_version': 1,
        'recorded_at': timestamp or datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'source_revision': manifest['source_revision'],
        'catalog_version': manifest['catalog_version'],
        'catalog_sha256': manifest['catalog_sha256'],
        'export_manifest_sha256': digest(manifest_path),
        'parity_valid': True,
        'verifier_version': verifier_version,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--parity-result', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--verifier-version', required=True)
    parser.add_argument('--timestamp')
    args = parser.parse_args()
    try:
        record = build_record(args.manifest, args.parity_result, args.verifier_version, args.timestamp)
        destination = args.evidence_dir.expanduser().resolve() / 'release-evidence.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f'ERROR: {error}')
        return 1
    print(json.dumps({'record': str(destination), 'sha256': digest(destination)}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
