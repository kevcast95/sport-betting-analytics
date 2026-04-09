#!/usr/bin/env python3
"""
T-159 (US-BE-026) — Job programado para cron: envuelve fetch_upcoming con exit codes.

Exit codes:
  0 — ejecución completa y descarga API OK
  1 — error fatal (excepción, API key faltante, etc.)
  2 — descarga API falló (ver logs); la corrida puede haber procesado 0 fixtures
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from scripts.bt2_cdm.fetch_upcoming import run_fetch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Job cron fetch_upcoming BT2 (Sprint 06)")
    parser.add_argument("--hours-ahead", type=int, default=48)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = run_fetch(hours_ahead=args.hours_ahead, dry_run=args.dry_run)
    except Exception as exc:
        print(f"[job_fetch_upcoming] FATAL: {exc}", file=sys.stderr)
        return 1
    if not result.get("download_ok", True):
        print("[job_fetch_upcoming] WARN: descarga Sportmonks falló (ver logs).", file=sys.stderr)
        return 2
    print(f"[job_fetch_upcoming] OK: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
