#!/usr/bin/env python3
"""
merge_telegram_payload_parts.py

Junta varias piezas de `telegram_payload` (misma ventana / mismo día) en un solo JSON
para pasar a `render_telegram_payload.py`. Cada parte debe tener al menos la clave `events` (array).

Uso (tras analizar por lotes con el LLM):
  python3 jobs/merge_telegram_payload_parts.py \\
    -i out/payload_morning_part01.json out/payload_morning_part02.json \\
    -o out/telegram_payload.json

El `header` se toma del primer archivo; `pick_count` se recalcula. `db_1x2_line` se concatenan
con " | " si vienen en cada parte.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Une events[] de varios telegram_payload parciales.")
    p.add_argument("-i", "--input", nargs="+", required=True, help="JSON parciales (orden importa)")
    p.add_argument("-o", "--output", required=True, help="Salida unificada")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    all_events: List[Dict[str, Any]] = []
    header: Dict[str, Any] | None = None
    db_lines: List[str] = []

    for path in args.input:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            print(f"Error: {path} no es un objeto JSON.", file=sys.stderr)
            sys.exit(1)
        ev = d.get("events")
        if not isinstance(ev, list):
            print(f"Error: {path} sin 'events' array.", file=sys.stderr)
            sys.exit(1)
        all_events.extend(ev)
        if header is None and isinstance(d.get("header"), dict):
            header = dict(d["header"])
        db = d.get("db_1x2_line")
        if isinstance(db, str) and db.strip():
            db_lines.append(db.strip())

    if header is None:
        header = {"title": "Copa Foxkids", "date": "", "daily_run_id": None, "pick_count": 0}

    pick_count = sum(len(e.get("picks") or []) for e in all_events)
    header["pick_count"] = pick_count

    out: Dict[str, Any] = {
        "header": header,
        "events": all_events,
    }
    if db_lines:
        out["db_1x2_line"] = " | ".join(db_lines)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK merged {len(all_events)} events, {pick_count} picks -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
