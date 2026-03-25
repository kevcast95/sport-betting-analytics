#!/usr/bin/env python3
"""
split_ds_batches.py

Parte el JSON de select_candidates (o event_splitter) en **varios archivos** con menos
eventos en `ds_input` por archivo. Así cada llamada al LLM lleva menos tokens y evita
timeouts de 10 min con 15–20 eventos completos (processed + context).

Uso típico tras event_splitter:
  python3 jobs/split_ds_batches.py -i out/candidates_2026-03-22_exec_08h.json \\
    -o out/batches/candidates_2026-03-22_exec_08h --chunk-size 4 --slim

Salida: morning_2026-03-22_batch01of05.json, ...

--slim: quita run_inventory, rejected masivo, etc.; deja lo mínimo para análisis (ahorra tokens).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List


def _slim(data: Dict[str, Any]) -> Dict[str, Any]:
    """Copia ligera para enviar al modelo (sin inventario completo)."""
    keys = (
        "job",
        "daily_run_id",
        "sport",
        "captured_at_utc",
        "contract",
        "schedule_timezone",
        "ds_input_summary",
    )
    out: Dict[str, Any] = {k: data[k] for k in keys if k in data}
    out["job"] = "split_ds_batches_slim"
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Divide ds_input en lotes para el LLM.")
    p.add_argument("-i", "--input", required=True, help="JSON (select_candidates / event_splitter)")
    p.add_argument(
        "-o",
        "--output-prefix",
        required=True,
        help="Prefijo de salida (sin extensión); ej. out/batches/morning_2026-03-22",
    )
    p.add_argument("--chunk-size", type=int, default=4, help="Máx. eventos por archivo (default: 4)")
    p.add_argument(
        "--slim",
        action="store_true",
        help="Omite run_inventory y campos pesados; solo metadatos + ds_input del lote",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    chunk = max(1, int(args.chunk_size))

    with open(args.input, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    ds_in: List[Dict[str, Any]] = list(data.get("ds_input") or [])
    n = len(ds_in)
    if n == 0:
        print("ds_input vacío; no se generan lotes.", file=sys.stderr)
        sys.exit(1)

    total_batches = math.ceil(n / chunk)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    base_template = _slim(data) if args.slim else dict(data)
    if args.slim:
        for k in ("rejected", "rejection_reasons", "candidates_detail", "selected", "event_splitter"):
            base_template.pop(k, None)
    else:
        pass  # keep full copy per batch (heavy)

    written: List[str] = []
    for b in range(total_batches):
        slice_ = ds_in[b * chunk : (b + 1) * chunk]
        part = dict(base_template)
        part["ds_input"] = slice_
        if not args.slim:
            ids = {x["event_id"] for x in slice_}
            if "selected" in part:
                part["selected"] = [x["event_id"] for x in slice_]
            if "candidates_detail" in data:
                part["candidates_detail"] = [
                    c for c in (data.get("candidates_detail") or []) if c.get("event_id") in ids
                ]
            if "run_inventory" in data:
                part["run_inventory"] = [
                    r for r in (data.get("run_inventory") or []) if r.get("event_id") in ids
                ]
        part["split_batches"] = {
            "job": "split_ds_batches",
            "batch_index": b + 1,
            "batch_total": total_batches,
            "events_in_batch": len(slice_),
            "events_total": n,
            "chunk_size_requested": chunk,
            "slim": args.slim,
        }
        out_path = f"{args.output_prefix}_batch{b + 1:02d}of{total_batches:02d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(part, f, ensure_ascii=False, indent=2)
        written.append(out_path)

    print(
        json.dumps(
            {
                "job": "split_ds_batches",
                "input_events": n,
                "chunk_size": chunk,
                "batches": total_batches,
                "files": written,
                "slim": args.slim,
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
