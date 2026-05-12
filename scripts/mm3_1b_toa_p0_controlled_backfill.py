#!/usr/bin/env python3
"""
MM-3.1B — TOA P0 controlled backfill (Big 5, h2h+totals, eu, T-60).

- Solo lectura DB (SELECT). Sin escrituras. Sin DSR/SM.
- GET /v4/historical/sports/{sport}/odds (misma URL que MM-3.1A validada).
- Resume-safe vía checkpoint JSON.
- Stop: créditos, requests, remaining mínimo, errores repetidos, coste/request ≠ 20.

Salidas bajo scripts/outputs/mm3_1b_* y audit markdown.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "scripts" / "outputs"
CHECKPOINT_PATH = OUT_DIR / "mm3_1b_toa_p0_checkpoint.json"
RAW_PATH = OUT_DIR / "mm3_1b_toa_p0_raw.json"
COST_PATH = OUT_DIR / "mm3_1b_toa_p0_cost.json"
MATCH_CSV = OUT_DIR / "mm3_1b_toa_p0_match_rows.csv"
REJ_CSV = OUT_DIR / "mm3_1b_toa_p0_rejections.csv"
BOARD_JSON = OUT_DIR / "mm3_1b_toa_p0_market_board.json"
BOARD_CSV = OUT_DIR / "mm3_1b_toa_p0_market_board_rows.csv"
SUMMARY_PATH = OUT_DIR / "mm3_1b_summary.json"
AUDIT_PATH = REPO / "docs" / "bettracker2" / "audits" / "MM3_1B_TOA_P0_CONTROLLED_BACKFILL_AUDIT.md"

ALLOWED_SPORT_KEYS = frozenset(
    {
        "soccer_epl",
        "soccer_spain_la_liga",
        "soccer_italy_serie_a",
        "soccer_germany_bundesliga",
        "soccer_france_ligue_one",
    }
)

MAX_CREDITS_RUN = 60_000
MAX_REQUESTS_RUN = 3_000
MIN_REMAINING_ABORT = 35_000
CHECKPOINT_EVERY = 50
EXPECTED_CREDITS_PER_REQUEST = 20

REPO_FIX_CANDIDATES: list[dict[str, Any]] = [
    {
        "id": "TOA_HISTORICAL_ODDS_URL_MM31A",
        "affected_path": "scripts/bt2_atraco/theoddsapi_worker.py",
        "bug": "endpoint histórico TOA incorrecto",
        "wrong_endpoint": "GET /v4/historical/odds?sport=...",
        "correct_endpoint": "GET /v4/historical/sports/{sport}/odds",
        "evidence": "MM-3.1A: ruta antigua → HTML 404 sin headers de uso; ruta correcta → HTTP 200 + x-requests-last=20 (h2h+totals, eu).",
        "recommendation": "Fix en branch limpia separada; no mezclar con backfill/artifacts MM-3.1B.",
    }
]
CONSECUTIVE_ERROR_ABORT = 5
SAME_ERROR_REPEAT_ABORT = 8
ROLLING_WINDOW = 30
ROLLING_DEVIATION_MAX = 2.5


def _load_mm3_1a():
    p = REPO / "scripts" / "mm3_1a_toa_historical_sweep_cost_estimator.py"
    name = "mm3_1a_mod"
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _ensure_out() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h) for h in headers})


def _pair_key(sport: str, ts: str) -> str:
    return f"{sport}|{ts}"


def _parse_commence(x: str):
    try:
        from datetime import datetime as dt

        return dt.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        return None


def _digest_toa_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Resumen ligero para raw.json (sin escaleras completas de bookmakers)."""
    bids = ev.get("bookmakers") or []
    mk_keys: set[str] = set()
    totals_points: list[float] = []
    h2h_n = 0
    for bk in bids[:12]:
        if not isinstance(bk, dict):
            continue
        for mkt in bk.get("markets") or []:
            if not isinstance(mkt, dict):
                continue
            k = (mkt.get("key") or "").lower()
            mk_keys.add(k or "?")
            if k == "h2h":
                h2h_n = max(h2h_n, len(mkt.get("outcomes") or []))
            if k == "totals":
                for o in mkt.get("outcomes") or []:
                    if not isinstance(o, dict):
                        continue
                    pt = o.get("point")
                    if pt is not None:
                        try:
                            totals_points.append(float(pt))
                        except (TypeError, ValueError):
                            pass
    return {
        "id": ev.get("id"),
        "commence_time": ev.get("commence_time"),
        "home_team": ev.get("home_team"),
        "away_team": ev.get("away_team"),
        "market_keys": sorted(mk_keys),
        "h2h_outcome_count_max": h2h_n,
        "totals_distinct_points": len(set(round(p, 3) for p in totals_points)),
        "totals_points_sample": sorted(set(round(p, 2) for p in totals_points))[:8],
    }


