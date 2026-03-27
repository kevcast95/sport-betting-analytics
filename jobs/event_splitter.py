#!/usr/bin/env python3
"""
event_splitter.py

Filtra la salida de `select_candidates` (JSON con `ds_input`) por **ventana de kickoff en hora local**.
La lógica de franjas vive aquí (determinista), no en el LLM / OC.

Entrada: JSON completo de select_candidates (-o candidates.json).
Salida: mismo esquema reducido a eventos cuyo start_timestamp cae en [inicio, fin) del día --date en --timezone.

Slots predefinidos (2 ventanas al día, alineadas a cron 05:00 y 13:00 CO):
  --slot morning   → kickoff local [06:00, 14:00) en --date
  --slot afternoon → kickoff local [14:00, 24:00) en --date
  --slot full_day  → todo el día calendario --date en --timezone (sin franjas)

Uso típico tras select_candidates (convención out/ — ver openclaw/NAMING_ARTIFACTS.md):
  python3 jobs/event_splitter.py -i out/candidates_2026-03-22_select.json \\
    -o out/candidates_2026-03-22_exec_08h.json \\
    --date 2026-03-22 --slot morning --timezone America/Bogota
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo


def _parse_hhmm(s: str) -> time:
    parts = s.strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return time(h, m, 0)


def _kickoff_local(
    event_context: Dict[str, Any], tz: ZoneInfo
) -> Optional[datetime]:
    raw = event_context.get("start_timestamp")
    if raw is None:
        return None
    try:
        ts = int(raw)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, tz=tz)


def _window_for_slot(
    slot: str,
) -> Tuple[str, time, Optional[time], bool]:
    """(label, t_start, t_end exclusive o None, open_ended_after_start)"""
    s = slot.lower().strip()
    if s in ("1", "morning", "am", "m"):
        return ("[06:00, 14:00)", time(6, 0), time(14, 0), False)
    if s in ("2", "afternoon", "pm", "p", "tarde"):
        return ("[14:00, 24:00)", time(14, 0), None, True)
    if s in ("full_day", "fullday", "full", "all", "day", "dia", "día"):
        # Mismo día local: [00:00, 24:00) vía open_ended desde medianoche.
        return ("[00:00, 24:00) día completo", time(0, 0), None, True)
    raise ValueError(
        f"slot desconocido: {slot!r}; use morning|afternoon|full_day o 1|2"
    )


def _in_window(
    kickoff: datetime,
    day: date,
    t_start: time,
    t_end: Optional[time],
    open_ended: bool,
) -> bool:
    if kickoff.date() != day:
        return False
    tt = kickoff.timetz().replace(tzinfo=None) if kickoff.tzinfo else kickoff.time()
    if open_ended:
        return tt >= t_start
    assert t_end is not None
    return t_start <= tt < t_end


def _custom_window(t_start: time, t_end: time) -> str:
    return f"[{_fmt_t(t_start)}, {_fmt_t(t_end)})"


def _fmt_t(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Filtra ds_input por ventana de kickoff (hora local).")
    p.add_argument("--input", "-i", required=True, help="JSON salida de select_candidates")
    p.add_argument("--output", "-o", type=str, default=None, help="Salida (default: stdout)")
    p.add_argument("--date", required=True, help="Día calendario del kickoff (YYYY-MM-DD), TZ ref")
    p.add_argument(
        "--timezone",
        default="America/Bogota",
        help="Zona horaria para interpretar kickoff (default: America/Bogota)",
    )
    p.add_argument(
        "--slot",
        type=str,
        default=None,
        help="morning | afternoon | full_day (día completo, análisis sin franjas)",
    )
    p.add_argument("--local-start", type=str, default=None, help="HH:MM inicio (con --local-end)")
    p.add_argument("--local-end", type=str, default=None, help="HH:MM fin exclusivo (con --local-start)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tz = ZoneInfo(args.timezone)
    day = date.fromisoformat(args.date)

    open_ended = False
    if args.local_start and args.local_end:
        label = _custom_window(_parse_hhmm(args.local_start), _parse_hhmm(args.local_end))
        t_start, t_end = _parse_hhmm(args.local_start), _parse_hhmm(args.local_end)
    elif args.slot:
        label, t_start, t_end, open_ended = _window_for_slot(args.slot)
    else:
        print("Error: usa --slot o --local-start y --local-end juntos", file=sys.stderr)
        sys.exit(2)

    with open(args.input, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    ds_in: List[Dict[str, Any]] = list(data.get("ds_input") or [])
    kept: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for item in ds_in:
        ec = item.get("event_context") or {}
        ko = _kickoff_local(ec, tz)
        if ko is None:
            skipped.append({"event_id": item.get("event_id"), "reason": "no_start_timestamp"})
            continue
        if _in_window(ko, day, t_start, t_end, open_ended):
            kept.append(item)
        else:
            skipped.append(
                {
                    "event_id": item.get("event_id"),
                    "reason": "outside_window",
                    "kickoff_local": ko.isoformat(),
                }
            )

    out = dict(data)
    out["ds_input"] = kept
    out["event_splitter"] = {
        "job": "event_splitter",
        "date_local": args.date,
        "timezone": args.timezone,
        "window_label": label,
        "slot": args.slot or f"{args.local_start}-{args.local_end}",
        "input_ds_input_count": len(ds_in),
        "output_ds_input_count": len(kept),
        "skipped": skipped,
    }
    if "selected" in out:
        out["selected"] = [x["event_id"] for x in kept]
    if "candidates_detail" in out:
        kid = {x["event_id"] for x in kept}
        out["candidates_detail"] = [c for c in (out.get("candidates_detail") or []) if c.get("event_id") in kid]
    if "run_inventory" in out:
        kid = {x["event_id"] for x in kept}
        out["run_inventory"] = [r for r in (out.get("run_inventory") or []) if r.get("event_id") in kid]

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"OK written to {args.output} ({len(kept)} eventos en ventana)", file=sys.stderr)
    else:
        sys.stdout.write(text)

    print(
        json.dumps(
            {
                "job": "event_splitter",
                "kept": len(kept),
                "skipped": len(skipped),
                "window": label,
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
