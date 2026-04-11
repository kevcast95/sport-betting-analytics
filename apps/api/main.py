"""
API de lectura (y escritura mínima) sobre SQLite del scrapper + rutas BetTracker `/bt2` (Postgres).

Ejecutar desde la raíz del repo: `PYTHONPATH="${PWD}" python3 -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload`
(o `npm run dev:api`). Requiere `.env` para BT2 — ver `docs/bettracker2/LOCAL_API.md` y `.env.example`.
"""

import sqlite3
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from apps.api.bt2_router import router as bt2_router
from apps.api.deps import DbConn, verify_local_api_key
from apps.api.jsonutil import parse_json_field
from apps.api.schemas import (
    BacktestRunOut,
    BacktestRunPage,
    ComboLegOut,
    DailyRunBoardOut,
    DailyRunOut,
    DailyRunPage,
    DashboardBundleOut,
    DashboardPerformanceBlock,
    DashboardPerformanceSplit,
    DashboardRecentPick,
    DashboardSummaryBlock,
    DailyRunEventInspectOut,
    DailyRunEventsInspectOut,
    EnsureBaselinesResponse,
    EffectivenessReportStatusOut,
    PipelineReplayRequest,
    PipelineReplayResponse,
    HealthOut,
    PickDetail,
    PickPage,
    PickResultOut,
    PickStatusPatch,
    PickStatusPatchResponse,
    PickSummary,
    RegenerateCombosResponse,
    SignalCheckBody,
    SignalCheckOut,
    SuggestedComboOut,
    TrackingBoardOut,
    ValidatePicksWindowOut,
    UserBankrollBody,
    UserComboTakenBody,
    UserCreate,
    UserOut,
    UserPickTakenBody,
    ValidatePicksRunResponse,
    RevertRecentPickOutcomesResponse,
)
from db.config import get_db_config
from db.db import connect as db_connect
from db.init_db import init_db
from db.repositories.dashboard_repo import (
    _effective_outcome,
    _execution_slot_from_created_at_utc,
    dashboard_insights,
    daily_picks_summary,
    recent_picks_for_date,
)
from db.repositories.model_feedback_repo import fetch_feedback_map
from db.repositories.pick_event_meta_repo import (
    is_stake_taken_locked_now,
    load_event_meta_for_daily_run,
    merge_meta_into_odds_ref,
)
from db.repositories.picks_repo import set_pick_status
from db.repositories.suggest_combos_repo import (
    list_legs_for_combo,
    list_suggested_combos_with_legs,
    regenerate_suggested_combos,
)
from db.repositories.tracking_repo import (
    ensure_pick_baselines_for_run,
    get_combo_decision_rows_for_run,
    get_pick_decision_rows_for_run,
    insert_signal_check,
    sync_user_pick_realized_return,
    revert_user_outcomes_auto_for_recent_picks,
    upsert_user_combo_decision,
    upsert_user_pick_decision,
)
from db.repositories.users_repo import (
    ensure_default_test_users,
    get_user_by_id,
    insert_user,
    list_users,
    set_user_bankroll_cop,
)
from core.candidate_contract import (
    base_contract_ok,
    classify_tier,
    diagnostics_flags,
    normalize_sport,
    reject_reason as contract_reject_reason,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Aplica schema.sql (IF NOT EXISTS) al arrancar: evita 500 si faltan tablas nuevas."""
    cfg = get_db_config()
    conn = db_connect(cfg.path)
    try:
        init_db(conn)
        conn.commit()
    finally:
        conn.close()
    yield


def _validate_hour_bounds() -> Tuple[int, int, int, int]:
    """Defaults alineados con scripts/run_validate_picks_scheduled.sh."""
    min_m = int(os.environ.get("ALTEA_VALIDATE_MORNING_HOUR_MIN", "5"))
    max_m = int(os.environ.get("ALTEA_VALIDATE_MORNING_HOUR_MAX_EXCL", "13"))
    min_e = int(os.environ.get("ALTEA_VALIDATE_AFTERNOON_HOUR_MIN", "16"))
    max_e = int(os.environ.get("ALTEA_VALIDATE_AFTERNOON_HOUR_MAX_EXCL", "24"))
    return min_m, max_m, min_e, max_e


def _execution_slot_from_created_at_utc(created_at_utc: str) -> Tuple[str, str]:
    """
    Clasifica la hora local de creación del run (cohortes ALTEA_VALIDATE_*).
    """
    tz_name = os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota")
    tz = ZoneInfo(tz_name)
    t = str(created_at_utc).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(tz)
    h = local.hour
    min_m, max_m, min_e, max_e = _validate_hour_bounds()
    if min_m <= h < max_m:
        return (
            "morning",
            f"mañana (creación local [{min_m:02d},{max_m:02d}), {tz_name})",
        )
    if min_e <= h < max_e:
        return (
            "evening",
            f"tarde/noche (creación local [{min_e:02d},{max_e:02d}), {tz_name})",
        )
    return "night", f"fuera de cohortes mañana/tarde ({tz_name})"


def _validate_picks_window_for_run_date(
    run_date: str,
) -> Tuple[Optional[str], Optional[int], Optional[int], str, Literal["morning", "evening", "full"]]:
    """
    Cohorte que debe usar validate_picks.py según **reloj local ahora** y fecha del run.

    - Día del run = hoy: ventana 1 si hora < fin mañana; si no, ventana 2 (tarde/noche).
      Inicio ventana 2: ALTEA_VALIDATE_UI_AFTERNOON_HOUR_MIN o, si no existe, fin exclusivo mañana
      (segunda mitad del día contigua al script de mañana).
    - Run histórico: sin recorte horario (todos los pendientes del run).
    """
    tz_name = os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    today_s = now.date().isoformat()
    run_d = str(run_date).strip()
    min_m, max_m, min_e, max_e = _validate_hour_bounds()
    afternoon_start_raw = os.environ.get("ALTEA_VALIDATE_UI_AFTERNOON_HOUR_MIN")
    if afternoon_start_raw is not None and str(afternoon_start_raw).strip() != "":
        afternoon_start = int(str(afternoon_start_raw).strip())
    else:
        afternoon_start = max_m

    if run_d < today_s:
        return (
            None,
            None,
            None,
            f"Run histórico ({run_d}): cohorte completa (sin filtro horario). Zona: {tz_name}.",
            "full",
        )
    if run_d > today_s:
        return (
            None,
            None,
            None,
            f"Fecha del run futura ({run_d}): sin filtro horario. Zona: {tz_name}.",
            "full",
        )

    H = now.hour
    if H < max_m:
        label = (
            f"Mañana: picks creados el {run_d} en "
            f"[{min_m:02d}:00, {max_m:02d}:00) local ({tz_name})."
        )
        return run_d, min_m, max_m, label, "morning"

    lo, hi = afternoon_start, max_e
    if lo >= hi:
        lo, hi = min_e, max_e
    label = (
        f"Tarde/noche: picks creados el {run_d} en "
        f"[{lo:02d}:00, {hi:02d}:00) local ({tz_name})."
    )
    return run_d, lo, hi, label, "evening"


def _parse_validate_picks_stdout(text: str) -> Optional[Dict[str, Any]]:
    marker = "=== VALIDATE_PICKS ==="
    if marker not in text:
        return None
    chunk = text.split(marker, 1)[1]
    if "=== OK" in chunk:
        chunk = chunk.split("=== OK", 1)[0]
    try:
        return json.loads(chunk.strip())
    except json.JSONDecodeError:
        return None


def _user_out_from_row(r: sqlite3.Row) -> UserOut:
    br = r["bankroll_cop"]
    return UserOut(
        user_id=int(r["user_id"]),
        slug=str(r["slug"]),
        display_name=str(r["display_name"]),
        created_at_utc=str(r["created_at_utc"]),
        bankroll_cop=float(br) if br is not None else None,
    )


app = FastAPI(
    title="Scrapper tracking API",
    version="0.1.0",
    description="Lectura de daily_runs, picks, pick_results y backtests (SQLite).",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    # Vite puede usar 5174 si 5173 está ocupado; preview en 4173
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):(5173|5174|4173)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bt2_router)

_global_deps = [Depends(verify_local_api_key)]


def _h2h_summary_from_processed(processed: Any) -> Optional[str]:
    if not isinstance(processed, dict):
        return None
    h2h = processed.get("h2h")
    if not isinstance(h2h, dict):
        return None
    duel = h2h.get("team_duel")
    if not isinstance(duel, dict):
        return None
    try:
        hw = int(duel.get("home_wins"))
        dr = int(duel.get("draws"))
        aw = int(duel.get("away_wins"))
    except (TypeError, ValueError):
        return None
    return f"H2H {hw}-{dr}-{aw} (home-draw-away)"


def _latest_effectiveness_report_path() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(repo_root, "out", "reports", "effectiveness_latest.json")


def _read_latest_effectiveness_report() -> Optional[Dict[str, Any]]:
    p = _latest_effectiveness_report_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _stake_amount_unchanged(
    a: Optional[float], b: Optional[float]
) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return round(float(a), 2) == round(float(b), 2)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    cfg = get_db_config()
    return HealthOut(ok=True, db_path=cfg.path)


@app.get(
    "/reports/effectiveness/latest-status",
    response_model=EffectivenessReportStatusOut,
    dependencies=_global_deps,
)
def api_latest_effectiveness_report_status() -> EffectivenessReportStatusOut:
    raw = _read_latest_effectiveness_report()
    if raw is None:
        return EffectivenessReportStatusOut(available=False)
    totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
    return EffectivenessReportStatusOut(
        available=True,
        generated_at_utc=str(raw.get("generated_at_utc")) if raw.get("generated_at_utc") else None,
        range_start=str(raw.get("range_start")) if raw.get("range_start") else None,
        range_end=str(raw.get("range_end")) if raw.get("range_end") else None,
        days=int(raw["days"]) if raw.get("days") is not None else None,
        issued=int(totals["issued"]) if totals.get("issued") is not None else None,
        settled=int(totals["settled"]) if totals.get("settled") is not None else None,
        win_rate=float(totals["win_rate"]) if totals.get("win_rate") is not None else None,
        roi_unit=float(totals["roi_unit"]) if totals.get("roi_unit") is not None else None,
    )


@app.get("/dashboard", response_model=DashboardBundleOut, dependencies=_global_deps)
def api_dashboard(
    conn: DbConn,
    run_date: Optional[str] = Query(
        None,
        description="YYYY-MM-DD (default: hoy en el servidor)",
    ),
    user_id: Optional[int] = Query(
        None,
        description="Para métricas ‘tomé’ / stake / P/L estimado",
    ),
    only_taken: bool = Query(
        False,
        description="Si true, la lista reciente solo incluye picks marcados como tomados",
    ),
    sport: str = Query(
        "football",
        description="Filtra por `daily_runs.sport` (ej. football, tennis).",
    ),
    recent_limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Tamaño de página para la lista reciente de picks.",
    ),
    recent_page: int = Query(
        0,
        ge=0,
        description="Página 0-based de la lista reciente (con recent_limit).",
    ),
) -> DashboardBundleOut:
    rd = run_date or date.today().isoformat()
    se = str(sport or "football").strip().lower()
    if se not in ("football", "tennis"):
        se = "football"
    if only_taken and user_id is None:
        raise HTTPException(
            status_code=400,
            detail="only_taken requiere user_id",
        )
    urow = get_user_by_id(conn, user_id) if user_id is not None else None
    if user_id is not None and urow is None:
        raise HTTPException(status_code=404, detail="user not found")
    s = daily_picks_summary(conn, run_date=rd, user_id=user_id, sport=se)
    ins = dashboard_insights(conn, run_date=rd, sport=se, user_id=user_id)
    br_dash = urow["bankroll_cop"] if urow is not None else None
    bankroll_summary = float(br_dash) if br_dash is not None else None
    off = int(recent_page) * int(recent_limit)
    raw_recent, recent_total = recent_picks_for_date(
        conn,
        run_date=rd,
        user_id=user_id,
        offset=off,
        limit=int(recent_limit),
        only_taken=bool(only_taken),
        sport=se,
    )
    recent: List[DashboardRecentPick] = []
    meta_cache: Dict[int, Dict[int, Dict[str, Optional[str]]]] = {}
    for r in raw_recent:
        pr_o = r["pr_outcome"]
        uo = r["u_outcome"]
        eff = _effective_outcome(uo, pr_o)
        if pr_o in ("win", "loss"):
            sys_od: str = str(pr_o)
        elif pr_o == "pending":
            sys_od = "pending"
        else:
            sys_od = "pending"
        uo_out = uo if uo in ("win", "loss", "pending") else None
        drid = int(r["daily_run_id"])
        if drid not in meta_cache:
            meta_cache[drid] = load_event_meta_for_daily_run(conn, daily_run_id=drid)
        em = meta_cache[drid].get(int(r["event_id"]))
        odds_parsed = parse_json_field(
            str(r["odds_reference"]) if r["odds_reference"] is not None else None
        )
        sel_disp = _selection_display_from_odds_ref(odds_parsed)
        slot_v, slot_lbl = _execution_slot_from_created_at_utc(r["run_created_at_utc"])
        recent.append(
            DashboardRecentPick(
                pick_id=int(r["pick_id"]),
                daily_run_id=drid,
                event_id=int(r["event_id"]),
                market=str(r["market"]),
                selection=str(r["selection"]),
                picked_value=r["picked_value"],
                created_at_utc=str(r["created_at_utc"]),
                outcome=eff,  # type: ignore[arg-type]
                outcome_system=sys_od,  # type: ignore[arg-type]
                user_outcome=uo_out,  # type: ignore[arg-type]
                user_taken=bool(r["u_taken"]) if r["u_taken"] is not None else None,
                risk_category=r["u_risk"],
                decision_origin=r["u_origin"],
                stake_amount=float(r["u_stake"]) if r["u_stake"] is not None else None,
                event_label=em.get("event_label") if em else None,
                league=em.get("league") if em else None,
                kickoff_display=em.get("kickoff_display") if em else None,
                kickoff_at_utc=em.get("kickoff_at_utc") if em else None,
                match_state=em.get("match_state") if em else None,
                execution_slot=slot_v,  # type: ignore[arg-type]
                execution_slot_label_es=slot_lbl,
                selection_display=sel_disp,
                odds_reference=odds_parsed,
            )
        )
    return DashboardBundleOut(
        summary=DashboardSummaryBlock(
            run_date=str(s["run_date"]),
            sport=s.get("sport"),
            primary_daily_run_id=s.get("primary_daily_run_id"),
            events_total=int(s.get("events_total", 0)),
            selection_passed_filters=int(s.get("selection_passed_filters", 0)),
            selection_rejected=int(s.get("selection_rejected", 0)),
            selection_selected_events=int(s.get("selection_selected_events", 0)),
            selection_top_reject_reason=s.get("selection_top_reject_reason"),
            selection_top_reject_reason_count=int(
                s.get("selection_top_reject_reason_count", 0)
            ),
            selection_analyzed_without_pick=int(
                s.get("selection_analyzed_without_pick", 0)
            ),
            picks_total=int(s["picks_total"]),
            outcome_wins=int(s["outcome_wins"]),
            outcome_losses=int(s["outcome_losses"]),
            outcome_pending=int(s["outcome_pending"]),
            settled_count=int(s.get("settled_count", 0)),
            roi_unit=(
                float(s["roi_unit"])
                if s.get("roi_unit") is not None
                else None
            ),
            settled_count_tradable=int(s.get("settled_count_tradable", 0)),
            settled_count_below_min_odds=int(s.get("settled_count_below_min_odds", 0)),
            min_tradable_odds=(
                float(s["min_tradable_odds"])
                if s.get("min_tradable_odds") is not None
                else None
            ),
            roi_unit_tradable=(
                float(s["roi_unit_tradable"])
                if s.get("roi_unit_tradable") is not None
                else None
            ),
            picks_taken_count=int(s["picks_taken_count"]),
            taken_outcome_wins=int(s.get("taken_outcome_wins", 0)),
            taken_outcome_losses=int(s.get("taken_outcome_losses", 0)),
            taken_outcome_pending=int(s.get("taken_outcome_pending", 0)),
            performance=DashboardPerformanceBlock(
                totals=DashboardPerformanceSplit(
                    wins=int(s["outcome_wins"]),
                    losses=int(s["outcome_losses"]),
                    pending=int(s["outcome_pending"]),
                ),
                taken=DashboardPerformanceSplit(
                    wins=int(s.get("taken_outcome_wins", 0)),
                    losses=int(s.get("taken_outcome_losses", 0)),
                    pending=int(s.get("taken_outcome_pending", 0)),
                ),
                not_taken=DashboardPerformanceSplit(
                    wins=int(s.get("not_taken_outcome_wins", 0)),
                    losses=int(s.get("not_taken_outcome_losses", 0)),
                    pending=int(s.get("not_taken_outcome_pending", 0)),
                ),
            ),
            bankroll_cop=bankroll_summary,
            net_pl_estimate=s["net_pl_estimate"],
            has_stake_data=bool(s["has_stake_data"]),
        ),
        recent=recent,
        issued_daily=ins.get("issued_daily") or [],
        rolling_by_sport=ins.get("rolling_by_sport") or [],
        calibration=ins.get("calibration"),
        recent_total=int(recent_total),
    )


@app.get("/daily-runs", response_model=DailyRunPage, dependencies=_global_deps)
def list_daily_runs(
    conn: DbConn,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[int] = Query(
        None,
        description="Keyset estable: daily_run_id estrictamente menor que este valor",
    ),
    run_date: Optional[str] = None,
    sport: Optional[str] = None,
    status: Optional[str] = None,
) -> DailyRunPage:
    take = limit + 1
    where: List[str] = []
    params: List[Any] = []
    if cursor is not None:
        where.append("daily_run_id < ?")
        params.append(cursor)
    if run_date is not None:
        where.append("run_date = ?")
        params.append(run_date)
    if sport is not None:
        where.append("LOWER(TRIM(sport)) = ?")
        params.append(str(sport).strip().lower())
    if status is not None:
        where.append("status = ?")
        params.append(status)
    wh = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT daily_run_id, run_date, sport, created_at_utc, status
        FROM daily_runs
        {wh}
        ORDER BY daily_run_id DESC
        LIMIT ?
    """
    params.append(take)
    rows = conn.execute(sql, tuple(params)).fetchall()
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [
        DailyRunOut(
            daily_run_id=int(r["daily_run_id"]),
            run_date=str(r["run_date"]),
            sport=str(r["sport"]),
            created_at_utc=str(r["created_at_utc"]),
            status=str(r["status"]),  # type: ignore[arg-type]
        )
        for r in page_rows
    ]
    next_cursor = int(rows[limit]["daily_run_id"]) if has_more else None
    return DailyRunPage(items=items, next_cursor=next_cursor)


@app.get(
    "/daily-runs/{daily_run_id}/events",
    response_model=DailyRunEventsInspectOut,
    dependencies=_global_deps,
)
def api_daily_run_events_inspect(
    daily_run_id: int,
    conn: DbConn,
    limit: int = Query(500, ge=1, le=2000),
) -> DailyRunEventsInspectOut:
    run = conn.execute(
        "SELECT daily_run_id, run_date, created_at_utc, sport FROM daily_runs WHERE daily_run_id = ?",
        (daily_run_id,),
    ).fetchone()
    if run is None:
        raise HTTPException(status_code=404, detail="daily_run not found")

    run_sport = normalize_sport(run["sport"])
    feature_rows = conn.execute(
        """
        SELECT event_id, features_json
        FROM event_features
        WHERE captured_at_utc = ? AND sport = ?
        ORDER BY event_id ASC
        LIMIT ?
        """,
        (str(run["created_at_utc"]), run_sport, int(limit)),
    ).fetchall()

    selected_event_ids = {
        int(r["event_id"])
        for r in conn.execute(
            "SELECT DISTINCT event_id FROM picks WHERE daily_run_id = ?",
            (daily_run_id,),
        ).fetchall()
    }

    model_feedback_by_event = fetch_feedback_map(conn, daily_run_id=int(daily_run_id))

    items: List[DailyRunEventInspectOut] = []
    for r in feature_rows:
        raw = parse_json_field(r["features_json"])
        feat = raw if isinstance(raw, dict) else {}
        event_context = feat.get("event_context") if isinstance(feat.get("event_context"), dict) else {}
        diagnostics = feat.get("diagnostics") if isinstance(feat.get("diagnostics"), dict) else {}
        processed = feat.get("processed") if isinstance(feat.get("processed"), dict) else feat.get("processed")
        match_state = str(event_context.get("match_state") or "").lower()
        flags = diagnostics_flags(diagnostics)
        tier = classify_tier(flags, sport=run_sport)
        passed = base_contract_ok(flags, sport=run_sport) and match_state != "finished"
        reject_reason = (
            None
            if passed
            else contract_reject_reason(flags, match_state, sport=run_sport)
        )
        eid = int(r["event_id"])
        mf = model_feedback_by_event.get(eid)
        model_skip_reason = mf[0] if mf else None
        pipeline_skip_summary = mf[1] if mf else None
        items.append(
            DailyRunEventInspectOut(
                daily_run_id=int(daily_run_id),
                event_id=eid,
                event_label=(
                    f"{event_context.get('home_team') or '?'} vs {event_context.get('away_team') or '?'}"
                ),
                league=(
                    str(event_context.get("tournament"))
                    if event_context.get("tournament") is not None
                    else None
                ),
                h2h_summary=_h2h_summary_from_processed(processed),
                match_state=match_state or None,
                passed_candidate_filters=passed,
                in_ds_input=eid in selected_event_ids,
                reject_reason=reject_reason,
                model_skip_reason=model_skip_reason,
                pipeline_skip_summary=pipeline_skip_summary,
                selection_tier=tier if tier in ("A", "B") else None,
                event_context=event_context,
                diagnostics=diagnostics,
                processed=processed,
            )
        )

    return DailyRunEventsInspectOut(
        daily_run_id=int(run["daily_run_id"]),
        run_date=str(run["run_date"]),
        sport=str(run["sport"]),
        captured_at_utc=str(run["created_at_utc"]),
        total_events=len(items),
        items=items,
    )


def _selection_display_from_odds_ref(odds_reference: Any) -> Optional[str]:
    if isinstance(odds_reference, dict):
        v = odds_reference.get("selection_display")
        return str(v) if v is not None else None
    return None


def _apply_event_meta(
    s: PickSummary,
    emap: Dict[int, Dict[str, Optional[str]]],
) -> PickSummary:
    meta = emap.get(s.event_id)
    if not meta:
        return s
    d = s.model_dump()
    d["event_label"] = meta.get("event_label")
    d["league"] = meta.get("league")
    d["kickoff_display"] = meta.get("kickoff_display")
    d["kickoff_at_utc"] = meta.get("kickoff_at_utc")
    d["match_state"] = meta.get("match_state")
    d["odds_reference"] = merge_meta_into_odds_ref(d.get("odds_reference"), meta)
    return PickSummary.model_validate(d)


def _pick_summary_from_join_row(r: sqlite3.Row) -> PickSummary:
    slot_v, slot_lbl = _execution_slot_from_created_at_utc(
        r["run_created_at_utc"] if "run_created_at_utc" in r.keys() else None
    )
    result = None
    if r["pr_validated_at_utc"] is not None:
        result = PickResultOut(
            validated_at_utc=str(r["pr_validated_at_utc"]),
            home_score=r["pr_home_score"],
            away_score=r["pr_away_score"],
            result_1x2=r["pr_result_1x2"],  # type: ignore[arg-type]
            outcome=str(r["pr_outcome"]),  # type: ignore[arg-type]
            evidence_json=parse_json_field(
                str(r["pr_evidence_json"]) if r["pr_evidence_json"] is not None else None
            ),
        )
    keys = r.keys()
    run_date_v = (
        str(r["run_date"])
        if "run_date" in keys and r["run_date"] is not None
        else None
    )
    return PickSummary(
        pick_id=int(r["pick_id"]),
        daily_run_id=int(r["daily_run_id"]),
        event_id=int(r["event_id"]),
        market=str(r["market"]),
        selection=str(r["selection"]),  # type: ignore[arg-type]
        picked_value=r["picked_value"],
        odds_reference=parse_json_field(r["odds_reference"] if r["odds_reference"] else None),
        status=str(r["status"]),  # type: ignore[arg-type]
        created_at_utc=str(r["created_at_utc"]),
        idempotency_key=str(r["idempotency_key"]),
        result=result,
        run_date=run_date_v,
        execution_slot=slot_v,  # type: ignore[arg-type]
        execution_slot_label_es=slot_lbl,
    )


def _pick_summary_merge_user_detail(
    s: PickSummary,
    dr: Optional[sqlite3.Row],
) -> PickSummary:
    dump = s.model_dump()
    if dr is not None:
        dump["user_taken"] = bool(dr["taken"])
        dump["risk_category"] = dr["risk_category"]
        dump["decision_origin"] = dr["decision_origin"]
        dump["stake_amount"] = (
            float(dr["stake_amount"]) if dr["stake_amount"] is not None else None
        )
        uox = dr["user_outcome"]
        dump["user_outcome"] = uox if uox in ("win", "loss", "pending") else None
        rr = dr["realized_return_cop"]
        dump["realized_return_cop"] = float(rr) if rr is not None else None
    else:
        dump["user_taken"] = None
        dump["risk_category"] = None
        dump["decision_origin"] = None
        dump["stake_amount"] = None
        dump["user_outcome"] = None
        dump["realized_return_cop"] = None
    return PickSummary.model_validate(dump)


def _is_tradable_pick_summary(s: PickSummary, min_tradable_odds: float) -> bool:
    pv_raw = s.picked_value
    pv = float(pv_raw) if pv_raw is not None else 0.0
    if pv >= min_tradable_odds:
        return True
    ref = s.odds_reference
    if isinstance(ref, dict):
        tv = ref.get("tradable")
        if isinstance(tv, bool):
            return tv
    return False


def _pick_summary_effective_outcome(s: PickSummary) -> str:
    if s.status == "void":
        return "pending"
    uo = s.user_outcome
    pr_o = s.result.outcome if s.result else None
    return _effective_outcome(uo, pr_o)


def _combo_outcome_from_leg_picks(
    picks_by_id: Dict[int, PickSummary],
    leg_pick_ids: List[int],
) -> str:
    try:
        outs = [_pick_summary_effective_outcome(picks_by_id[pid]) for pid in leg_pick_ids]
    except KeyError:
        return "pending"
    if any(o == "loss" for o in outs):
        return "loss"
    if all(o == "win" for o in outs):
        return "win"
    return "pending"


@app.get("/picks", response_model=PickPage, dependencies=_global_deps)
def list_picks(
    conn: DbConn,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[int] = Query(
        None,
        description="Keyset estable: pick_id estrictamente menor que este valor",
    ),
    daily_run_id: Optional[int] = None,
    pick_status: Optional[str] = Query(None, alias="status"),
) -> PickPage:
    take = limit + 1
    where: List[str] = []
    params: List[Any] = []
    if cursor is not None:
        where.append("p.pick_id < ?")
        params.append(cursor)
    if daily_run_id is not None:
        where.append("p.daily_run_id = ?")
        params.append(daily_run_id)
    if pick_status is not None:
        where.append("p.status = ?")
        params.append(pick_status)
    wh = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT
            p.pick_id, p.daily_run_id, p.event_id, p.market, p.selection,
            p.picked_value, p.odds_reference, p.status, p.created_at_utc, p.idempotency_key,
            dr.created_at_utc AS run_created_at_utc,
            pr.validated_at_utc AS pr_validated_at_utc,
            pr.home_score AS pr_home_score,
            pr.away_score AS pr_away_score,
            pr.result_1x2 AS pr_result_1x2,
            pr.outcome AS pr_outcome,
            pr.evidence_json AS pr_evidence_json
        FROM picks p
        INNER JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        {wh}
        ORDER BY p.pick_id DESC
        LIMIT ?
    """
    params.append(take)
    rows = conn.execute(sql, tuple(params)).fetchall()
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [_pick_summary_from_join_row(r) for r in page_rows]
    next_cursor = int(rows[limit]["pick_id"]) if has_more else None
    return PickPage(items=items, next_cursor=next_cursor)


@app.get("/picks/{pick_id}", response_model=PickDetail, dependencies=_global_deps)
def get_pick(pick_id: int, conn: DbConn) -> PickDetail:
    sql = """
        SELECT
            p.pick_id, p.daily_run_id, p.event_id, p.market, p.selection,
            p.picked_value, p.odds_reference, p.status, p.created_at_utc, p.idempotency_key,
            dr.run_date AS run_date,
            dr.sport AS run_sport,
            dr.created_at_utc AS run_created_at_utc,
            pr.validated_at_utc AS pr_validated_at_utc,
            pr.home_score AS pr_home_score,
            pr.away_score AS pr_away_score,
            pr.result_1x2 AS pr_result_1x2,
            pr.outcome AS pr_outcome,
            pr.evidence_json AS pr_evidence_json
        FROM picks p
        INNER JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        WHERE p.pick_id = ?
    """
    r = conn.execute(sql, (pick_id,)).fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="pick not found")
    summary = _pick_summary_from_join_row(r)
    emap = load_event_meta_for_daily_run(conn, daily_run_id=int(summary.daily_run_id))
    summary = _apply_event_meta(summary, emap)
    detail_dump = summary.model_dump()
    rs = r["run_sport"] if "run_sport" in r.keys() else None
    detail_dump["run_sport"] = str(rs).strip().lower() if rs is not None else None
    return PickDetail.model_validate(detail_dump)


@app.patch(
    "/picks/{pick_id}/status",
    response_model=PickStatusPatchResponse,
    dependencies=_global_deps,
)
def patch_pick_status(
    pick_id: int,
    body: PickStatusPatch,
    conn: DbConn,
) -> PickStatusPatchResponse:
    """Solo permite marcar void un pick en pending (escritura acotada)."""
    row = conn.execute("SELECT status FROM picks WHERE pick_id = ?", (pick_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="pick not found")
    if str(row["status"]) != "pending":
        raise HTTPException(
            status_code=409,
            detail="solo picks en pending pueden anularse (void)",
        )
    if body.status != "void":
        raise HTTPException(status_code=400, detail="solo status=void está permitido")
    set_pick_status(conn, pick_id=pick_id, status="void")
    conn.commit()
    return PickStatusPatchResponse(ok=True, pick_id=pick_id, status="void")


@app.get("/backtest-runs", response_model=BacktestRunPage, dependencies=_global_deps)
def list_backtest_runs(
    conn: DbConn,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[int] = Query(
        None,
        description="Keyset estable: backtest_run_id estrictamente menor que este valor",
    ),
) -> BacktestRunPage:
    take = limit + 1
    if cursor is not None:
        sql = """
            SELECT
                b.backtest_run_id, b.range_start, b.range_end, b.strategy_version, b.created_at_utc,
                m.metrics_json AS metrics_json
            FROM backtest_runs b
            LEFT JOIN backtest_metrics m ON m.backtest_run_id = b.backtest_run_id
            WHERE b.backtest_run_id < ?
            ORDER BY b.backtest_run_id DESC
            LIMIT ?
        """
        rows = conn.execute(sql, (cursor, take)).fetchall()
    else:
        sql = """
            SELECT
                b.backtest_run_id, b.range_start, b.range_end, b.strategy_version, b.created_at_utc,
                m.metrics_json AS metrics_json
            FROM backtest_runs b
            LEFT JOIN backtest_metrics m ON m.backtest_run_id = b.backtest_run_id
            ORDER BY b.backtest_run_id DESC
            LIMIT ?
        """
        rows = conn.execute(sql, (take,)).fetchall()
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [
        BacktestRunOut(
            backtest_run_id=int(r["backtest_run_id"]),
            range_start=str(r["range_start"]),
            range_end=str(r["range_end"]),
            strategy_version=str(r["strategy_version"]),
            created_at_utc=str(r["created_at_utc"]),
            metrics_json=parse_json_field(r["metrics_json"] if r["metrics_json"] else None),
        )
        for r in page_rows
    ]
    next_cursor = int(rows[limit]["backtest_run_id"]) if has_more else None
    return BacktestRunPage(items=items, next_cursor=next_cursor)


# --- Usuarios y tracking ---


@app.get("/users", response_model=List[UserOut], dependencies=_global_deps)
def api_list_users(conn: DbConn) -> List[UserOut]:
    rows = list_users(conn)
    return [_user_out_from_row(r) for r in rows]


@app.get("/users/{user_id}", response_model=UserOut, dependencies=_global_deps)
def api_get_user(user_id: int, conn: DbConn) -> UserOut:
    row = get_user_by_id(conn, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_out_from_row(row)


@app.put("/users/{user_id}/bankroll", response_model=UserOut, dependencies=_global_deps)
def api_put_user_bankroll(
    user_id: int, body: UserBankrollBody, conn: DbConn
) -> UserOut:
    if get_user_by_id(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    set_user_bankroll_cop(conn, user_id=user_id, bankroll_cop=body.bankroll_cop)
    conn.commit()
    row = get_user_by_id(conn, user_id)
    assert row is not None
    return _user_out_from_row(row)


@app.post("/users", response_model=UserOut, dependencies=_global_deps)
def api_create_user(body: UserCreate, conn: DbConn) -> UserOut:
    try:
        uid = insert_user(conn, slug=body.slug, display_name=body.display_name)
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=409, detail="slug duplicado") from e
    row = get_user_by_id(conn, uid)
    assert row is not None
    return _user_out_from_row(row)


@app.post("/users/bootstrap", response_model=List[UserOut], dependencies=_global_deps)
def api_bootstrap_users(conn: DbConn) -> List[UserOut]:
    rows = ensure_default_test_users(conn)
    conn.commit()
    return [_user_out_from_row(r) for r in rows]


@app.post(
    "/ops/pipeline/replay",
    response_model=PipelineReplayResponse,
    dependencies=_global_deps,
)
def api_pipeline_replay(body: PipelineReplayRequest, conn: DbConn) -> PipelineReplayResponse:
    """
    Re-disparar pasos clave del pipeline desde UI (sin consola):
    - ingest: vuelve a poblar eventos del día/deporte.
    - select: recalcula candidates_{date}_{sport}_select.json para el último daily_run.
    - window: corre análisis DS por ventana (morning/afternoon) con persist_picks.
    """
    cfg = get_db_config()
    repo_root = Path(__file__).resolve().parents[2]
    sp = str(body.sport).strip().lower()
    rd = str(body.run_date).strip()

    def _clip(text: str, n: int = 4000) -> str:
        return text[-n:] if len(text) > n else text

    def _latest_daily_run_id_for_date(run_date: str, sport: str) -> Optional[int]:
        row = conn.execute(
            """
            SELECT daily_run_id
            FROM daily_runs
            WHERE run_date = ? AND LOWER(TRIM(sport)) = ?
            ORDER BY daily_run_id DESC
            LIMIT 1
            """,
            (run_date, sport),
        ).fetchone()
        if row is None or row["daily_run_id"] is None:
            return None
        return int(row["daily_run_id"])

    env = os.environ.copy()
    env["FECHA"] = rd

    if body.step == "ingest":
        cmd = [
            sys.executable,
            str(repo_root / "jobs" / "ingest_daily_events.py"),
            "--sport",
            sp,
            "--date",
            rd,
            "--db",
            cfg.path,
        ]
        if body.limit_ingest is not None:
            cmd += ["--limit", str(int(body.limit_ingest))]
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=1800,
            env=env,
        )
        drid = _latest_daily_run_id_for_date(rd, sp)
        return PipelineReplayResponse(
            ok=proc.returncode == 0,
            step=body.step,
            sport=sp,  # type: ignore[arg-type]
            run_date=rd,
            daily_run_id=drid,
            subprocess_exit_code=int(proc.returncode),
            stdout_excerpt=_clip(proc.stdout or "") or None,
            stderr_excerpt=_clip(proc.stderr or "") or None,
            message=(
                f"Ingest {'OK' if proc.returncode == 0 else 'falló'} para {sp} {rd}"
                + (f" (daily_run_id={drid})" if drid is not None else "")
            ),
        )

    if body.step == "select":
        drid = _latest_daily_run_id_for_date(rd, sp)
        if drid is None:
            raise HTTPException(
                status_code=404,
                detail=f"No existe daily_run para {sp} en {rd}. Ejecuta ingest primero.",
            )
        out_path = repo_root / "out" / f"candidates_{rd}_{sp}_select.json"
        cmd = [
            sys.executable,
            str(repo_root / "jobs" / "select_candidates.py"),
            "--db",
            cfg.path,
            "--daily-run-id",
            str(drid),
            "--limit",
            str(int(body.limit_select or 200)),
            "-o",
            str(out_path),
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
        )
        return PipelineReplayResponse(
            ok=proc.returncode == 0,
            step=body.step,
            sport=sp,  # type: ignore[arg-type]
            run_date=rd,
            daily_run_id=drid,
            subprocess_exit_code=int(proc.returncode),
            stdout_excerpt=_clip(proc.stdout or "") or None,
            stderr_excerpt=_clip(proc.stderr or "") or None,
            message=f"Select {'OK' if proc.returncode == 0 else 'falló'} → {out_path.name}",
        )

    # step=window
    slot = body.slot
    if slot is None:
        raise HTTPException(status_code=400, detail="slot es obligatorio para step=window")
    cmd = [str(repo_root / "scripts" / "run_independent_window.sh"), slot, sp]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=3600,
        env=env,
    )
    drid = _latest_daily_run_id_for_date(rd, sp)
    return PipelineReplayResponse(
        ok=proc.returncode == 0,
        step=body.step,
        sport=sp,  # type: ignore[arg-type]
        run_date=rd,
        slot=slot,  # type: ignore[arg-type]
        daily_run_id=drid,
        subprocess_exit_code=int(proc.returncode),
        stdout_excerpt=_clip(proc.stdout or "") or None,
        stderr_excerpt=_clip(proc.stderr or "") or None,
        message=f"Window {slot} {'OK' if proc.returncode == 0 else 'falló'} para {sp} {rd}",
    )


@app.get(
    "/daily-runs/{daily_run_id}/board",
    response_model=TrackingBoardOut,
    dependencies=_global_deps,
)
def api_tracking_board(
    daily_run_id: int,
    conn: DbConn,
    user_id: Optional[int] = Query(
        None,
        description=(
            "Usuario que ve el tablero. Si se omite, se usa el primer usuario (ORDER BY user_id ASC) "
            "para poder listar picks sin selector en UI."
        ),
    ),
) -> TrackingBoardOut:
    if user_id is None:
        rows_u = list_users(conn)
        if not rows_u:
            raise HTTPException(
                status_code=404,
                detail="no users in database; POST /users/bootstrap or POST /users",
            )
        user_id = int(rows_u[0]["user_id"])
    elif get_user_by_id(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    run = conn.execute(
        """
        SELECT daily_run_id, run_date, sport, status, created_at_utc
        FROM daily_runs WHERE daily_run_id = ?
        """,
        (daily_run_id,),
    ).fetchone()
    if run is None:
        raise HTTPException(status_code=404, detail="daily_run not found")
    slot, slot_label = _execution_slot_from_created_at_utc(str(run["created_at_utc"]))

    sql = """
        SELECT
            p.pick_id, p.daily_run_id, p.event_id, p.market, p.selection,
            p.picked_value, p.odds_reference, p.status, p.created_at_utc, p.idempotency_key,
            dr.created_at_utc AS run_created_at_utc,
            pr.validated_at_utc AS pr_validated_at_utc,
            pr.home_score AS pr_home_score,
            pr.away_score AS pr_away_score,
            pr.result_1x2 AS pr_result_1x2,
            pr.outcome AS pr_outcome,
            pr.evidence_json AS pr_evidence_json
        FROM picks p
        INNER JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        WHERE p.daily_run_id = ?
        ORDER BY p.pick_id DESC
    """
    rows_all = list(conn.execute(sql, (daily_run_id,)).fetchall())
    total_generated = len(rows_all)
    raw_floor = os.environ.get("ALTEA_MIN_TRADABLE_ODDS", "1.30").strip()
    try:
        min_tradable_odds = max(1.0, float(raw_floor))
    except ValueError:
        min_tradable_odds = 1.30

    # Operatividad: en el tablero del run se muestran solo picks tradables.
    # Los no tradables quedan en DB para analítica/rendimiento del modelo.
    def _is_tradable_pick_row(row: sqlite3.Row) -> bool:
        pv_raw = row["picked_value"]
        pv = float(pv_raw) if pv_raw is not None else 0.0
        if pv >= min_tradable_odds:
            return True
        ref_raw = row["odds_reference"]
        if not ref_raw:
            return False
        try:
            ref = json.loads(str(ref_raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        if isinstance(ref, dict):
            tv = ref.get("tradable")
            if isinstance(tv, bool):
                return tv
        return False

    rows_tradable = [r for r in rows_all if _is_tradable_pick_row(r)]
    tradable_visible = len(rows_tradable)
    hidden_non_tradable = max(0, total_generated - tradable_visible)
    emap = load_event_meta_for_daily_run(conn, daily_run_id=daily_run_id)
    detail = get_pick_decision_rows_for_run(
        conn, user_id=user_id, daily_run_id=daily_run_id
    )
    picks_all_by_id: Dict[int, PickSummary] = {}
    for r in rows_all:
        base = _apply_event_meta(_pick_summary_from_join_row(r), emap)
        pid = int(r["pick_id"])
        picks_all_by_id[pid] = _pick_summary_merge_user_detail(base, detail.get(pid))
    picks_out = [picks_all_by_id[int(r["pick_id"])] for r in rows_tradable]

    combo_rows = list_suggested_combos_with_legs(conn, daily_run_id=daily_run_id)
    combo_rows_detail = get_combo_decision_rows_for_run(
        conn, user_id=user_id, daily_run_id=daily_run_id
    )
    combos_out: List[SuggestedComboOut] = []
    for c in combo_rows:
        cid = int(c["suggested_combo_id"])
        legs_raw = list_legs_for_combo(conn, suggested_combo_id=cid)
        legs: List[ComboLegOut] = []
        for x in legs_raw:
            pid = int(x["pick_id"])
            ps = picks_all_by_id.get(pid)
            lo_raw = _pick_summary_effective_outcome(ps) if ps is not None else "pending"
            lo: Literal["win", "loss", "pending"] = (
                lo_raw
                if lo_raw in ("win", "loss", "pending")
                else "pending"
            )
            pv_leg = (
                float(ps.picked_value)
                if ps is not None and ps.picked_value is not None
                else None
            )
            vis = (
                _is_tradable_pick_summary(ps, min_tradable_odds)
                if ps is not None
                else False
            )
            legs.append(
                ComboLegOut(
                    pick_id=pid,
                    leg_order=int(x["leg_order"]),
                    event_id=int(x["event_id"]),
                    market=str(x["market"]),
                    selection=str(x["selection"]),
                    picked_value=pv_leg,
                    leg_outcome=lo,
                    operativo_visible=vis,
                )
            )
        leg_ids = [int(x["pick_id"]) for x in legs_raw]
        from_legs = _combo_outcome_from_leg_picks(picks_all_by_id, leg_ids)
        ddr = combo_rows_detail.get(cid)
        if ddr is not None:
            u_taken = bool(ddr["taken"])
            u_stake = (
                float(ddr["stake_amount"])
                if ddr["stake_amount"] is not None
                else None
            )
            u_ox = ddr["user_outcome"]
            u_out = u_ox if u_ox in ("win", "loss", "pending") else None
        else:
            u_taken = None
            u_stake = None
            u_out = None
        eff = _effective_outcome(u_out, from_legs)
        combos_out.append(
            SuggestedComboOut(
                suggested_combo_id=cid,
                daily_run_id=int(c["daily_run_id"]),
                rank_order=int(c["rank_order"]),
                created_at_utc=str(c["created_at_utc"]),
                strategy_note=c["strategy_note"],
                legs=legs,
                user_taken=u_taken if ddr is not None else None,
                user_stake_amount=u_stake,
                user_outcome=u_out,  # type: ignore[arg-type]
                outcome_from_legs=from_legs,  # type: ignore[arg-type]
                outcome_effective=eff,  # type: ignore[arg-type]
            )
        )

    _lon, _hmin, _hmax, _vlab, _vph = _validate_picks_window_for_run_date(str(run["run_date"]))
    validate_window = ValidatePicksWindowOut(
        label_es=_vlab,
        local_on=_lon,
        hour_min_incl=_hmin,
        hour_max_excl=_hmax,
        phase=_vph,
    )

    return TrackingBoardOut(
        run=DailyRunBoardOut(
            daily_run_id=int(run["daily_run_id"]),
            run_date=str(run["run_date"]),
            sport=str(run["sport"]),
            status=str(run["status"]),
            created_at_utc=str(run["created_at_utc"]),
            execution_slot=slot,  # type: ignore[arg-type]
            execution_slot_label_es=slot_label,
        ),
        user_id=user_id,
        picks=picks_out,
        suggested_combos=combos_out,
        validate_window=validate_window,
        picks_stats={
            "total_generated": total_generated,
            "tradable_visible": tradable_visible,
            "hidden_non_tradable": hidden_non_tradable,
            "min_tradable_odds": round(min_tradable_odds, 2),
        },
    )


@app.post(
    "/daily-runs/{daily_run_id}/validate-picks",
    response_model=ValidatePicksRunResponse,
    dependencies=_global_deps,
)
def api_validate_picks_for_run(daily_run_id: int, conn: DbConn) -> ValidatePicksRunResponse:
    """
    Ejecuta jobs/validate_picks.py para este daily_run_id (SofaScore → pick_results).

    La cohorte horaria (--only-created-local-*) sigue el reloj local y la fecha del run,
    alineada con ALTEA_VALIDATE_* y run_validate_picks_scheduled.sh (ver _validate_picks_window_for_run_date).
    """
    row = conn.execute(
        "SELECT daily_run_id, created_at_utc, run_date FROM daily_runs WHERE daily_run_id = ?",
        (daily_run_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="daily_run not found")
    local_on, hmin, hmax, label_filter, phase = _validate_picks_window_for_run_date(
        str(row["run_date"])
    )
    tz_name = os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota")
    cfg = get_db_config()
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "jobs" / "validate_picks.py"
    if not script.is_file():
        raise HTTPException(status_code=500, detail="validate_picks.py no encontrado en el repo")

    cmd: List[str] = [
        sys.executable,
        str(script),
        "--db",
        cfg.path,
        "--daily-run-id",
        str(daily_run_id),
        "--timezone",
        tz_name,
    ]
    if local_on is not None and hmin is not None and hmax is not None:
        cmd += [
            "--only-created-local-on",
            local_on,
            "--only-created-local-hour-min",
            str(hmin),
            "--only-created-local-hour-max-excl",
            str(hmax),
        ]

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=900,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    parsed = _parse_validate_picks_stdout(proc.stdout or "")
    excerpt = combined[-4000:] if len(combined) > 4000 else combined

    if proc.returncode != 0:
        return ValidatePicksRunResponse(
            ok=False,
            daily_run_id=daily_run_id,
            execution_slot=phase,  # type: ignore[arg-type]
            execution_slot_label_es=label_filter,
            subprocess_exit_code=proc.returncode,
            log_excerpt=excerpt,
            message=(proc.stderr or proc.stdout or "validate_picks terminó con error").strip()[:500],
        )
    if parsed is None:
        return ValidatePicksRunResponse(
            ok=False,
            daily_run_id=daily_run_id,
            execution_slot=phase,  # type: ignore[arg-type]
            execution_slot_label_es=label_filter,
            subprocess_exit_code=proc.returncode,
            log_excerpt=excerpt,
            message="No se pudo parsear la salida de validate_picks",
        )

    total_processed = int(parsed.get("total_processed") or 0)
    return ValidatePicksRunResponse(
        ok=True,
        daily_run_id=daily_run_id,
        execution_slot=phase,  # type: ignore[arg-type]
        execution_slot_label_es=label_filter,
        total_processed=total_processed,
        validated=int(parsed.get("validated") or 0),
        pending_outcomes=int(parsed.get("pending_outcomes") or 0),
        pending_before_filter=int(parsed.get("pending_before_filter") or 0),
        subprocess_exit_code=0,
        message=parsed.get("message") if isinstance(parsed.get("message"), str) else None,
    )


@app.post(
    "/users/{user_id}/picks/revert-recent-outcomes",
    response_model=RevertRecentPickOutcomesResponse,
    dependencies=_global_deps,
)
def api_revert_recent_pick_outcomes(
    user_id: int,
    conn: DbConn,
    minutes: int = Query(90, ge=1, le=24 * 60),
) -> RevertRecentPickOutcomesResponse:
    """
    Revertir el cierre manual del usuario (user_outcome) a "automático"
    para picks modificados en los últimos `minutes`.

    Criterio:
      - user_outcome_updated_at_utc >= now - minutes
      - user_outcome IN ('win','loss','pending')
    """
    urow = get_user_by_id(conn, user_id)
    if urow is None:
        raise HTTPException(status_code=404, detail="user not found")

    res = revert_user_outcomes_auto_for_recent_picks(
        conn,
        user_id=user_id,
        minutes=minutes,
    )
    conn.commit()
    return RevertRecentPickOutcomesResponse(
        ok=True,
        user_id=user_id,
        minutes=int(minutes),
        affected_picks=int(res.get("affected_picks") or 0),
    )


@app.put(
    "/users/{user_id}/picks/{pick_id}/taken",
    dependencies=_global_deps,
)
def api_put_pick_taken(
    user_id: int,
    pick_id: int,
    body: UserPickTakenBody,
    conn: DbConn,
) -> dict:
    urow = get_user_by_id(conn, user_id)
    if urow is None:
        raise HTTPException(status_code=404, detail="user not found")
    pick_row = conn.execute(
        "SELECT daily_run_id, event_id FROM picks WHERE pick_id = ?",
        (pick_id,),
    ).fetchone()
    if pick_row is None:
        raise HTTPException(status_code=404, detail="pick not found")
    daily_run_id = int(pick_row["daily_run_id"])
    event_id = int(pick_row["event_id"])
    prev = conn.execute(
        """
        SELECT taken, user_outcome, stake_amount FROM user_pick_decisions
        WHERE user_id = ? AND pick_id = ?
        """,
        (user_id, pick_id),
    ).fetchone()
    prev_taken_bool = bool(prev["taken"]) if prev else False
    prev_uo = prev["user_outcome"] if prev else None
    prev_stake = (
        float(prev["stake_amount"])
        if prev and prev["stake_amount"] is not None
        else None
    )
    if "stake_amount" in body.model_fields_set:
        merged_stake_pick: Optional[float] = body.stake_amount
    else:
        merged_stake_pick = prev_stake

    if is_stake_taken_locked_now(
        conn, daily_run_id=daily_run_id, event_id=event_id
    ):
        if body.taken != prev_taken_bool:
            raise HTTPException(
                status_code=400,
                detail=(
                    "El partido ya terminó: no se puede "
                    "cambiar si tomaste el pick."
                ),
            )
        if not _stake_amount_unchanged(merged_stake_pick, prev_stake):
            raise HTTPException(
                status_code=400,
                detail=(
                    "El partido ya terminó: el monto "
                    "ya no es editable."
                ),
            )

    if body.taken and (merged_stake_pick is None or merged_stake_pick <= 0):
        raise HTTPException(
            status_code=400,
            detail="Para marcar el pick como tomado hace falta un monto (stake) mayor a 0.",
        )

    br_raw = urow["bankroll_cop"]
    bankroll = float(br_raw) if br_raw is not None else None
    if body.taken and merged_stake_pick is not None and merged_stake_pick > 0:
        if bankroll is None or bankroll <= 0:
            raise HTTPException(
                status_code=400,
                detail="Define tu bankroll en el usuario antes de marcar un pick tomado con monto.",
            )
        if merged_stake_pick > bankroll:
            raise HTTPException(
                status_code=400,
                detail="El monto no puede superar tu bankroll.",
            )

    if body.user_outcome_auto:
        merged_uo: Optional[str] = None
    elif "user_outcome" in body.model_fields_set:
        merged_uo = body.user_outcome
    else:
        merged_uo = prev_uo if prev_uo in ("win", "loss", "pending") else None

    upsert_user_pick_decision(
        conn,
        user_id=user_id,
        pick_id=pick_id,
        taken=body.taken,
        notes=body.notes,
        risk_category=body.risk_category,
        decision_origin=body.decision_origin,
        stake_amount=merged_stake_pick,
        user_outcome=merged_uo,
    )
    sync_user_pick_realized_return(conn, user_id=user_id, pick_id=pick_id)
    conn.commit()
    return {"ok": True, "user_id": user_id, "pick_id": pick_id, "taken": body.taken}


@app.put(
    "/users/{user_id}/suggested-combos/{combo_id}/taken",
    dependencies=_global_deps,
)
def api_put_combo_taken(
    user_id: int,
    combo_id: int,
    body: UserComboTakenBody,
    conn: DbConn,
) -> dict:
    urow = get_user_by_id(conn, user_id)
    if urow is None:
        raise HTTPException(status_code=404, detail="user not found")
    cr = conn.execute(
        "SELECT 1 FROM suggested_combos WHERE suggested_combo_id = ?",
        (combo_id,),
    ).fetchone()
    if cr is None:
        raise HTTPException(status_code=404, detail="combo not found")
    prev = conn.execute(
        """
        SELECT stake_amount, user_outcome FROM user_combo_decisions
        WHERE user_id = ? AND suggested_combo_id = ?
        """,
        (user_id, combo_id),
    ).fetchone()
    prev_stake = float(prev["stake_amount"]) if prev and prev["stake_amount"] is not None else None
    prev_uo = prev["user_outcome"] if prev else None

    if "stake_amount" in body.model_fields_set:
        merged_stake: Optional[float] = body.stake_amount
    else:
        merged_stake = prev_stake

    if body.user_outcome_auto:
        merged_uo: Optional[str] = None
    elif "user_outcome" in body.model_fields_set:
        merged_uo = body.user_outcome
    else:
        merged_uo = prev_uo if prev_uo in ("win", "loss", "pending") else None

    if body.taken and (merged_stake is None or merged_stake <= 0):
        raise HTTPException(
            status_code=400,
            detail="Para marcar la combinada como tomada hace falta un monto mayor a 0.",
        )

    br_raw = urow["bankroll_cop"]
    bankroll = float(br_raw) if br_raw is not None else None
    if body.taken and merged_stake is not None and merged_stake > 0:
        if bankroll is None or bankroll <= 0:
            raise HTTPException(
                status_code=400,
                detail="Define tu bankroll en el usuario antes de marcar una combinada tomada con monto.",
            )
        if merged_stake > bankroll:
            raise HTTPException(
                status_code=400,
                detail="El monto no puede superar tu bankroll.",
            )

    upsert_user_combo_decision(
        conn,
        user_id=user_id,
        suggested_combo_id=combo_id,
        taken=body.taken,
        stake_amount=merged_stake,
        user_outcome=merged_uo,
    )
    conn.commit()
    return {"ok": True, "user_id": user_id, "suggested_combo_id": combo_id, "taken": body.taken}


@app.post(
    "/daily-runs/{daily_run_id}/suggested-combos/regenerate",
    response_model=RegenerateCombosResponse,
    dependencies=_global_deps,
)
def api_regenerate_combos(daily_run_id: int, conn: DbConn) -> RegenerateCombosResponse:
    run = conn.execute(
        "SELECT 1 FROM daily_runs WHERE daily_run_id = ?",
        (daily_run_id,),
    ).fetchone()
    if run is None:
        raise HTTPException(status_code=404, detail="daily_run not found")
    ids = regenerate_suggested_combos(conn, daily_run_id=daily_run_id)
    conn.commit()
    return RegenerateCombosResponse(
        ok=True, daily_run_id=daily_run_id, suggested_combo_ids=ids
    )


@app.post(
    "/daily-runs/{daily_run_id}/pick-baselines",
    response_model=EnsureBaselinesResponse,
    dependencies=_global_deps,
)
def api_ensure_baselines(daily_run_id: int, conn: DbConn) -> EnsureBaselinesResponse:
    run = conn.execute(
        "SELECT 1 FROM daily_runs WHERE daily_run_id = ?",
        (daily_run_id,),
    ).fetchone()
    if run is None:
        raise HTTPException(status_code=404, detail="daily_run not found")
    n = ensure_pick_baselines_for_run(conn, daily_run_id=daily_run_id)
    conn.commit()
    return EnsureBaselinesResponse(
        ok=True, daily_run_id=daily_run_id, baselines_inserted=n
    )


@app.post(
    "/picks/{pick_id}/signal-checks",
    response_model=SignalCheckOut,
    dependencies=_global_deps,
)
def api_signal_check(pick_id: int, body: SignalCheckBody, conn: DbConn) -> SignalCheckOut:
    pr = conn.execute("SELECT 1 FROM picks WHERE pick_id = ?", (pick_id,)).fetchone()
    if pr is None:
        raise HTTPException(status_code=404, detail="pick not found")
    cid = insert_signal_check(
        conn,
        pick_id=pick_id,
        slot=body.slot.strip(),
        status=body.status,
        detail=body.detail,
    )
    conn.commit()
    return SignalCheckOut(ok=True, check_id=cid)