def _markets_from_toa_event(ev: dict[str, Any]) -> tuple[bool, bool, set[float], bool]:
    """
    FT_1X2 ready: mercado h2h con al menos 2 outcomes con price.
    totals ready: mercado totals con al menos 2 outcomes.
    OU lines: conjunto de points en totals.
    OU2.5: point 2.5 (±0.05) presente.
    """
    h2h_ok = False
    totals_ok = False
    points: set[float] = set()
    ou25 = False
    for bk in ev.get("bookmakers") or []:
        if not isinstance(bk, dict):
            continue
        for mkt in bk.get("markets") or []:
            if not isinstance(mkt, dict):
                continue
            key = (mkt.get("key") or "").lower()
            outs = [o for o in (mkt.get("outcomes") or []) if isinstance(o, dict)]
            if key == "h2h":
                priced = sum(1 for o in outs if o.get("price") is not None)
                if priced >= 2:
                    h2h_ok = True
            if key == "totals":
                if len(outs) >= 2:
                    totals_ok = True
                for o in outs:
                    pt = o.get("point")
                    if pt is None:
                        continue
                    try:
                        pf = float(pt)
                        points.add(round(pf, 4))
                        if abs(pf - 2.5) < 0.051:
                            ou25 = True
                    except (TypeError, ValueError):
                        pass
    return h2h_ok, totals_ok, points, ou25


def _match_fixture(
    ev: dict[str, Any],
    fixtures_by_sport: dict[str, list[Any]],
    norm_team,
) -> tuple[Any | None, float]:
    """Devuelve (FixtureRow|None, score)."""
    h = str(ev.get("home_team") or "")
    a = str(ev.get("away_team") or "")
    ct = str(ev.get("commence_time") or "")
    ctd = _parse_commence(ct)
    sk = str(ev.get("sport_key") or "")
    candidates = fixtures_by_sport.get(sk) or []
    if not candidates:
        return None, -1.0
    best = None
    best_score = -1.0
    for f in candidates:
        delta = abs((f.kickoff_utc - ctd).total_seconds()) if ctd else 9e9
        sh = norm_team(f.home_team) == norm_team(h)
        sa = norm_team(f.away_team) == norm_team(a)
        score = (2.0 if sh and sa else 0.0) - min(delta, 7200.0) / 7200.0
        if score > best_score:
            best_score = score
            best = f
    return best, best_score


def _load_checkpoint() -> dict[str, Any]:
    if not CHECKPOINT_PATH.is_file():
        return {"version": 1, "completed_pairs": [], "updated_at_utc": None}
    try:
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "completed_pairs": [], "updated_at_utc": None}


