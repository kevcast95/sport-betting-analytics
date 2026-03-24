"""
API de lectura (y escritura mínima) sobre SQLite del scrapper.
Ejecutar desde la raíz del repo: PYTHONPATH=. uvicorn apps.api.main:app --reload
"""

import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

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
    DashboardRecentPick,
    DashboardSummaryBlock,
    EnsureBaselinesResponse,
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
    UserComboTakenBody,
    UserCreate,
    UserOut,
    UserPickTakenBody,
)
from db.config import get_db_config
from db.db import connect as db_connect
from db.init_db import init_db
from db.repositories.dashboard_repo import (
    _effective_outcome,
    daily_picks_summary,
    recent_picks_for_date,
)
from db.repositories.pick_event_meta_repo import (
    load_event_meta_for_daily_run,
    merge_meta_into_odds_ref,
)
from db.sqlite_migrate import apply_migrations
from db.repositories.picks_repo import set_pick_status
from db.repositories.suggest_combos_repo import (
    list_legs_for_combo,
    list_suggested_combos_with_legs,
    regenerate_suggested_combos,
)
from db.repositories.tracking_repo import (
    ensure_pick_baselines_for_run,
    get_combo_decisions_for_run,
    get_pick_decision_rows_for_run,
    insert_signal_check,
    upsert_user_combo_decision,
    upsert_user_pick_decision,
)
from db.repositories.users_repo import (
    ensure_default_test_users,
    get_user_by_id,
    insert_user,
    list_users,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Aplica schema.sql (IF NOT EXISTS) al arrancar: evita 500 si faltan tablas nuevas."""
    cfg = get_db_config()
    conn = db_connect(cfg.path)
    try:
        init_db(conn)
        apply_migrations(conn)
        conn.commit()
    finally:
        conn.close()
    yield


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

_global_deps = [Depends(verify_local_api_key)]


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    cfg = get_db_config()
    return HealthOut(ok=True, db_path=cfg.path)


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
) -> DashboardBundleOut:
    rd = run_date or date.today().isoformat()
    if only_taken and user_id is None:
        raise HTTPException(
            status_code=400,
            detail="only_taken requiere user_id",
        )
    if user_id is not None and get_user_by_id(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    s = daily_picks_summary(conn, run_date=rd, user_id=user_id)
    raw_recent = recent_picks_for_date(conn, run_date=rd, user_id=user_id, limit=40)
    recent: List[DashboardRecentPick] = []
    meta_cache: Dict[int, Dict[int, Dict[str, Optional[str]]]] = {}
    for r in raw_recent:
        if only_taken and r["u_taken"] != 1:
            continue
        if len(recent) >= 15:
            break
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
                selection_display=sel_disp,
                odds_reference=odds_parsed,
            )
        )
    return DashboardBundleOut(
        summary=DashboardSummaryBlock(
            run_date=str(s["run_date"]),
            picks_total=int(s["picks_total"]),
            outcome_wins=int(s["outcome_wins"]),
            outcome_losses=int(s["outcome_losses"]),
            outcome_pending=int(s["outcome_pending"]),
            picks_taken_count=int(s["picks_taken_count"]),
            taken_outcome_wins=int(s.get("taken_outcome_wins", 0)),
            taken_outcome_losses=int(s.get("taken_outcome_losses", 0)),
            taken_outcome_pending=int(s.get("taken_outcome_pending", 0)),
            net_pl_estimate=s["net_pl_estimate"],
            has_stake_data=bool(s["has_stake_data"]),
        ),
        recent=recent,
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
        where.append("sport = ?")
        params.append(sport)
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
    d["odds_reference"] = merge_meta_into_odds_ref(d.get("odds_reference"), meta)
    return PickSummary.model_validate(d)


def _pick_summary_from_join_row(r: sqlite3.Row) -> PickSummary:
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
    )


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
            pr.validated_at_utc AS pr_validated_at_utc,
            pr.home_score AS pr_home_score,
            pr.away_score AS pr_away_score,
            pr.result_1x2 AS pr_result_1x2,
            pr.outcome AS pr_outcome,
            pr.evidence_json AS pr_evidence_json
        FROM picks p
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
            pr.validated_at_utc AS pr_validated_at_utc,
            pr.home_score AS pr_home_score,
            pr.away_score AS pr_away_score,
            pr.result_1x2 AS pr_result_1x2,
            pr.outcome AS pr_outcome,
            pr.evidence_json AS pr_evidence_json
        FROM picks p
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        WHERE p.pick_id = ?
    """
    r = conn.execute(sql, (pick_id,)).fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="pick not found")
    summary = _pick_summary_from_join_row(r)
    emap = load_event_meta_for_daily_run(conn, daily_run_id=int(summary.daily_run_id))
    summary = _apply_event_meta(summary, emap)
    return PickDetail.model_validate(summary.model_dump())


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
    return [
        UserOut(
            user_id=int(r["user_id"]),
            slug=str(r["slug"]),
            display_name=str(r["display_name"]),
            created_at_utc=str(r["created_at_utc"]),
        )
        for r in rows
    ]


@app.post("/users", response_model=UserOut, dependencies=_global_deps)
def api_create_user(body: UserCreate, conn: DbConn) -> UserOut:
    try:
        uid = insert_user(conn, slug=body.slug, display_name=body.display_name)
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=409, detail="slug duplicado") from e
    row = get_user_by_id(conn, uid)
    assert row is not None
    return UserOut(
        user_id=int(row["user_id"]),
        slug=str(row["slug"]),
        display_name=str(row["display_name"]),
        created_at_utc=str(row["created_at_utc"]),
    )


