#!/usr/bin/env python3
"""
Evaluacion oficial de performance para picks del carril shadow.

No toca tablas productivas; escribe solo en `bt2_shadow_pick_eval`.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_settings import bt2_settings

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_performance"


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _norm(s: str) -> str:
    x = unicodedata.normalize("NFKD", (s or "").strip())
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"[^a-zA-Z0-9]+", " ", x).strip().lower()
    return re.sub(r"\s+", " ", x)


def _canon_team(s: str) -> str:
    aliases = {
        "afc bournemouth": "bournemouth",
        "bayer 04 leverkusen": "bayer leverkusen",
        "losc lille": "lille",
        "celta de vigo": "celta vigo",
        "deportivo alaves": "alaves",
        "olympique lyonnais": "lyon",
    }
    n = _norm(s)
    return aliases.get(n, n)


def _token_set(s: str) -> set[str]:
    stop = {"fc", "cf", "sc", "club", "de", "la", "the", "cd", "ud", "afc"}
    return {x for x in _canon_team(s).split() if x and x not in stop}


def _is_void_status(status: str) -> bool:
    s = _norm(status)
    return s in {
        "abandoned",
        "cancelled",
        "canceled",
        "postponed",
        "suspended",
        "interrupted",
        "deleted",
        "walkover",
    }


def _selection_side(selection: str, home: str, away: str) -> str | None:
    s = _canon_team(selection)
    if not s:
        return None
    if s in {"draw", "empate", "x"}:
        return "draw"
    if s in {"home", "local", "1"}:
        return "home"
    if s in {"away", "visitante", "2"}:
        return "away"
    hs = _canon_team(home)
    as_ = _canon_team(away)
    if hs and (hs in s or s in hs):
        return "home"
    if as_ and (as_ in s or s in as_):
        return "away"
    st = _token_set(selection)
    ht = _token_set(home)
    at = _token_set(away)
    if st and ht and len(st & ht) >= 1:
        return "home"
    if st and at and len(st & at) >= 1:
        return "away"
    return None


def _parse_sm_truth(payload: dict[str, Any]) -> tuple[str | None, int | None, int | None, str, str, bool]:
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    event_status = str(state.get("state") or state.get("name") or state.get("short_name") or "")
    participants = payload.get("participants") if isinstance(payload.get("participants"), list) else []
    p_home: int | None = None
    p_away: int | None = None
    home_name = ""
    away_name = ""
    for p in participants:
        if not isinstance(p, dict):
            continue
        pid = int(p.get("id") or 0) or None
        loc = str((p.get("meta") or {}).get("location") or "").lower()
        if loc == "home":
            p_home = pid
            home_name = str(p.get("name") or "")
        elif loc == "away":
            p_away = pid
            away_name = str(p.get("name") or "")
    scores = payload.get("scores") if isinstance(payload.get("scores"), list) else []
    best_rank = -1
    out_home: int | None = None
    out_away: int | None = None
    for s in scores:
        if not isinstance(s, dict):
            continue
        desc = _norm(str(s.get("description") or s.get("type") or ""))
        rank = 3 if desc in {"current", "fulltime", "ft"} else 2 if "2nd" in desc else 1 if "1st" in desc else 0
        pid = int(s.get("participant_id") or 0) or None
        score_node = s.get("score")
        val = None
        if isinstance(score_node, dict):
            raw = score_node.get("goals") if score_node.get("goals") is not None else score_node.get("participant")
            if raw is None:
                raw = score_node.get("score")
            try:
                val = int(raw) if raw is not None else None
            except (TypeError, ValueError):
                val = None
        if val is None:
            try:
                val = int(s.get("score")) if s.get("score") is not None else None
            except (TypeError, ValueError):
                val = None
        if val is None:
            continue
        if pid == p_home and rank >= best_rank:
            out_home = val
            best_rank = rank
        elif pid == p_away and rank >= best_rank:
            out_away = val
            best_rank = rank
    has_score = out_home is not None and out_away is not None
    return event_status or None, out_home, out_away, home_name, away_name, has_score


def _fetch_sm_truth_map(fixture_ids: set[int]) -> dict[int, dict[str, Any]]:
    api = (bt2_settings.sportmonks_api_key or "").strip()
    if not api or not fixture_ids:
        return {}
    out: dict[int, dict[str, Any]] = {}
    with httpx.Client(timeout=25) as client:
        for fid in sorted(fixture_ids):
            try:
                r = client.get(
                    f"https://api.sportmonks.com/v3/football/fixtures/{fid}",
                    params={"api_token": api, "include": "participants;scores;state"},
                )
            except Exception:
                continue
            if r.status_code != 200:
                continue
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            data = body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), dict) else {}
            if not data:
                continue
            st, rh, ra, hn, an, ok = _parse_sm_truth(data)
            if ok:
                out[fid] = {
                    "event_status": st,
                    "result_home": rh,
                    "result_away": ra,
                    "home_name": hn,
                    "away_name": an,
                }
    return out


@dataclass
class EvalRow:
    shadow_daily_pick_id: int
    run_key: str
    selection: str
    decimal_odds: float | None
    home_name: str
    away_name: str
    event_status: str | None
    result_home: int | None
    result_away: int | None
    sm_fixture_id: int | None


def _evaluate_one(r: EvalRow) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if _is_void_status(r.event_status or ""):
        return {
            "eval_status": "void",
            "evaluation_reason": f"event_status_void:{r.event_status or 'unknown'}",
            "evaluated_at": now,
            "truth_source": "bt2_events_cdm_v1",
            "result_home": r.result_home,
            "result_away": r.result_away,
            "event_status": r.event_status,
            "decimal_odds": r.decimal_odds,
            "roi_flat_stake_units": None,
        }
    if r.result_home is None or r.result_away is None:
        return {
            "eval_status": "pending_result",
            "evaluation_reason": "missing_final_score",
            "evaluated_at": now,
            "truth_source": "bt2_events_cdm_v1",
            "result_home": r.result_home,
            "result_away": r.result_away,
            "event_status": r.event_status,
            "decimal_odds": r.decimal_odds,
            "roi_flat_stake_units": None,
        }
    side = _selection_side(r.selection, r.home_name, r.away_name)
    if side is None:
        return {
            "eval_status": "no_evaluable",
            "evaluation_reason": "selection_not_mappable_h2h",
            "evaluated_at": now,
            "truth_source": "bt2_events_cdm_v1",
            "result_home": r.result_home,
            "result_away": r.result_away,
            "event_status": r.event_status,
            "decimal_odds": r.decimal_odds,
            "roi_flat_stake_units": None,
        }

    home_win = r.result_home > r.result_away
    away_win = r.result_away > r.result_home
    draw = r.result_home == r.result_away
    is_hit = (side == "home" and home_win) or (side == "away" and away_win) or (side == "draw" and draw)
    if is_hit:
        roi = (float(r.decimal_odds) - 1.0) if r.decimal_odds is not None else None
        return {
            "eval_status": "hit",
            "evaluation_reason": f"h2h_{side}_hit",
            "evaluated_at": now,
            "truth_source": "bt2_events_cdm_v1",
            "result_home": r.result_home,
            "result_away": r.result_away,
            "event_status": r.event_status,
            "decimal_odds": r.decimal_odds,
            "roi_flat_stake_units": roi,
        }
    return {
        "eval_status": "miss",
        "evaluation_reason": f"h2h_{side}_miss",
        "evaluated_at": now,
        "truth_source": "bt2_events_cdm_v1",
        "result_home": r.result_home,
        "result_away": r.result_away,
        "event_status": r.event_status,
        "decimal_odds": r.decimal_odds,
        "roi_flat_stake_units": -1.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Evalua performance de runs shadow ya persistidos")
    ap.add_argument(
        "--run-key",
        action="append",
        default=[],
        help="Run key a evaluar (repeatable). Default: backfill 2025-01-05 y recovery 2025-07-12.",
    )
    args = ap.parse_args()
    run_keys = args.run_key or [
        "shadow-subset5-backfill-2025-01-05",
        "shadow-subset5-recovery-2025-07-12",
    ]

    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    per_run: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "picks_total": 0,
            "scored": 0,
            "hit": 0,
            "miss": 0,
            "void": 0,
            "pending_result": 0,
            "no_evaluable": 0,
            "roi_flat_stake_units": 0.0,
            "hit_rate": 0.0,
            "roi_flat_stake_pct": 0.0,
        }
    )
    try:
        cur.execute(
            """
            SELECT
                dp.id AS shadow_daily_pick_id,
                r.run_key,
                COALESCE(dp.selection,'') AS selection,
                dp.decimal_odds,
                COALESCE(ht.name,'') AS home_name,
                COALESCE(at.name,'') AS away_name,
                ev.status AS event_status,
                ev.result_home,
                ev.result_away,
                dp.sm_fixture_id,
                COALESCE(dp.classification_taxonomy,'') AS classification_taxonomy
            FROM bt2_shadow_daily_picks dp
            INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
            LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
            LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
            LEFT JOIN bt2_teams at ON at.id = ev.away_team_id
            WHERE r.run_key = ANY(%s)
            ORDER BY r.run_key, dp.id
            """,
            (run_keys,),
        )
        rows = cur.fetchall() or []
        sm_truth_map = _fetch_sm_truth_map(
            {
                int(rr["sm_fixture_id"])
                for rr in rows
                if rr.get("sm_fixture_id") is not None and (rr.get("result_home") is None or rr.get("result_away") is None)
            }
        )
        for rr in rows:
            sm_fixture_id = int(rr["sm_fixture_id"]) if rr.get("sm_fixture_id") is not None else None
            fallback = sm_truth_map.get(sm_fixture_id or -1)
            event_status = str(rr.get("event_status") or "")
            result_home = int(rr["result_home"]) if rr.get("result_home") is not None else None
            result_away = int(rr["result_away"]) if rr.get("result_away") is not None else None
            home_name = str(rr.get("home_name") or "")
            away_name = str(rr.get("away_name") or "")
            truth_source = "bt2_events_cdm_v1"
            if fallback and (result_home is None or result_away is None):
                result_home = int(fallback["result_home"]) if fallback.get("result_home") is not None else result_home
                result_away = int(fallback["result_away"]) if fallback.get("result_away") is not None else result_away
                if fallback.get("event_status"):
                    event_status = str(fallback.get("event_status") or event_status)
                if fallback.get("home_name"):
                    home_name = str(fallback["home_name"])
                if fallback.get("away_name"):
                    away_name = str(fallback["away_name"])
                truth_source = "sportmonks_fixture_api_v1"
            er = EvalRow(
                shadow_daily_pick_id=int(rr["shadow_daily_pick_id"]),
                run_key=str(rr["run_key"]),
                selection=str(rr.get("selection") or ""),
                decimal_odds=float(rr["decimal_odds"]) if rr.get("decimal_odds") is not None else None,
                home_name=home_name,
                away_name=away_name,
                event_status=event_status,
                result_home=result_home,
                result_away=result_away,
                sm_fixture_id=sm_fixture_id,
            )
            ev = _evaluate_one(er)
            ev["truth_source"] = truth_source
            cur.execute(
                """
                INSERT INTO bt2_shadow_pick_eval (
                    shadow_daily_pick_id, eval_status, classification_taxonomy, eval_notes,
                    evaluation_reason, evaluated_at, truth_source, result_home, result_away,
                    event_status, decimal_odds, roi_flat_stake_units
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (shadow_daily_pick_id) DO UPDATE SET
                    eval_status = EXCLUDED.eval_status,
                    classification_taxonomy = EXCLUDED.classification_taxonomy,
                    eval_notes = EXCLUDED.eval_notes,
                    evaluation_reason = EXCLUDED.evaluation_reason,
                    evaluated_at = EXCLUDED.evaluated_at,
                    truth_source = EXCLUDED.truth_source,
                    result_home = EXCLUDED.result_home,
                    result_away = EXCLUDED.result_away,
                    event_status = EXCLUDED.event_status,
                    decimal_odds = EXCLUDED.decimal_odds,
                    roi_flat_stake_units = EXCLUDED.roi_flat_stake_units
                """,
                (
                    er.shadow_daily_pick_id,
                    ev["eval_status"],
                    str(rr.get("classification_taxonomy") or ""),
                    "shadow_performance_eval_v1_h2h",
                    ev["evaluation_reason"],
                    ev["evaluated_at"],
                    ev["truth_source"],
                    ev["result_home"],
                    ev["result_away"],
                    ev["event_status"],
                    ev["decimal_odds"],
                    ev["roi_flat_stake_units"],
                ),
            )
            pr = per_run[er.run_key]
            pr["picks_total"] += 1
            pr[ev["eval_status"]] += 1
            if ev["eval_status"] in ("hit", "miss"):
                pr["scored"] += 1
            if ev["roi_flat_stake_units"] is not None:
                pr["roi_flat_stake_units"] += float(ev["roi_flat_stake_units"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    out_rows: list[dict[str, Any]] = []
    for rk in run_keys:
        pr = per_run[rk]
        scored = int(pr["scored"])
        hit = int(pr["hit"])
        pr["hit_rate"] = round(hit / scored, 6) if scored else 0.0
        pr["roi_flat_stake_pct"] = round((pr["roi_flat_stake_units"] / scored) * 100.0, 6) if scored else 0.0
        out_rows.append({"run_key": rk, **pr})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "shadow_eval_summary.json").write_text(
        json.dumps(
            {
                "runs_evaluated": run_keys,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "rows": out_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (OUT_DIR / "shadow_eval_by_run.csv").open("w", encoding="utf-8", newline="") as f:
        fn = [
            "run_key",
            "picks_total",
            "scored",
            "hit",
            "miss",
            "void",
            "pending_result",
            "no_evaluable",
            "hit_rate",
            "roi_flat_stake_units",
            "roi_flat_stake_pct",
        ]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k) for k in fn})
    (OUT_DIR / "README.md").write_text(
        """# BT2 Shadow Performance

Evaluacion oficial del carril shadow (no productivo) sobre picks persistidos.

## Estado evaluacion (`eval_status`)

- `hit`
- `miss`
- `void`
- `pending_result`
- `no_evaluable`

## Artefactos

- `shadow_eval_summary.json`
- `shadow_eval_by_run.csv`
""",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "out_dir": str(OUT_DIR.relative_to(ROOT)), "rows": out_rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