def _save_checkpoint(
    completed: set[str],
    partial_stats: dict[str, Any],
) -> None:
    payload = {
        "version": 1,
        "completed_pairs": sorted(completed),
        "stats_partial": partial_stats,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    CHECKPOINT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    import psycopg2
    import psycopg2.extras

    p = argparse.ArgumentParser(description="MM-3.1B TOA P0 controlled backfill")
    p.add_argument("--dry-run", action="store_true", help="Plan + artefactos vacíos; sin HTTP")
    p.add_argument("--reset-checkpoint", action="store_true", help="Borra checkpoint antes de correr")
    p.add_argument("--db-url", default="", help="Override BT2_DATABASE_URL")
    p.add_argument("--http-timeout", type=int, default=45)
    args = p.parse_args()

    m31a = _load_mm3_1a()
    _ensure_out()

    if args.reset_checkpoint and CHECKPOINT_PATH.is_file():
        CHECKPOINT_PATH.unlink()

    dsn = m31a._sync_dsn(args.db_url.strip() or m31a._load_bt2_database_url())
    print("MM3_1B: conectando Postgres (SELECT)…", flush=True)
    conn = psycopg2.connect(dsn, connect_timeout=30)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout TO 0")
    fixtures = m31a.fetch_fixtures(cur, None, None)
    conn.close()

    fixtures = [f for f in fixtures if f.toa_sport_key in ALLOWED_SPORT_KEYS]
    fixtures_by_sport: dict[str, list[Any]] = defaultdict(list)
    for f in fixtures:
        fixtures_by_sport[f.toa_sport_key].append(f)

    keys = sorted(m31a.compute_deduped_requests(fixtures, "t60"))
    total_planned = len(keys)

    ck = _load_checkpoint()
    completed: set[str] = set(ck.get("completed_pairs") or [])

    # Opcional: leer batches 3.1A solo para métricas en summary
    batches_note = ""
    bp = OUT_DIR / "mm3_1a_backfill_batches.json"
    if bp.is_file():
        batches_note = str(bp)

    api_key = "" if args.dry_run else m31a._load_theoddsapi_key()
    if not args.dry_run and not api_key:
        print("Falta THEODDSAPI_KEY", file=sys.stderr)
        sys.exit(1)

    markets_param = "h2h,totals"
    regions_param = "eu"

    calls_out: list[dict[str, Any]] = []
    match_rows: dict[int, dict[str, Any]] = {}
    reject_rows: list[dict[str, Any]] = []
    board_by_event: dict[int, dict[str, Any]] = {}

    stats = {
        "requests_executed": 0,
        "requests_skipped_resume": 0,
        "sum_x_requests_last": 0.0,
        "last_x_requests_remaining": None,
        "last_x_requests_used": None,
        "provider_errors": [],
        "stop_reason": None,
    }

    consecutive_err = 0
    last_err_msg: str | None = None
    same_err_repeat = 0
    rolling_last: list[float] = []

    sport_completed: set[str] = set()
    ts_completed: set[str] = set()

    if not args.dry_run:
        pending = sum(1 for sk, ts in keys if _pair_key(sk, ts) not in completed)
        print(
            f"MM3_1B: inicio HTTP — total_pairs={total_planned}, pending={pending}, "
            f"checkpoint_pairs_prev={len(completed)}",
            flush=True,
        )

    for sk, ts_iso in keys:
        pk = _pair_key(sk, ts_iso)
        if pk in completed:
            stats["requests_skipped_resume"] += 1
            continue

        rem = stats["last_x_requests_remaining"]
        if rem is not None:
            try:
                if int(str(rem)) < MIN_REMAINING_ABORT:
                    stats["stop_reason"] = f"x-requests-remaining {rem} < {MIN_REMAINING_ABORT}"
                    break
            except (TypeError, ValueError):
                pass

        if stats["requests_executed"] >= MAX_REQUESTS_RUN:
            stats["stop_reason"] = "max_requests_for_this_run"
            break
        if stats["sum_x_requests_last"] + EXPECTED_CREDITS_PER_REQUEST > MAX_CREDITS_RUN:
            stats["stop_reason"] = "max_credits_for_this_run"
            break

        if args.dry_run:
            continue

        url = m31a.ODDS_HISTORICAL_PATH.format(sport=sk) + "?" + urlencode(
            {
                "apiKey": api_key,
                "regions": regions_param,
                "markets": markets_param,
                "dateFormat": "iso",
                "oddsFormat": "decimal",
                "date": ts_iso,
            }
        )
        try:
            body, hdrs, status = m31a.http_get_json(url, timeout=args.http_timeout)
            consecutive_err = 0
            same_err_repeat = 0
            last_err_msg = None
        except Exception as exc:
            consecutive_err += 1
            em = f"{pk}: {exc}"
            stats["provider_errors"].append(em)
            msg = str(exc)
            if msg == last_err_msg:
                same_err_repeat += 1
            else:
                same_err_repeat = 1
                last_err_msg = msg
            if consecutive_err >= CONSECUTIVE_ERROR_ABORT:
                stats["stop_reason"] = "consecutive_http_errors"
                break
            if same_err_repeat >= SAME_ERROR_REPEAT_ABORT:
                stats["stop_reason"] = "repeated_provider_error_message"
                break
            time.sleep(2.0)
            continue

        xl_raw = hdrs.get("x-requests-last")
        try:
            xl = float(xl_raw) if xl_raw is not None else 0.0
        except (TypeError, ValueError):
            xl = 0.0
        stats["sum_x_requests_last"] += xl
        stats["last_x_requests_remaining"] = hdrs.get("x-requests-remaining")
        stats["last_x_requests_used"] = hdrs.get("x-requests-used")
        stats["requests_executed"] += 1

        if xl_raw is not None and int(float(xl_raw)) != EXPECTED_CREDITS_PER_REQUEST:
            stats["stop_reason"] = f"x-requests-last {xl_raw} != {EXPECTED_CREDITS_PER_REQUEST}"
            rolling_last.append(xl)
            break
        rolling_last.append(xl)
        if len(rolling_last) >= ROLLING_WINDOW:
            w = rolling_last[-ROLLING_WINDOW:]
            avg = sum(w) / len(w)
            if abs(avg - EXPECTED_CREDITS_PER_REQUEST) > ROLLING_DEVIATION_MAX:
                stats["stop_reason"] = f"rolling_avg_x_requests_last_deviation avg={avg}"
                break

        events = []
        if isinstance(body, dict):
            ev = body.get("data")
            if isinstance(ev, list):
                events = ev

        digest_events = []
        for toa_ev in events:
            if not isinstance(toa_ev, dict):
                continue
            digest_events.append(_digest_toa_event(toa_ev))
            fx, score = _match_fixture(toa_ev, fixtures_by_sport, m31a._norm_team)
            eid_toa = str(toa_ev.get("id") or "")
            if fx and score >= 1.5:
                bid = fx.event_id
                h2h_ok, tot_ok, pts, ou25 = _markets_from_toa_event(toa_ev)
                row = {
                    "bt2_event_id": bid,
                    "toa_event_id": eid_toa,
                    "sport_key": sk,
                    "query_timestamp_utc": ts_iso,
                    "response_timestamp": body.get("timestamp"),
                    "kickoff_bt2_utc": fx.kickoff_utc.isoformat(),
                    "commence_toa": toa_ev.get("commence_time"),
                    "home_bt2": fx.home_team,
                    "away_bt2": fx.away_team,
                    "home_toa": toa_ev.get("home_team"),
                    "away_toa": toa_ev.get("away_team"),
                    "match_score": round(score, 4),
                }
                match_rows[bid] = row
                br = board_by_event.get(bid) or {
                    "bt2_event_id": bid,
                    "sport_key": fx.toa_sport_key,
                    "ft_1x2_ready": False,
                    "totals_ready": False,
                    "ou_lines_union": set(),
                    "ou25_ready": False,
                }
                br["ft_1x2_ready"] = br["ft_1x2_ready"] or h2h_ok
                br["totals_ready"] = br["totals_ready"] or tot_ok
                br["ou_lines_union"].update(pts)
                br["ou25_ready"] = br["ou25_ready"] or ou25
                board_by_event[bid] = br
            else:
                reject_rows.append(
                    {
                        "sport_key": sk,
                        "query_timestamp_utc": ts_iso,
                        "toa_event_id": eid_toa,
                        "commence_toa": toa_ev.get("commence_time"),
                        "home_toa": toa_ev.get("home_team"),
                        "away_toa": toa_ev.get("away_team"),
                        "reason": "no_bt2_match_or_low_score",
                        "match_score": round(score, 4) if fx else None,
                    }
                )

        calls_out.append(
            {
                "pair": pk,
                "http_status": status,
                "x_requests_last": xl_raw,
                "x_requests_remaining": hdrs.get("x-requests-remaining"),
                "response_timestamp": body.get("timestamp") if isinstance(body, dict) else None,
                "n_events": len(events),
                "events_digest": digest_events[:25],
            }
        )

        completed.add(pk)
        sport_completed.add(sk)
        ts_completed.add(ts_iso)

        if stats["requests_executed"] % CHECKPOINT_EVERY == 0:
            _save_checkpoint(completed, stats)
            print(
                f"MM3_1B: checkpoint — requests={stats['requests_executed']}, "
                f"credits_sum={stats['sum_x_requests_last']:.0f}, "
                f"remaining={stats['last_x_requests_remaining']}, "
                f"matched_bt2={len(match_rows)}, stop={stats['stop_reason']}",
                flush=True,
            )

        time.sleep(0.12)

    if not args.dry_run:
        _save_checkpoint(completed, stats)

    # Board rows
    board_rows: list[dict[str, Any]] = []
    ou_line_total = 0
    for bid, br in board_by_event.items():
        lines = br.get("ou_lines_union") or set()
        ou_line_total += len(lines)
        board_rows.append(
            {
                "bt2_event_id": bid,
                "sport_key": br.get("sport_key"),
                "ft_1x2_ready": br.get("ft_1x2_ready"),
                "totals_ready": br.get("totals_ready"),
                "ou_lines_count": len(lines),
                "ou_lines_sorted": ",".join(str(x) for x in sorted(lines)),
                "ou25_ready": br.get("ou25_ready"),
            }
        )
    board_rows.sort(key=lambda r: r["bt2_event_id"])

    ft_ready = sum(1 for r in board_rows if r["ft_1x2_ready"])
    tot_ready = sum(1 for r in board_rows if r["totals_ready"])
    ou25_ready = sum(1 for r in board_rows if r["ou25_ready"])

    cost_formula_ok = False
    if stats["requests_executed"] > 0:
        exp = stats["requests_executed"] * EXPECTED_CREDITS_PER_REQUEST
        obs = stats["sum_x_requests_last"]
        cost_formula_ok = abs(obs - exp) < 0.51

    n_fix = len(fixtures)
    n_matched = len(match_rows)
    match_frac = (n_matched / n_fix) if n_fix else 0.0
    ready_mm32 = (
        not args.dry_run
        and stats["stop_reason"] is None
        and stats["requests_executed"] > 0
        and cost_formula_ok
        and match_frac >= 0.65
        and (ft_ready / max(1, n_matched)) >= 0.70
        and (tot_ready / max(1, n_matched)) >= 0.55
    )
    ready_mm32_reasons: list[str] = []
    if args.dry_run:
        ready_mm32_reasons.append("dry_run_no_http")
    else:
        if stats["stop_reason"]:
            ready_mm32_reasons.append(f"run_stopped:{stats['stop_reason']}")
        if stats["requests_executed"] == 0:
            ready_mm32_reasons.append("no_requests_executed")
        if match_frac < 0.65:
            ready_mm32_reasons.append(f"match_coverage_low:{match_frac:.3f}")
        if n_matched and (ft_ready / n_matched) < 0.70:
            ready_mm32_reasons.append("ft_1x2_ready_below_threshold")
        if n_matched and (tot_ready / n_matched) < 0.55:
            ready_mm32_reasons.append("totals_ready_below_threshold")
        if stats["requests_executed"] > 0 and not cost_formula_ok:
            ready_mm32_reasons.append("cost_sum_mismatch_vs_20x_requests")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "requests_executed": stats["requests_executed"],
        "requests_skipped_resume": stats["requests_skipped_resume"],
        "credits_consumed_sum_x_requests_last": stats["sum_x_requests_last"],
        "remaining_credits_final": stats["last_x_requests_remaining"],
        "requests_used_header_final": stats["last_x_requests_used"],
        "sport_keys_completed_distinct": sorted(sport_completed),
        "timestamps_completed_distinct_count": len(ts_completed),
        "total_planned_pairs": total_planned,
        "planned_credits_if_full_run": total_planned * EXPECTED_CREDITS_PER_REQUEST,
        "checkpoint_pairs_completed_total": len(completed),
        "bt2_fixtures_in_scope": n_fix,
        "bt2_events_matched_distinct": n_matched,
        "match_coverage_vs_fixtures": round(match_frac, 4),
        "ft_1x2_ready_count": ft_ready,
        "totals_ready_count": tot_ready,
        "ou_lines_detected_sum_across_matched": ou_line_total,
        "ou2_5_ready_count": ou25_ready,
        "failed_rejected_match_rows": len(reject_rows),
        "provider_errors_count": len(stats["provider_errors"]),
        "provider_errors_sample": stats["provider_errors"][:20],
        "cost_formula_still_confirmed": cost_formula_ok,
        "ready_for_mm3_2_feature_dataset": ready_mm32,
        "ready_for_mm3_2_feature_dataset_reasons": ready_mm32_reasons,
        "stop_reason": stats["stop_reason"],
        "mm3_1a_batches_artifact": batches_note or None,
        "repo_fix_candidates": REPO_FIX_CANDIDATES,
    }

    RAW_PATH.write_text(
        json.dumps({"calls": calls_out}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    COST_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_csv(
        MATCH_CSV,
        [
            "bt2_event_id",
            "toa_event_id",
            "sport_key",
            "query_timestamp_utc",
            "response_timestamp",
            "kickoff_bt2_utc",
            "commence_toa",
            "home_bt2",
            "away_bt2",
            "home_toa",
            "away_toa",
            "match_score",
        ],
        list(sorted(match_rows.values(), key=lambda x: int(x["bt2_event_id"]))),
    )
    _write_csv(
        REJ_CSV,
        [
            "sport_key",
            "query_timestamp_utc",
            "toa_event_id",
            "commence_toa",
            "home_toa",
            "away_toa",
            "reason",
            "match_score",
        ],
        reject_rows,
    )
    _write_csv(
        BOARD_CSV,
        [
            "bt2_event_id",
            "sport_key",
            "ft_1x2_ready",
            "totals_ready",
            "ou_lines_count",
            "ou_lines_sorted",
            "ou25_ready",
        ],
        board_rows,
    )

    by_league: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in fixtures:
        by_league[f.toa_sport_key]["fixtures"] += 1
    for bid in match_rows:
        fx = next((x for x in fixtures if x.event_id == bid), None)
        if fx:
            by_league[fx.toa_sport_key]["matched"] += 1

    board_json = {
        "by_sport_key": {
            sk: {
                "fixtures": by_league[sk]["fixtures"],
                "matched_bt2": by_league[sk].get("matched", 0),
            }
            for sk in sorted(ALLOWED_SPORT_KEYS)
        },
        "matched_board": {
            "ft_1x2_ready": ft_ready,
            "totals_ready": tot_ready,
            "ou2_5_ready": ou25_ready,
            "ou_lines_sum": ou_line_total,
        },
    }
    BOARD_JSON.write_text(json.dumps(board_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # Audit markdown
    audit = f"""# MM-3.1B — TOA P0 Controlled Backfill (Audit)

## 1. Executive summary

- Modo: **{"dry-run" if args.dry_run else "HTTP ejecutado"}**.
- Requests ejecutados: **{stats["requests_executed"]}** (omitidos por resume: **{stats["requests_skipped_resume"]}**).
- Créditos consumidos (suma `x-requests-last`): **{stats["sum_x_requests_last"]}**.
- Remaining final (header): **{stats["last_x_requests_remaining"]}**.
- Partidos BT2 en alcance: **{n_fix}**; matcheados distintos: **{n_matched}** ({match_frac:.1%}).
- FT_1x2 listos: **{ft_ready}**; totals listos: **{tot_ready}**; OU 2.5 listo: **{ou25_ready}**.
- `ready_for_mm3_2_feature_dataset`: **{ready_mm32}** — {", ".join(ready_mm32_reasons) or "criterios cumplidos"}.
- Stop: `{stats["stop_reason"]}`.

## 2. Scope and restrictions

P0 only: **h2h, totals**, **eu**, **T-60**, Big 5 `sport_key` fijos. Sin DB writes, sin DSR/SM, sin P1/P2.

## 3. Why MM-3.1B was approved

MM-3.1A validó endpoint, **20 créditos/request** y matching piloto.

## 4. Pilot recap

Ver `docs/bettracker2/audits/MM3_1A_TOA_HISTORICAL_SWEEP_COST_ESTIMATOR_AUDIT.md` y piloto EPL.

## 5. Cost limits and stop conditions

Máx **{MAX_CREDITS_RUN}** créditos, **{MAX_REQUESTS_RUN}** requests; abort si remaining **<{MIN_REMAINING_ABORT}**; checkpoint cada **{CHECKPOINT_EVERY}**; resume por `mm3_1b_toa_p0_checkpoint.json`; `x-requests-last` ≠ **{EXPECTED_CREDITS_PER_REQUEST}** aborta; errores consecutivos / mensaje repetido abortan.

## 6. Execution summary

Pares planeados: **{total_planned}**. Pares en checkpoint al final: **{len(completed)}**.

## 7. Coverage by league

```json
{json.dumps(board_json["by_sport_key"], indent=2)}
```

## 8. Coverage by market

Resumen board: FT_1x2 ready **{ft_ready}**, totals ready **{tot_ready}**, líneas OU (suma por evento): **{ou_line_total}**, OU2.5 ready **{ou25_ready}**.

## 9. Match/rejection analysis

- Matches: `{MATCH_CSV.name}` (**{n_matched}** filas).
- Rechazos TOA-event: `{REJ_CSV.name}` (**{len(reject_rows)}** filas).

## 10. Cost reconciliation

Suma `x-requests-last` = **{stats["sum_x_requests_last"]}** vs **20 × requests** = **{stats["requests_executed"] * EXPECTED_CREDITS_PER_REQUEST}** → formula_ok **{cost_formula_ok}**.

## 11. Output market board

- `{BOARD_JSON.name}`, `{BOARD_CSV.name}`.

## 12. What this proves

Existencia de snapshots TOA T-60 alineables a BT2 con mercados P0 presentes en payload (subconjunto verificado por filas board).

## 13. What this does not prove

ROI de estrategia, calidad de todas las casas, cobertura fuera del rango DB, ni ausencia de sesgo de matching.

## 14. Recommended next step

Persistencia controlada (fuera de MM-3.1B) o MM-3.2 feature matrix si `ready_for_mm3_2_feature_dataset` es true; si false, revisar stop_reason y umbrales de match.

## 15. Repo fix candidates (main / cleanup, fuera de MM-3.1B)

No modificar `theoddsapi_worker.py` dentro de este backfill. Candidato registrado (también en `mm3_1b_summary.json` → `repo_fix_candidates`):

```json
{json.dumps(REPO_FIX_CANDIDATES, indent=2, ensure_ascii=False)}
```
"""
    AUDIT_PATH.write_text(audit, encoding="utf-8")

    print(
        f"MM3_1B: fin — requests={stats['requests_executed']}, credits={stats['sum_x_requests_last']:.0f}, "
        f"remaining={stats['last_x_requests_remaining']}, matched={n_matched}, "
        f"ready_mm32={ready_mm32}, stop={stats['stop_reason']}",
        flush=True,
    )
    print("MM3_1B: listo —", SUMMARY_PATH, flush=True)


if __name__ == "__main__":
    main()
