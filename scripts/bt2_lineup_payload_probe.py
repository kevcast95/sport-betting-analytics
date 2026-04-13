#!/usr/bin/env python3
"""
§4.1 + §4.2 — AUDITORIA_RAW_SPORTMONKS: conteos tipo ILIKE + probe recursivo → out/lineup_probe_paths.json

§4.1: Por defecto **muestra aleatoria** (subcadena en `json.dumps(payload)`), equivalente a ILIKE sobre
`payload::text` por fila. El ILIKE global `WHERE payload::text ILIKE` sobre ~55k JSON muy grandes puede
tardar horas (seq scan repetido); para conteos exactos usar las 5 sentencias del runbook en batch nocturno
o `RUN_EXACT_ILIKE=1` (misma lentitud).

§4.2: 10 fixture_id mixtos + walk recursivo (keys/strings cortas).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
OUT_JSON = REPO / "out" / "lineup_probe_paths.json"

KEY_PAT = re.compile(
    r"lineup|formation|squad|sidelined|injur|missing|suspension",
    re.I,
)


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


def _snippet(val: Any, max_len: int = 200) -> str:
    s = json.dumps(val, ensure_ascii=False, default=str)
    if len(s) > max_len:
        return s[:max_len] + "…"
    return s


def _walk(
    obj: Any,
    path: str,
    hits: list[dict[str, Any]],
    *,
    max_hits_per_fixture: int = 500,
) -> None:
    if len(hits) >= max_hits_per_fixture:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if KEY_PAT.search(str(k)):
                hits.append(
                    {
                        "path": f"{path}.{k}" if path else k,
                        "match": "key",
                        "value_type": type(v).__name__,
                        "snippet": _snippet(v, 240),
                    }
                )
            if isinstance(v, str) and len(v) < 500 and KEY_PAT.search(v):
                hits.append(
                    {
                        "path": f"{path}.{k}" if path else k,
                        "match": "string_value",
                        "value_type": "str",
                        "snippet": _snippet(v, 240),
                    }
                )
            child_path = f"{path}.{k}" if path else k
            _walk(v, child_path, hits, max_hits_per_fixture=max_hits_per_fixture)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if len(hits) >= max_hits_per_fixture:
                return
            _walk(item, f"{path}[{i}]", hits, max_hits_per_fixture=max_hits_per_fixture)


def main() -> None:
    import psycopg2
    import psycopg2.extras

    url = _sync_dsn(_load_bt2_database_url())
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout TO 0")

    cur.execute("SELECT COUNT(*) AS c FROM raw_sportmonks_fixtures")
    table_total = int(cur.fetchone()["c"])

    queries = [
        ("lineup", "%lineup%"),
        ("formation", "%formation%"),
        ("sidelined", "%sidelined%"),
        ("injur", "%injur%"),
        ("missing", "%missing%"),
    ]
    counts: dict[str, int] = {}
    method_note = ""

    if os.environ.get("RUN_EXACT_ILIKE", "").strip() in ("1", "true", "yes"):
        method_note = "exact_postgres_ilike_full_table"
        for label, pat in queries:
            print(f"… ILIKE global {label} (lento)", flush=True)
            cur.execute(
                "SELECT COUNT(*) AS c FROM raw_sportmonks_fixtures WHERE payload::text ILIKE %s",
                (pat,),
            )
            counts[label] = int(cur.fetchone()["c"])
    else:
        method_note = "random_sample_json_dumps_equivalent_to_ilike_per_row"
        sample_n = int(os.environ.get("LINEUP_AUDIT_SAMPLE_N", "250"))
        print(f"… §4.1 muestra aleatoria n={sample_n} (equiv. ILIKE por fila; proyección al corpus)", flush=True)
        cur.execute(
            """
            SELECT payload FROM raw_sportmonks_fixtures
            WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
            ORDER BY random()
            LIMIT %s;
            """,
            (sample_n,),
        )
        sample_rows = cur.fetchall()
        counts = {k: 0 for k, _ in queries}
        max_bytes = int(os.environ.get("LINEUP_AUDIT_MAX_JSON_BYTES", str(6 * 1024 * 1024)))
        for row in sample_rows:
            payload = row["payload"]
            raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
            if len(raw) > max_bytes:
                raw = raw[:max_bytes]
            t = raw.lower()
            if "lineup" in t:
                counts["lineup"] += 1
            if "formation" in t:
                counts["formation"] += 1
            if "sidelined" in t:
                counts["sidelined"] += 1
            if "injur" in t:
                counts["injur"] += 1
            if "missing" in t:
                counts["missing"] += 1
        sample_len = len(sample_rows)
        projected = {
            k: round(table_total * counts[k] / sample_len) if sample_len else 0 for k in counts
        }
    print("## §4.1 — Conteos subcadena (runbook lineup / formation / sidelined / injur / missing)\n")
    if method_note == "exact_postgres_ilike_full_table":
        print("| patrón | filas (ILIKE global) |")
        print("|--------|----------------------|")
        for label, pat in queries:
            print(f"| `{pat}` ({label}) | {counts[label]} |")
    else:
        print(f"Metodo: muestra aleatoria **n={sample_len}** / **{table_total}** filas; texto JSON truncado a {max_bytes} B/fila si aplica.\n")
        print("| patrón | hits en muestra | proyección ~corpus |")
        print("|--------|-----------------|--------------------|")
        for label, pat in queries:
            print(f"| `{pat}` ({label}) | {counts[label]} | {projected[label]} |")
        print("\n*Proyección = round(total × hits/n). Para **conteos exactos** ejecutar en Postgres las 5 sentencias del runbook o `RUN_EXACT_ILIKE=1`.*")

    # 10 fixture_id: 3 sin result_info, 3 con result_info, 4 random (únicos)
    cur.execute(
        """
        SELECT fixture_id FROM raw_sportmonks_fixtures
        WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
          AND (payload->>'result_info' IS NULL OR btrim(payload->>'result_info') = '')
        ORDER BY fetched_at DESC
        LIMIT 3;
        """
    )
    upcoming = [int(r["fixture_id"]) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT fixture_id FROM raw_sportmonks_fixtures
        WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
          AND payload->>'result_info' IS NOT NULL AND length(btrim(payload->>'result_info')) > 0
        ORDER BY fetched_at DESC
        LIMIT 3;
        """
    )
    finished = [int(r["fixture_id"]) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT fixture_id FROM raw_sportmonks_fixtures
        WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
        ORDER BY random()
        LIMIT 12;
        """
    )
    rnd = [int(r["fixture_id"]) for r in cur.fetchall()]

    seen: set[int] = set()
    fixture_ids: list[int] = []
    for fid in upcoming[:3]:
        if fid not in seen:
            seen.add(fid)
            fixture_ids.append(fid)
    for fid in finished[:3]:
        if fid not in seen:
            seen.add(fid)
            fixture_ids.append(fid)
    for fid in rnd:
        if len(fixture_ids) >= 10:
            break
        if fid not in seen:
            seen.add(fid)
            fixture_ids.append(fid)

    out_rows: list[dict[str, Any]] = []
    meta_fixture: list[dict[str, Any]] = []

    for fid in fixture_ids[:10]:
        cur.execute(
            """
            SELECT fixture_id, fixture_date, fetched_at, payload,
                   payload->>'result_info' AS result_info_preview
            FROM raw_sportmonks_fixtures
            WHERE fixture_id = %s
            """,
            (fid,),
        )
        row = cur.fetchone()
        if not row:
            continue
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        hits: list[dict[str, Any]] = []
        _walk(payload, "", hits)
        meta_fixture.append(
            {
                "fixture_id": fid,
                "bucket_hint": "upcoming"
                if fid in upcoming
                else "finished"
                if fid in finished
                else "random",
                "fixture_date": str(row["fixture_date"]) if row["fixture_date"] else None,
                "has_nonempty_result_info": bool(
                    row.get("result_info_preview") and str(row["result_info_preview"]).strip()
                ),
                "hit_count": len(hits),
            }
        )
        for h in hits:
            out_rows.append(
                {
                    "fixture_id": fid,
                    "path": h["path"],
                    "match": h["match"],
                    "value_type": h["value_type"],
                    "snippet": h["snippet"],
                }
            )

    cur.close()
    conn.close()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    if method_note == "exact_postgres_ilike_full_table":
        doc_counts: dict[str, Any] = {"mode": "exact_ilike", "per_label_row_count": counts}
    else:
        doc_counts = {
            "mode": "random_sample",
            "table_total_rows": table_total,
            "sample_n": len(sample_rows),
            "max_json_bytes_per_row": max_bytes,
            "hits_in_sample": counts,
            "projected_row_hits": projected,
            "runbook_exact_sql": [
                "SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%lineup%';",
                "SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%formation%';",
                "SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%sidelined%';",
                "SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%injur%';",
                "SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%missing%';",
            ],
        }
    doc = {
        "section_4_1": doc_counts,
        "fixture_sample_meta": meta_fixture,
        "paths": out_rows,
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nEscrito: {OUT_JSON.relative_to(REPO)} ({len(out_rows)} filas path)")


if __name__ == "__main__":
    main()