@app.post("/users/bootstrap", response_model=List[UserOut], dependencies=_global_deps)
def api_bootstrap_users(conn: DbConn) -> List[UserOut]:
    rows = ensure_default_test_users(conn)
    conn.commit()
    return [
        UserOut(
            user_id=int(r["user_id"]),
            slug=str(r["slug"]),
            display_name=str(r["display_name"]),
            created_at_utc=str(r["created_at_utc"]),
        )
        for r in rows
    ]


@app.get(
    "/daily-runs/{daily_run_id}/board",
    response_model=TrackingBoardOut,
    dependencies=_global_deps,
)
def api_tracking_board(
    daily_run_id: int,
    conn: DbConn,
    user_id: int = Query(..., description="Usuario que ve el tablero"),
) -> TrackingBoardOut:
    if get_user_by_id(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    run = conn.execute(
        "SELECT daily_run_id, run_date, sport, status FROM daily_runs WHERE daily_run_id = ?",
        (daily_run_id,),
    ).fetchone()
    if run is None:
        raise HTTPException(status_code=404, detail="daily_run not found")

    sql = """
        SELECT
            p.pick_id, p.daily_run_id, p.event_id, p.market, p.selection,
            p.picked_value, p.odds_reference, p.status, p.created_at_utc, p.idempotency_key,
            pr.validated_at_utc AS pr_validated_at_utc,
            pr.home_score AS pr_home_score,
            pr.away_score AS pr_away_score,
            pr.result_1x2 AS pr_result_1x2,
            pr.outcome AS pr_outcome,
            pr.evidence_json AS pr_evidence_json
        FROM picks p
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        WHERE p.daily_run_id = ?
        ORDER BY p.pick_id DESC
    """
    rows = conn.execute(sql, (daily_run_id,)).fetchall()
    emap = load_event_meta_for_daily_run(conn, daily_run_id=daily_run_id)
    detail = get_pick_decision_rows_for_run(
        conn, user_id=user_id, daily_run_id=daily_run_id
    )
    picks_out: List[PickSummary] = []
    for r in rows:
        s = _apply_event_meta(_pick_summary_from_join_row(r), emap)
        pid = int(r["pick_id"])
        dr = detail.get(pid)
        dump = s.model_dump()
        if dr is not None:
            dump["user_taken"] = bool(dr["taken"])
            dump["risk_category"] = dr["risk_category"]
            dump["decision_origin"] = dr["decision_origin"]
            dump["stake_amount"] = (
                float(dr["stake_amount"]) if dr["stake_amount"] is not None else None
            )
            uox = dr["user_outcome"]
            dump["user_outcome"] = (
                uox if uox in ("win", "loss", "pending") else None
            )
        else:
            dump["user_taken"] = None
            dump["risk_category"] = None
            dump["decision_origin"] = None
            dump["stake_amount"] = None
            dump["user_outcome"] = None
        picks_out.append(PickSummary.model_validate(dump))

    combo_rows = list_suggested_combos_with_legs(conn, daily_run_id=daily_run_id)
    combo_decisions = get_combo_decisions_for_run(conn, user_id=user_id, daily_run_id=daily_run_id)
    combos_out: List[SuggestedComboOut] = []
    for c in combo_rows:
        cid = int(c["suggested_combo_id"])
        legs_raw = list_legs_for_combo(conn, suggested_combo_id=cid)
        legs = [
            ComboLegOut(
                pick_id=int(x["pick_id"]),
                leg_order=int(x["leg_order"]),
                event_id=int(x["event_id"]),
                market=str(x["market"]),
                selection=str(x["selection"]),
            )
            for x in legs_raw
        ]
        cd = combo_decisions.get(cid)
        combos_out.append(
            SuggestedComboOut(
                suggested_combo_id=cid,
                daily_run_id=int(c["daily_run_id"]),
                rank_order=int(c["rank_order"]),
                created_at_utc=str(c["created_at_utc"]),
                strategy_note=c["strategy_note"],
                legs=legs,
                user_taken=cd if cid in combo_decisions else None,
            )
        )

    return TrackingBoardOut(
        run=DailyRunBoardOut(
            daily_run_id=int(run["daily_run_id"]),
            run_date=str(run["run_date"]),
            sport=str(run["sport"]),
            status=str(run["status"]),
        ),
        user_id=user_id,
        picks=picks_out,
        suggested_combos=combos_out,
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
    if get_user_by_id(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    pr = conn.execute("SELECT 1 FROM picks WHERE pick_id = ?", (pick_id,)).fetchone()
    if pr is None:
        raise HTTPException(status_code=404, detail="pick not found")
    prev = conn.execute(
        """
        SELECT user_outcome FROM user_pick_decisions
        WHERE user_id = ? AND pick_id = ?
        """,
        (user_id, pick_id),
    ).fetchone()
    prev_uo = prev["user_outcome"] if prev else None
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
        stake_amount=body.stake_amount,
        user_outcome=merged_uo,
    )
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
    if get_user_by_id(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    cr = conn.execute(
        "SELECT 1 FROM suggested_combos WHERE suggested_combo_id = ?",
        (combo_id,),
    ).fetchone()
    if cr is None:
        raise HTTPException(status_code=404, detail="combo not found")
    upsert_user_combo_decision(
        conn, user_id=user_id, suggested_combo_id=combo_id, taken=body.taken
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
