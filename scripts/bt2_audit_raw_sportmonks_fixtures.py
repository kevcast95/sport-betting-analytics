#!/usr/bin/env python3
"""
Auditoría raw_sportmonks_fixtures (runbook BE_INSTRUCCION_AUDITORIA_RAW_FIXTURES.md).
Uso: desde la raíz del repo, con BT2_DATABASE_URL en el entorno o en .env
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[1]


def _load_bt2_database_url() -> str:
    url = (os.environ.get("BT2_DATABASE_URL") or "").strip().strip('"').strip("'")
    if url:
        return url
    env_path = REPO / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("BT2_DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        print("Falta BT2_DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    return url


def _sync_dsn(url: str) -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url, flags=re.I)


def _truncate_sample(obj: Any, max_chars: int = 4000) -> Any:
    raw = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    if len(raw) <= max_chars:
        return json.loads(raw) if isinstance(obj, (dict, list)) else obj
    return raw[:max_chars] + "\n… [truncado]"


def main() -> None:
    import psycopg2
    import psycopg2.extras

    url = _sync_dsn(_load_bt2_database_url())
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Tablas muy grandes: B puede tardar minutos (full scan + jsonb_object_keys).
    cur.execute("SET statement_timeout TO 0")

    def _serialize_row(d: dict[str, Any]) -> dict[str, Any]:
        out = dict(d)
        for k, v in list(out.items()):
            if hasattr(v, "isoformat"):
                out[k] = v.isoformat()
            elif v is not None and k.endswith("_date") and not isinstance(v, str):
                out[k] = str(v)
        return out

    # A (rápido) — imprimir ya
    cur.execute(
        """
        SELECT
          COUNT(*) AS total_rows,
          COUNT(DISTINCT fixture_id) AS distinct_fixture_ids,
          MIN(fixture_date) AS min_fixture_date,
          MAX(fixture_date) AS max_fixture_date,
          MAX(fetched_at) AS last_fetched_at
        FROM raw_sportmonks_fixtures;
        """
    )
    row_a = _serialize_row(dict(cur.fetchone()))
    print("=== QUERY_A_JSON ===", flush=True)
    print(json.dumps(row_a, ensure_ascii=False, separators=(",", ":")), flush=True)

    # D — imprimir ya
    cur.execute(
        """
        SELECT
          COUNT(*) AS bt2_events_total,
          COUNT(r.fixture_id) AS events_with_raw_row
        FROM bt2_events e
        LEFT JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id;
        """
    )
    row_d = dict(cur.fetchone())
    print("\n=== QUERY_D_JSON ===", flush=True)
    print(json.dumps(row_d, ensure_ascii=False, separators=(",", ":")), flush=True)

    # C: 2 últimos por fetched_at + 2 random (excluyendo esos fixture_id)
    cur.execute(
        """
        SELECT fixture_id, fixture_date, fetched_at, payload
        FROM raw_sportmonks_fixtures
        WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
        ORDER BY fetched_at DESC NULLS LAST
        LIMIT 2;
        """
    )
    recent = [dict(r) for r in cur.fetchall()]
    exclude = tuple(r["fixture_id"] for r in recent)
    if exclude:
        cur.execute(
            """
            SELECT fixture_id, fixture_date, fetched_at, payload
            FROM raw_sportmonks_fixtures
            WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
              AND fixture_id NOT IN %s
            ORDER BY random()
            LIMIT 2;
            """,
            (exclude,),
        )
    else:
        cur.execute(
            """
            SELECT fixture_id, fixture_date, fetched_at, payload
            FROM raw_sportmonks_fixtures
            WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
            ORDER BY random()
            LIMIT 2;
            """
        )
    rnd = [dict(r) for r in cur.fetchall()]
    samples = recent + rnd

    def summarize_row(r: dict[str, Any]) -> dict[str, Any]:
        payload = r["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        top_keys = list(payload.keys()) if isinstance(payload, dict) else []
        types_map = {}
        if isinstance(payload, dict):
            for k in top_keys:
                v = payload[k]
                if v is None:
                    types_map[k] = "null"
                elif isinstance(v, bool):
                    types_map[k] = "boolean"
                elif isinstance(v, int):
                    types_map[k] = "number"
                elif isinstance(v, float):
                    types_map[k] = "number"
                elif isinstance(v, str):
                    types_map[k] = "string"
                elif isinstance(v, list):
                    types_map[k] = "array"
                elif isinstance(v, dict):
                    types_map[k] = "object"
                else:
                    types_map[k] = type(v).__name__
        fd = r["fixture_date"]
        fa = r["fetched_at"]
        return {
            "fixture_id": r["fixture_id"],
            "fixture_date": fd.isoformat() if hasattr(fd, "isoformat") else str(fd) if fd is not None else None,
            "fetched_at": fa.isoformat() if hasattr(fa, "isoformat") else str(fa),
            "payload_top_level_keys": top_keys,
            "payload_json_types": types_map,
            "payload_sample_redacted": _truncate_sample(payload, max_chars=4000),
        }

    summaries_c = [summarize_row(r) for r in samples]
    print("\n=== QUERY_C_JSON_ARRAY ===", flush=True)
    print(json.dumps(summaries_c, ensure_ascii=False), flush=True)

    # B (solo objetos JSON) — al final; puede ser lento
    print("\n=== QUERY_B_running (puede tardar en tablas grandes) ===", flush=True)
    cur.execute(
        """
        SELECT
          key,
          COUNT(*) AS occurrences
        FROM raw_sportmonks_fixtures,
             LATERAL jsonb_object_keys(payload) AS key
        WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
        GROUP BY key
        ORDER BY occurrences DESC, key;
        """
    )
    keys_rows = [dict(r) for r in cur.fetchall()]

    out_dir = REPO / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "raw_sportmonks_payload_keys.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key", "occurrences"])
        w.writeheader()
        w.writerows(keys_rows)

    cur.close()
    conn.close()

    print(f"=== CSV_KEYS === {csv_path.relative_to(REPO)} filas={len(keys_rows)}", flush=True)
    print("\n=== TOP_40_KEYS ===", flush=True)
    for r in keys_rows[:40]:
        print(f"{r['key']}\t{r['occurrences']}", flush=True)
    if len(keys_rows) > 40:
        print(f"(... {len(keys_rows) - 40} keys más en CSV)", flush=True)


if __name__ == "__main__":
    main()
