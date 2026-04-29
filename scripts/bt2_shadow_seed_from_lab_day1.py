#!/usr/bin/env python3
"""
Seed mínimo del carril shadow usando artefactos del laboratorio day1.

Puebla:
- bt2_shadow_runs
- bt2_shadow_provider_snapshots
- bt2_shadow_daily_picks
- bt2_shadow_pick_inputs
- bt2_shadow_pick_eval
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "scripts" / "outputs" / "bt2_vendor_lab_day1"


def _dsn() -> str:
    env = os.getenv("BT2_DATABASE_URL", "").strip().replace("postgresql+asyncpg://", "postgresql://")
    if env:
        return env
    dot = ROOT / ".env"
    if dot.is_file():
        with dot.open(encoding="utf-8") as f:
            for ln in f:
                if ln.strip().startswith("BT2_DATABASE_URL="):
                    v = ln.split("=", 1)[1].strip().strip('"').strip("'")
                    return v.replace("postgresql+asyncpg://", "postgresql://")
    raise SystemExit("Falta BT2_DATABASE_URL en entorno o .env")


def _read_csv(p: Path) -> list[dict[str, str]]:
    if not p.is_file():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _parse_ts(v: str | None) -> Optional[datetime]:
    s = (v or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _norm_team(s: str) -> str:
    t = unicodedata.normalize("NFKD", (s or "").strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[\.\'`´]", "", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for tok in (" fc", " cf", " sc", " afc", " fk", " ac"):
        if t.endswith(tok):
            t = t[: -len(tok)].strip()
    return t


def _canon_team(s: str) -> str:
    aliases = {
        "afc bournemouth": "bournemouth",
        "bayer 04 leverkusen": "bayer leverkusen",
        "losc lille": "lille",
        "celta de vigo": "celta vigo",
        "deportivo alaves": "alaves",
    }
    n = _norm_team(s)
    return aliases.get(n, n)


def _normalize_selection_for_h2h(selection: str | None, home_name: str, away_name: str) -> str | None:
    s_raw = (selection or "").strip()
    if not s_raw:
        return None
    s = _canon_team(s_raw)
    if s in {"draw", "empate", "x"}:
        return "draw"
    home = _canon_team(home_name)
    away = _canon_team(away_name)
    if home and (s == home or home in s or s in home):
        return home_name
    if away and (s == away or away in s or s in away):
        return away_name
    return s_raw


@dataclass
class Counts:
    runs: int = 0
    snapshots: int = 0
    picks: int = 0
    inputs: int = 0
    evals: int = 0


def _extract_decimal_and_selection(summary: str) -> tuple[Optional[float], Optional[str]]:
    s = (summary or "").strip()
    if not s:
        return None, None
    first = s.split(";")[0].strip()
    if ":" not in first:
        return None, None
    sel, dec = first.split(":", 1)
    return _safe_float(dec.strip()), (sel.strip() or None)


def seed_once(cur: Any, *, run_key: str) -> Counts:
    manifest = _read_csv(LAB_DIR / "day1_lab_manifest.csv")
    matching = _read_csv(LAB_DIR / "toa_event_matching_results.csv")
    odds = _read_csv(LAB_DIR / "toa_h2h_t60_results.csv")
    compare = _read_csv(LAB_DIR / "bt2_vs_toa_exploration.csv")
    credit_json = {}
    try:
        credit_json = json.loads((LAB_DIR / "toa_credit_usage_summary.json").read_text(encoding="utf-8"))
    except Exception:
        credit_json = {}

    if not manifest:
        raise SystemExit("No existe day1_lab_manifest.csv para poblar shadow.")

    match_by_fixture = {str(r.get("sm_fixture_id", "")): r for r in matching}
    odds_by_fixture = {str(r.get("sm_fixture_id", "")): r for r in odds}
    cmp_by_fixture = {str(r.get("sm_fixture_id", "")): r for r in compare}
    calls = credit_json.get("calls") or []
    credits_by_fixture: dict[str, float] = {}
    for c in calls:
        fid = str(c.get("fixture") or "").strip()
        if not fid:
            continue
        credits_by_fixture[fid] = credits_by_fixture.get(fid, 0.0) + (_safe_float(c.get("x-requests-last")) or 0.0)

    dkeys = []
    for m in manifest:
        kickoff = str(m.get("kickoff_utc") or "")
        if len(kickoff) >= 10:
            dkeys.append(kickoff[:10])
    d_from = min(dkeys) if dkeys else datetime.now(timezone.utc).date().isoformat()
    d_to = max(dkeys) if dkeys else d_from

    cur.execute(
        """
        INSERT INTO bt2_shadow_runs (
            run_key, operating_day_key_from, operating_day_key_to,
            mode, provider_stack, is_shadow, notes
        )
        VALUES (%s,%s,%s,'shadow','sportmonks_fixture_master + theoddsapi_historical_h2h_t60',true,%s)
        RETURNING id
        """,
        (run_key, d_from, d_to, "seeded_from_lab_day1"),
    )
    run_id = int(cur.fetchone()["id"])
    out = Counts(runs=1)

    for m in manifest:
        fid = str(m.get("sm_fixture_id") or "").strip()
        if not fid:
            continue
        od = odds_by_fixture.get(fid, {})
        mt = match_by_fixture.get(fid, {})
        cm = cmp_by_fixture.get(fid, {})
        cls = str(od.get("classification") or mt.get("classification") or "request_error")
        dec, sel = _extract_decimal_and_selection(str(od.get("outcomes_decimal_summary") or ""))
        sel = _normalize_selection_for_h2h(sel, str(m.get("home_team_sm") or ""), str(m.get("away_team_sm") or ""))
        provider_snapshot_time = _parse_ts(od.get("provider_snapshot_time"))
        provider_last_update = _parse_ts(od.get("provider_last_update"))
        ingested_at = _parse_ts(od.get("ingested_at")) or datetime.now(timezone.utc)
        bt2_event_id = int(m.get("bt2_event_id") or 0) or None
        sm_fixture_id = int(fid)
        sm_league_id = int(m.get("sm_league_id") or 0) or None
        if sm_league_id is not None:
            cur.execute("SELECT id FROM bt2_leagues WHERE sportmonks_id = %s", (sm_league_id,))
            lr = cur.fetchone()
            league_id = int(lr["id"]) if lr else None
        else:
            league_id = None

        payload = {
            "snapshot_time_t60": m.get("snapshot_time_t60"),
            "toa_event_id": mt.get("toa_event_id"),
            "match_notes": mt.get("match_notes"),
            "value_pool_pass": cm.get("value_pool_recomputed_sm_lbu_t60"),
            "payload_summary": od.get("payload_summary"),
            "request_url": od.get("request_url"),
            "http_status": od.get("http_status"),
        }
        cur.execute(
            """
            INSERT INTO bt2_shadow_provider_snapshots (
                run_id, bt2_event_id, sm_fixture_id, provider_source, sport_key, market, region,
                provider_snapshot_time, provider_last_update, ingested_at, credits_used, raw_payload
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                run_id,
                bt2_event_id,
                sm_fixture_id,
                "the_odds_api_historical_h2h",
                m.get("the_odds_api_sport_key_expected"),
                m.get("market") or "h2h",
                m.get("region") or "us",
                provider_snapshot_time,
                provider_last_update,
                ingested_at,
                credits_by_fixture.get(fid, 0.0),
                psycopg2.extras.Json(payload),
            ),
        )
        provider_snapshot_id = int(cur.fetchone()["id"])
        out.snapshots += 1

        kickoff = str(m.get("kickoff_utc") or "")
        day_key = kickoff[:10] if len(kickoff) >= 10 else d_from
        status_shadow = "ready_for_shadow_pick" if cls == "matched_with_odds_t60" else "needs_review"
        cur.execute(
            """
            INSERT INTO bt2_shadow_daily_picks (
                run_id, operating_day_key, bt2_event_id, sm_fixture_id, league_id,
                market, selection, status_shadow, classification_taxonomy, decimal_odds,
                dsr_source, provider_snapshot_id
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                run_id,
                day_key,
                bt2_event_id,
                sm_fixture_id,
                league_id,
                m.get("market") or "h2h",
                sel,
                status_shadow,
                cls,
                dec,
                "historical_sm_lbu_t60",
                provider_snapshot_id,
            ),
        )
        shadow_pick_id = int(cur.fetchone()["id"])
        out.picks += 1

        input_payload = {
            "manifest_row": m,
            "matching_row": mt,
            "odds_row": {k: v for k, v in od.items() if k != "payload_summary"},
            "compare_row": cm,
        }
        cur.execute(
            """
            INSERT INTO bt2_shadow_pick_inputs (shadow_daily_pick_id, input_source, payload_json)
            VALUES (%s,%s,%s)
            """,
            (shadow_pick_id, "lab_day1_artifacts", psycopg2.extras.Json(input_payload)),
        )
        out.inputs += 1

        eval_status = "shadow_pass" if cls == "matched_with_odds_t60" else "shadow_needs_review"
        cur.execute(
            """
            INSERT INTO bt2_shadow_pick_eval (shadow_daily_pick_id, eval_status, classification_taxonomy, eval_notes)
            VALUES (%s,%s,%s,%s)
            """,
            (shadow_pick_id, eval_status, cls, "seed_day1_initial"),
        )
        out.evals += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed shadow tables desde lab day1")
    ap.add_argument("--run-key", default=f"shadow-seed-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    args = ap.parse_args()

    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        c = seed_once(cur, run_key=args.run_key)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    print(
        json.dumps(
            {
                "run_key": args.run_key,
                "rows": {
                    "bt2_shadow_runs": c.runs,
                    "bt2_shadow_provider_snapshots": c.snapshots,
                    "bt2_shadow_daily_picks": c.picks,
                    "bt2_shadow_pick_inputs": c.inputs,
                    "bt2_shadow_pick_eval": c.evals,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

