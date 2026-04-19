"""
Rutas BT2 — Sprint 03 / Sprint 04.
Sprint 04 añade dominio conductual: picks, sesión operativa, settings, DP ledger.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Literal, Optional, Tuple, cast

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from apps.api.bt2_dx_constants import (
    BT2_ERR_DP_INSUFFICIENT_PREMIUM,
    BT2_ERR_INSUFFICIENT_BANKROLL_STAKE,
    BT2_ERR_PICK_KICKOFF_ELAPSED,
    DP_PREMIUM_UNLOCK_COST,
    VAULT_DAILY_UNLOCK_CAP_PREMIUM,
    VAULT_DAILY_UNLOCK_CAP_STANDARD,
    VAULT_DAILY_UNLOCK_CAP_TOTAL,
    PICK_SETTLE_DP_REWARD,
    PENALTY_STATION_UNCLOSED_DP,
    PENALTY_UNSETTLED_DP,
    REASON_PENALTY_STATION_UNCLOSED,
    REASON_PENALTY_UNSETTLED_NOT_APPLICABLE,
    REASON_PENALTY_UNSETTLED_PICKS,
    REASON_PICK_PREMIUM_UNLOCK,
    REASON_PICK_SETTLE,
    REASON_SESSION_CLOSE_DISCIPLINE,
    SESSION_CLOSE_DISCIPLINE_REWARD_DP,
)
from apps.api.bt2_dsr_contract import PIPELINE_VERSION_DEFAULT
from apps.api.bt2_dsr_deepseek import deepseek_suggest_batch
from apps.api.bt2_dsr_ds_input_builder import aggregated_odds_for_event_psycopg, build_ds_input_item_from_db
from apps.api.bt2_dsr_odds_aggregation import (
    consensus_decimal_for_canonical_pick,
    data_completeness_score,
)
from apps.api.bt2_dsr_postprocess import hash_for_ds_input_item, postprocess_dsr_pick
from apps.api.bt2_dsr_suggest import (
    PIPELINE_VERSION_DEEPSEEK,
    consensus_to_legacy_odds,
    suggest_for_snapshot_row,
    suggest_sql_stat_fallback_from_consensus,
)
from apps.api.bt2_value_pool import (
    MIN_ODDS_DECIMAL_DEFAULT,
    build_value_pool_for_snapshot,
    count_future_events_window,
    parse_priority_league_ids,
)
from apps.api.bt2_market_canonical import (
    determine_settlement_outcome,
    evaluate_model_vs_result,
    market_canonical_label_es,
    normalized_pick_to_canonical,
    selection_canonical_summary_es,
)
from apps.api.bt2_schemas import (
    Bt2AdminCountRowOut,
    Bt2AdminDsrDayOut,
    Bt2AdminDsrAuditRowOut,
    Bt2AdminDsrDaySummaryOut,
    Bt2AdminDsrRangeOut,
    Bt2AdminDsrRangeTotalsOut,
    Bt2AdminFase1OperationalSummaryOut,
    Bt2AdminF2PoolMetricsOut,
    Bt2AdminMonitorResultadosOut,
    Bt2AdminBacktestReplayOut,
    Bt2AdminOfficialEvaluationLoopOut,
    Bt2AdminRefreshCdmFromSmOut,
    Bt2AdminOfficialPrecisionBucketOut,
    Bt2AdminPoolCoverageOut,
    Bt2AdminScoreBucketOut,
    Bt2AdminVaultPickDistributionOut,
    Bt2AdminVaultRegenerateSnapshotOut,
    Bt2BehavioralMetricsOut,
    Bt2MetaOut,
    Bt2SessionDayOut,
    Bt2VaultPickOut,
    Bt2VaultPicksPageOut,
    DiagnosticIn,
    DiagnosticOut,
    OperatingDaySummaryOut,
    VaultPremiumUnlockIn,
    VaultPremiumUnlockOut,
    VaultPickCommitmentIn,
    VaultPickCommitmentOut,
    VaultStandardUnlockIn,
    VaultStandardUnlockOut,
)
from apps.api.bt2_admin_backtest_replay import build_backtest_replay_payload
from apps.api.bt2_monitor_resultados import build_monitor_resultados_payload
from apps.api.bt2_admin_fase1_summary import build_fase1_operational_summary
from apps.api.bt2_f2_metrics import build_f2_pool_eligibility_metrics
from apps.api.bt2_admin_refresh_cdm_from_sm import (
    admin_refresh_cdm_from_sm_for_daily_pick_day_range,
    admin_refresh_cdm_from_sm_for_operating_day,
)
from apps.api.bt2_official_evaluation_job import fetch_official_evaluation_loop_metrics
from apps.api.bt2_dev_sm_refresh import refresh_raw_sportmonks_for_value_pool_today
from apps.api.bt2_sfs_cdm_ingest import run_sfs_auto_ingest_after_cdm_fetch
from apps.api.bt2_settings import bt2_settings
from apps.api.bt2_vault_market_mix import order_indices_for_top_slate_diversity
from apps.api.bt2_pick_signal_dimensions import (
    assign_predictive_tier,
    assign_standard_premium_access,
    compute_row_signal_fields,
    league_eligible_for_snapshot,
    prob_coherence_flag_for_agg,
    strength_score,
)
from apps.api.bt2_vault_pool import (
    VAULT_POOL_HARD_CAP,
    VAULT_POOL_TARGET,
    VAULT_VALUE_POOL_UNIVERSE_MAX,
    compose_vault_daily_picks,
    is_event_available_for_pick_strict,
    is_event_unlockable_for_vault,
    kickoff_utc_to_time_band,
)
from apps.api.deps import Bt2UserId

router = APIRouter(prefix="/bt2", tags=["bt2"])
logger = logging.getLogger("bt2_router")

# Penalizaciones DP: el débito no puede dejar saldo negativo (carga parcial hasta 0).
_DP_PENALTY_REASONS = frozenset(
    {REASON_PENALTY_STATION_UNCLOSED, REASON_PENALTY_UNSETTLED_PICKS},
)

_VAULT_HARD_EMPTY_MESSAGE_ES = (
    "No hay eventos elegibles hoy según los umbrales del protocolo (mercados completos en CDM y cuota mínima). "
    "Si acabas de abrir la estación, revisa más tarde o la ingesta de datos."
)
_VAULT_FALLBACK_DISCLAIMER_ES = (
    "No hubo suficiente valor para el criterio del modelo estadístico; se muestran opciones reales del CDM "
    "con criterio alternativo. La selección puede estar sesgada por los datos limitados del día."
)


def _vault_suggested_ml_display(
    *,
    model_market_canonical: Optional[str],
    model_selection_canonical: Optional[str],
    home_team: str,
    away_team: str,
    odds_home: float,
    odds_draw: float,
    odds_away: float,
) -> Tuple[str, str, float]:
    """
    Cuota + selección visibles en bóveda para 1X2.

    Antes se usaba max(home, draw, away): eso mostraba la cuota **más alta** (típ. underdog)
    aunque Vektor/DSR hubiera razonado el **favorito**, generando contradicción narrativa vs línea.
    Si hay mercado/selección canónicos FT_1X2, alineamos con ese lado.
    """
    mmc = (model_market_canonical or "").strip().upper()
    msc = (model_selection_canonical or "").strip().lower()
    if mmc == "FT_1X2" and msc in ("home", "draw", "away"):
        if msc == "home" and odds_home > 1.0:
            return ("ML_SIDE", f"Victoria {home_team}", odds_home)
        if msc == "away" and odds_away > 1.0:
            return ("ML_AWAY", f"Victoria {away_team}", odds_away)
        if msc == "draw" and odds_draw > 1.0:
            return ("ML_SIDE", "Empate", odds_draw)

    best_odds = max(odds_home, odds_draw, odds_away)
    if best_odds > 1.0:
        if odds_home == best_odds:
            return ("ML_SIDE", f"Victoria {home_team}", odds_home)
        if odds_away == best_odds:
            return ("ML_AWAY", f"Victoria {away_team}", odds_away)
        return ("ML_SIDE", "Empate", odds_draw)
    return ("ML_SIDE", f"{home_team} vs {away_team}", 2.0)


def _vault_line_from_consensus_or_ml(
    *,
    agg: Optional[Any],
    model_market_canonical: Optional[str],
    model_selection_canonical: Optional[str],
    home_team: str,
    away_team: str,
    odds_home: float,
    odds_draw: float,
    odds_away: float,
) -> Tuple[str, str, float]:
    """
    Cuota + selección visibles en bóveda: misma mediana `consensus` que DSR (agregación + fusión SFS).
    Sin esto, mercados ≠ FT_1X2 quedaban con línea/cuota del 1X2 (`_vault_suggested_ml_display`).
    """
    mmc = (model_market_canonical or "").strip().upper()
    msc = (model_selection_canonical or "").strip().lower()
    if agg is not None and mmc and mmc != "UNKNOWN" and msc and msc != "unknown_side":
        sub = getattr(agg, "consensus", None) or {}
        if isinstance(sub, dict):
            mc_map = sub.get(mmc)
            if isinstance(mc_map, dict):
                consensus_val = mc_map.get(msc)
                try:
                    co = float(consensus_val) if consensus_val is not None else 0.0
                except (TypeError, ValueError):
                    co = 0.0
                if co > 1.0:
                    sel_es = selection_canonical_summary_es(
                        model_market_canonical,
                        model_selection_canonical,
                        home_team=home_team,
                        away_team=away_team,
                    )
                    if sel_es:
                        return (mmc, sel_es, co)
    return _vault_suggested_ml_display(
        model_market_canonical=model_market_canonical,
        model_selection_canonical=model_selection_canonical,
        home_team=home_team,
        away_team=away_team,
        odds_home=odds_home,
        odds_draw=odds_draw,
        odds_away=odds_away,
    )


# Bono único al completar onboarding fase A (ledger como fuente de verdad; US-FE-011).
ONBOARDING_PHASE_A_DP_GRANT = 250
ONBOARDING_PHASE_A_LEDGER_REASON = "onboarding_phase_a"


# ── Helpers DB sync ───────────────────────────────────────────────────────────

def _db_conn():
    url = bt2_settings.bt2_database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)


# ── Auth schemas ──────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    user_id: str
    display_name: Optional[str] = None


class MeOut(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str]
    created_at: str


# ── Auth endpoints ────────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=TokenOut, status_code=200)
def bt2_register(body: RegisterIn) -> TokenOut:
    from apps.api.bt2_auth import create_jwt, hash_password

    email = body.email.strip().lower()
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM bt2_users WHERE email = %s", (email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email ya registrado")

        pw_hash = hash_password(body.password)
        cur.execute(
            """INSERT INTO bt2_users (email, password_hash, display_name)
               VALUES (%s, %s, %s) RETURNING id, display_name""",
            (email, pw_hash, body.display_name),
        )
        row = cur.fetchone()
        user_id = str(row[0])
        display_name = row[1]
        # US-BE-009 Regla 3: crear bt2_user_settings con defaults automáticamente
        cur.execute(
            """INSERT INTO bt2_user_settings (user_id) VALUES (%s)
               ON CONFLICT (user_id) DO NOTHING""",
            (user_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    token = create_jwt(user_id)
    return TokenOut(access_token=token, user_id=user_id, display_name=display_name)


@router.post("/auth/login", response_model=TokenOut, status_code=200)
def bt2_login(body: LoginIn) -> TokenOut:
    from apps.api.bt2_auth import create_jwt, verify_password

    email = body.email.strip().lower()
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, password_hash, display_name FROM bt2_users WHERE email = %s AND is_active = true",
            (email,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row or not verify_password(body.password, row[1]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    user_id = str(row[0])
    token = create_jwt(user_id)
    return TokenOut(access_token=token, user_id=user_id, display_name=row[2])


@router.get("/auth/me", response_model=MeOut, status_code=200)
def bt2_me(user_id: Bt2UserId) -> MeOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, email, display_name, created_at FROM bt2_users WHERE id = %s::uuid",
            (user_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return MeOut(
        user_id=str(row[0]),
        email=row[1],
        display_name=row[2],
        created_at=row[3].isoformat() if row[3] else "",
    )

_MARKET_LABEL_ES: dict[str, str] = {
    "ML_TOTAL": "Totales (más/menos)",
    "SPREAD_HOME": "Hándicap local",
    "ML_SIDE": "Ganador del partido",
    "TOTAL_UNDER": "Menos de (Under)",
    "PLAYER_PROP": "Prop de jugador",
    "ML_AWAY": "Victoria visitante",
    "TOTAL_OVER": "Más de (Over)",
}

# Coherente con `apps/web/src/data/vaultMockPicks.ts` (mismo orden y valores).
_RAW_PICKS: list[dict] = [
    {
        "id": "v2-p-001",
        "marketClass": "ML_TOTAL",
        "eventLabel": "Atlético Norte vs Rápidos · Jornada 14",
        "titulo": "Sobrecarga ofensiva vs. defensa cansada",
        "suggestedDecimalOdds": 1.87,
        "edgeBps": 120,
        "selectionSummaryEs": "Más de 218.5 puntos",
        "accessTier": "premium",
        "traduccionHumana": (
            "El mercado subestima el ritmo cuando ambos equipos priorizan transición rápida; "
            "tu ventaja es asumir más posesiones efectivas de las que precia el cierre."
        ),
        "curvaEquidad": [0, 0.4, 0.2, 0.9, 1.1, 0.8, 1.4, 1.2, 1.6],
    },
    {
        "id": "v2-p-002",
        "marketClass": "SPREAD_HOME",
        "eventLabel": "Centauros vs Halcones · Jornada 22",
        "titulo": "Local con descanso asimétrico",
        "suggestedDecimalOdds": 1.92,
        "edgeBps": 95,
        "selectionSummaryEs": "Local -4.5 puntos",
        "accessTier": "premium",
        "traduccionHumana": (
            "Condición física y rotación favorecen al local en el tramo final; el spread no "
            "refleja el desgaste acumulado del visitante."
        ),
        "curvaEquidad": [0, -0.1, 0.3, 0.5, 0.4, 0.7, 0.6, 0.9],
    },
    {
        "id": "v2-p-003",
        "marketClass": "ML_SIDE",
        "eventLabel": "Tigres vs Leones · Jornada 8",
        "titulo": "Sesgo de cierre por noticias tardías",
        "suggestedDecimalOdds": 2.10,
        "edgeBps": 140,
        "selectionSummaryEs": "Victoria Leones (visitante)",
        "accessTier": "premium",
        "traduccionHumana": (
            "Ajustes tardíos empujaron el precio hacia el favorito público; el valor queda del "
            "lado opuesto si la tesis previa sigue intacta."
        ),
        "curvaEquidad": [0, 0.2, 0.5, 0.3, 0.8, 1.0, 0.9, 1.3],
    },
    {
        "id": "v2-p-004",
        "marketClass": "TOTAL_UNDER",
        "eventLabel": "Cóndores vs Panteras · Jornada 31",
        "titulo": "Clima y superficie: menos posesiones limpias",
        "suggestedDecimalOdds": 1.95,
        "edgeBps": 88,
        "selectionSummaryEs": "Menos de 42.5 puntos",
        "accessTier": "open",
        "traduccionHumana": (
            "Condiciones que aumentan errores no forzados reducen eficiencia real; el total no "
            "incorpora bien esa fricción."
        ),
        "curvaEquidad": [0, 0.1, 0.15, 0.35, 0.2, 0.45, 0.5],
    },
    {
        "id": "v2-p-005",
        "marketClass": "PLAYER_PROP",
        "eventLabel": "Águilas vs Delfines · Jornada 19",
        "titulo": "Rol ampliado sin repricing",
        "suggestedDecimalOdds": 1.80,
        "edgeBps": 110,
        "selectionSummaryEs": "Jugador 7 — más de 24.5 puntos",
        "accessTier": "open",
        "traduccionHumana": (
            "Minutos y uso creador subieron; la línea sigue anclada al rol anterior. La disciplina "
            "es no sobre-apostar si el precio alcanza fair."
        ),
        "curvaEquidad": [0, -0.2, 0.1, 0.4, 0.2, 0.6, 0.55, 0.7],
    },
    {
        "id": "v2-p-006",
        "marketClass": "ML_AWAY",
        "eventLabel": "Víboras vs Gladiadores · Jornada 5",
        "titulo": "Visitante con matchup de esquemas favorable",
        "suggestedDecimalOdds": 2.25,
        "edgeBps": 72,
        "selectionSummaryEs": "Victoria Gladiadores (visitante)",
        "accessTier": "open",
        "traduccionHumana": (
            "El estilo del visitante explota la cobertura del rival; el mercado pondera más el "
            "factor cancha que el ajuste táctico."
        ),
        "curvaEquidad": [0, 0.05, 0.2, 0.15, 0.35, 0.3, 0.5],
    },
    {
        "id": "v2-p-007",
        "marketClass": "TOTAL_OVER",
        "eventLabel": "Gaviotas vs Tormentas · Jornada 27",
        "titulo": "Ritmo proyectado por árbitros y faltas",
        "suggestedDecimalOdds": 1.89,
        "edgeBps": 99,
        "selectionSummaryEs": "Más de 226.5 puntos",
        "accessTier": "open",
        "traduccionHumana": (
            "Tendencia arbitral a cortar juego interior genera más tiros libres y posesiones "
            "alargadas; el over está infravalorado."
        ),
        "curvaEquidad": [0, 0.2, 0.4, 0.35, 0.55, 0.7, 0.65, 0.85],
    },
]

_UNLOCK_DP_PREMIUM = 50


# ── Helpers CDM ───────────────────────────────────────────────────────────────

def _operating_day_key(tz_name: str = "America/Bogota") -> str:
    """Calcula la fecha del día operativo en la zona horaria del usuario."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz=tz).date().isoformat()


def _fetch_upcoming_events(hours: int, require_active_league: bool = True) -> list[dict]:
    """Lee bt2_events con kickoff en las próximas `hours` horas con odds disponibles."""
    conn = _db_conn()
    cur = conn.cursor()
    try:
        active_filter = "AND l.is_active = true" if require_active_league else ""
        cur.execute(f"""
            SELECT
                e.id, e.kickoff_utc, e.season,
                th.name AS home_team, ta.name AS away_team, l.name AS league,
                MAX(CASE WHEN o.market = 'Match Winner' AND o.selection = 'Home'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_home,
                MAX(CASE WHEN o.market = 'Match Winner' AND o.selection = 'Draw'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_draw,
                MAX(CASE WHEN o.market = 'Match Winner' AND o.selection = 'Away'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_away
            FROM bt2_events e
            JOIN bt2_teams th ON e.home_team_id = th.id
            JOIN bt2_teams ta ON e.away_team_id = ta.id
            JOIN bt2_leagues l ON e.league_id = l.id
            JOIN bt2_odds_snapshot o ON o.event_id = e.id
            WHERE e.kickoff_utc BETWEEN now() AND now() + interval '{hours} hours'
              AND e.status = 'scheduled'
              {active_filter}
            GROUP BY e.id, e.kickoff_utc, e.season, th.name, ta.name, l.name
            ORDER BY e.kickoff_utc
        """)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


# ── Endpoints reales (T-085) ──────────────────────────────────────────────────

@router.get("/meta", response_model=Bt2MetaOut, response_model_by_alias=True)
def bt2_meta() -> Bt2MetaOut:
    import os
    mode = os.getenv("BT2_SETTLEMENT_MODE", "trust")
    dkey = (bt2_settings.deepseek_api_key or "").strip()
    return Bt2MetaOut(
        settlement_verification_mode=cast(Literal["trust", "verified"], mode),
        dsr_enabled=bool(bt2_settings.bt2_dsr_enabled),
        dsr_provider=str(bt2_settings.bt2_dsr_provider or "rules").strip().lower(),
        deepseek_configured=bool(dkey),
        sfs_markets_fusion_enabled=bool(getattr(bt2_settings, "bt2_sfs_markets_fusion_enabled", False)),
    )


@router.get("/session/day", response_model=Bt2SessionDayOut, response_model_by_alias=True)
def bt2_session_day(user_id: Bt2UserId) -> Bt2SessionDayOut:
    tz_name = _user_timezone(user_id)
    odk = _operating_day_key_for_user(user_id)
    conn = _db_conn()
    cur = conn.cursor()
    try:
        # Sesión de hoy
        cur.execute(
            """SELECT status, grace_until_iso FROM bt2_operating_sessions
               WHERE user_id = %s::uuid AND operating_day_key = %s
               ORDER BY station_opened_at DESC LIMIT 1""",
            (user_id, odk),
        )
        today_session = cur.fetchone()

        # Picks pendientes del día anterior
        try:
            prev_d = (date.fromisoformat(odk) - timedelta(days=1)).isoformat()
        except Exception:
            prev_d = odk
        cur.execute(
            """SELECT COUNT(*) FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'
                 AND DATE(opened_at AT TIME ZONE 'UTC') = %s""",
            (user_id, prev_d),
        )
        pending = int(cur.fetchone()[0])
    finally:
        cur.close()
        conn.close()

    station_closed = False
    grace_until = None

    if today_session:
        station_closed = today_session[0] == "closed"
        if today_session[1]:
            grace_until = today_session[1].isoformat()

    return Bt2SessionDayOut(
        operating_day_key=odk,
        user_time_zone=tz_name,
        grace_until_iso=grace_until,
        pending_settlements_previous_day=pending,
        station_closed_for_operating_day=station_closed,
    )


@router.get(
    "/operating-day/summary",
    status_code=200,
    response_model=OperatingDaySummaryOut,
    response_model_by_alias=True,
)
def bt2_operating_day_summary(
    user_id: Bt2UserId,
    operating_day_key: Optional[str] = Query(default=None, alias="operatingDayKey"),
) -> OperatingDaySummaryOut:
    """US-BE-018 — agregados del día operativo (TZ usuario; ventana alineada al snapshot)."""
    tz_name = _user_timezone(user_id)
    odk = operating_day_key or _operating_day_key_for_user(user_id)
    start_utc, end_utc = _day_bounds_utc_for_odk(odk, tz_name)

    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT COUNT(*) FROM bt2_picks
               WHERE user_id = %s::uuid
                 AND opened_at >= %s AND opened_at < %s""",
            (user_id, start_utc, end_utc),
        )
        picks_opened = int(cur.fetchone()[0])

        cur.execute(
            """SELECT
                   COUNT(*) AS n_settled,
                   COUNT(*) FILTER (WHERE status = 'won') AS won,
                   COUNT(*) FILTER (WHERE status = 'lost') AS lost,
                   COUNT(*) FILTER (WHERE status = 'void') AS voided,
                   COALESCE(SUM(stake_units) FILTER (
                       WHERE status IN ('won','lost','void')), 0) AS total_stake,
                   COALESCE(SUM(pnl_units) FILTER (
                       WHERE status IN ('won','lost','void')), 0) AS net_pnl
               FROM bt2_picks
               WHERE user_id = %s::uuid
                 AND settled_at IS NOT NULL
                 AND settled_at >= %s AND settled_at < %s""",
            (user_id, start_utc, end_utc),
        )
        agg = cur.fetchone()

        cur.execute(
            """SELECT COALESCE(SUM(delta_dp), 0) FROM bt2_dp_ledger
               WHERE user_id = %s::uuid AND reason = %s
                 AND created_at >= %s AND created_at < %s""",
            (user_id, REASON_PICK_SETTLE, start_utc, end_utc),
        )
        dp_settle = int(cur.fetchone()[0])

        cur.execute(
            """SELECT COALESCE(SUM(delta_dp), 0) FROM bt2_dp_ledger
               WHERE user_id = %s::uuid AND reason = %s
                 AND created_at >= %s AND created_at < %s""",
            (user_id, REASON_SESSION_CLOSE_DISCIPLINE, start_utc, end_utc),
        )
        dp_session_close = int(cur.fetchone()[0])
    finally:
        cur.close()
        conn.close()

    n_settled = int(agg[0] or 0)
    return OperatingDaySummaryOut(
        operating_day_key=odk,
        user_time_zone=tz_name,
        picks_opened_count=picks_opened,
        picks_settled_count=n_settled,
        won_count=int(agg[1] or 0),
        lost_count=int(agg[2] or 0),
        void_count=int(agg[3] or 0),
        total_stake_units_settled=float(agg[4] or 0),
        net_pnl_units=float(agg[5] or 0),
        dp_earned_from_settlements=dp_settle,
        dp_earned_from_session_close=dp_session_close,
    )


def _kickoff_utc_iso_z(ko: Optional[datetime]) -> str:
    """ISO 8601 UTC con sufijo Z; vacío si no hay instante (US-BE-019)."""
    if ko is None:
        return ""
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    else:
        ko = ko.astimezone(timezone.utc)
    return ko.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_vault_daily_pick_id(vault_pick_id: str) -> int:
    """Acepta `dp-7` o `7` (US-BE-029)."""
    raw = vault_pick_id.strip()
    if raw.lower().startswith("dp-"):
        raw = raw[3:].strip()
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="vaultPickId debe ser el id del snapshot (p. ej. dp-12 o 12).",
        )


@router.post(
    "/vault/premium-unlock",
    status_code=200,
    response_model=VaultPremiumUnlockOut,
    response_model_by_alias=True,
)
def bt2_vault_premium_unlock(
    body: VaultPremiumUnlockIn, user_id: Bt2UserId
) -> VaultPremiumUnlockOut:
    """
    US-BE-029 / D-05.1-002: cobra pick_premium_unlock (−50 DP) sin crear bt2_picks.
    Idempotente: segundo POST mismo ítem/día → 200 sin duplicar ledger.
    """
    dp_id = _parse_vault_daily_pick_id(body.vault_pick_id)
    odk = _operating_day_key_for_user(user_id)
    canonical_id = f"dp-{dp_id}"
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, access_tier FROM bt2_daily_picks
               WHERE id = %s AND user_id = %s::uuid AND operating_day_key = %s""",
            (dp_id, user_id, odk),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Ítem de bóveda no encontrado o no pertenece al snapshot del día",
            )
        if row[1] != "premium":
            raise HTTPException(
                status_code=404,
                detail="El ítem no es premium en el snapshot del día operativo",
            )

        cur.execute(
            """SELECT 1 FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND daily_pick_id = %s""",
            (user_id, dp_id),
        )
        if cur.fetchone():
            conn.commit()
            return VaultPremiumUnlockOut(
                vault_pick_id=canonical_id,
                premium_unlocked=True,
                dp_balance_after=_get_dp_balance(cur, user_id),
            )

        cur.execute(
            """SELECT e.kickoff_utc, e.status FROM bt2_events e
               INNER JOIN bt2_daily_picks dp ON dp.event_id = e.id
               WHERE dp.id = %s AND dp.user_id = %s::uuid AND dp.operating_day_key = %s""",
            (dp_id, user_id, odk),
        )
        evk = cur.fetchone()
        if evk:
            now_pick = datetime.now(timezone.utc)
            if not is_event_unlockable_for_vault(
                event_status=str(evk[1] or ""),
                kickoff_utc=evk[0],
                now_utc=now_pick,
            ):
                raise HTTPException(
                    status_code=422,
                    detail="El evento ya no admite liberación (kickoff pasado o estado final).",
                )

        cur.execute(
            """SELECT COUNT(*)::int AS n FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        n_prem = int(cur.fetchone()[0])
        cur.execute(
            """SELECT COUNT(*)::int AS n FROM bt2_vault_standard_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        n_std = int(cur.fetchone()[0])
        if n_prem >= VAULT_DAILY_UNLOCK_CAP_PREMIUM:
            conn.rollback()
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Ya alcanzaste el máximo de {VAULT_DAILY_UNLOCK_CAP_PREMIUM} "
                    "señales premium liberadas hoy (día operativo)."
                ),
            )
        if n_std + n_prem >= VAULT_DAILY_UNLOCK_CAP_TOTAL:
            conn.rollback()
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Ya liberaste el máximo de {VAULT_DAILY_UNLOCK_CAP_TOTAL} picks "
                    "hoy; no puedes desbloquear más aunque tengas DP."
                ),
            )

        bal_raw = _get_dp_ledger_sum(cur, user_id)
        if bal_raw < DP_PREMIUM_UNLOCK_COST:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": BT2_ERR_DP_INSUFFICIENT_PREMIUM,
                    "message": (
                        "Saldo de Discipline Points insuficiente para desbloquear la señal premium "
                        f"del día (se requieren {DP_PREMIUM_UNLOCK_COST} DP)."
                    ),
                    "requiredDp": DP_PREMIUM_UNLOCK_COST,
                    "currentDp": max(0, bal_raw),
                },
            )

        cur.execute(
            """INSERT INTO bt2_vault_premium_unlocks (user_id, daily_pick_id, operating_day_key)
               VALUES (%s::uuid, %s, %s)""",
            (user_id, dp_id, odk),
        )
        _append_dp_ledger_move(
            cur,
            user_id,
            -DP_PREMIUM_UNLOCK_COST,
            REASON_PICK_PREMIUM_UNLOCK,
            None,
        )
        logger.info(
            "vault_premium_unlock: user=%s daily_pick_id=%s delta_dp=-%s (US-BE-029, sin bt2_picks)",
            user_id,
            dp_id,
            DP_PREMIUM_UNLOCK_COST,
        )
        conn.commit()
        return VaultPremiumUnlockOut(
            vault_pick_id=canonical_id,
            premium_unlocked=True,
            dp_balance_after=_get_dp_balance(cur, user_id),
        )
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@router.post(
    "/vault/standard-unlock",
    status_code=200,
    response_model=VaultStandardUnlockOut,
    response_model_by_alias=True,
)
def bt2_vault_standard_unlock(
    body: VaultStandardUnlockIn, user_id: Bt2UserId,
) -> VaultStandardUnlockOut:
    """Libera ítem estándar sin DP; topes diarios acotados en servidor."""
    dp_id = _parse_vault_daily_pick_id(body.vault_pick_id)
    odk = _operating_day_key_for_user(user_id)
    canonical_id = f"dp-{dp_id}"
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, access_tier FROM bt2_daily_picks
               WHERE id = %s AND user_id = %s::uuid AND operating_day_key = %s""",
            (dp_id, user_id, odk),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Ítem de bóveda no encontrado o no pertenece al snapshot del día",
            )
        if row[1] != "standard":
            raise HTTPException(
                status_code=404,
                detail="El ítem no es estándar en el snapshot del día operativo",
            )

        cur.execute(
            """SELECT 1 FROM bt2_vault_standard_unlocks
               WHERE user_id = %s::uuid AND daily_pick_id = %s""",
            (user_id, dp_id),
        )
        if cur.fetchone():
            conn.commit()
            return VaultStandardUnlockOut(
                vault_pick_id=canonical_id,
                standard_unlocked=True,
            )

        cur.execute(
            """SELECT e.kickoff_utc, e.status FROM bt2_events e
               INNER JOIN bt2_daily_picks dp ON dp.event_id = e.id
               WHERE dp.id = %s AND dp.user_id = %s::uuid AND dp.operating_day_key = %s""",
            (dp_id, user_id, odk),
        )
        evk = cur.fetchone()
        if evk:
            now_pick = datetime.now(timezone.utc)
            if not is_event_unlockable_for_vault(
                event_status=str(evk[1] or ""),
                kickoff_utc=evk[0],
                now_utc=now_pick,
            ):
                raise HTTPException(
                    status_code=422,
                    detail="El evento ya no admite liberación (kickoff pasado o estado final).",
                )

        cur.execute(
            """SELECT COUNT(*)::int AS n FROM bt2_vault_standard_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        n_std = int(cur.fetchone()[0])
        cur.execute(
            """SELECT COUNT(*)::int AS n FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        n_prem = int(cur.fetchone()[0])
        if n_std >= VAULT_DAILY_UNLOCK_CAP_STANDARD:
            conn.rollback()
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Ya liberaste el máximo de {VAULT_DAILY_UNLOCK_CAP_STANDARD} "
                    "señales estándar hoy."
                ),
            )
        if n_std + n_prem >= VAULT_DAILY_UNLOCK_CAP_TOTAL:
            conn.rollback()
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Ya liberaste el máximo de {VAULT_DAILY_UNLOCK_CAP_TOTAL} picks "
                    "hoy."
                ),
            )

        cur.execute(
            """INSERT INTO bt2_vault_standard_unlocks (user_id, daily_pick_id, operating_day_key)
               VALUES (%s::uuid, %s, %s)""",
            (user_id, dp_id, odk),
        )
        conn.commit()
        return VaultStandardUnlockOut(
            vault_pick_id=canonical_id,
            standard_unlocked=True,
        )
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@router.post(
    "/vault/pick-commitment",
    status_code=200,
    response_model=VaultPickCommitmentOut,
    response_model_by_alias=True,
)
def bt2_vault_pick_commitment_route(
    body: VaultPickCommitmentIn, user_id: Bt2UserId,
) -> VaultPickCommitmentOut:
    """Marcación manual tomó / no tomó (pick ya liberado)."""
    dp_id = _parse_vault_daily_pick_id(body.vault_pick_id)
    odk = _operating_day_key_for_user(user_id)
    canonical_id = f"dp-{dp_id}"
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT dp.event_id, dp.access_tier FROM bt2_daily_picks dp
               WHERE dp.id = %s AND dp.user_id = %s::uuid AND dp.operating_day_key = %s""",
            (dp_id, user_id, odk),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Ítem de bóveda no encontrado o no pertenece al snapshot del día",
            )
        ev_id = int(row[0])
        tier = row[1]
        unlocked = False
        if tier == "premium":
            cur.execute(
                """SELECT 1 FROM bt2_vault_premium_unlocks
                   WHERE user_id = %s::uuid AND daily_pick_id = %s""",
                (user_id, dp_id),
            )
            unlocked = cur.fetchone() is not None
        else:
            cur.execute(
                """SELECT 1 FROM bt2_vault_standard_unlocks
                   WHERE user_id = %s::uuid AND daily_pick_id = %s""",
                (user_id, dp_id),
            )
            unlocked = cur.fetchone() is not None
        if not unlocked:
            cur.execute(
                """SELECT 1 FROM bt2_picks
                   WHERE user_id = %s::uuid AND event_id = %s AND status = 'open'""",
                (user_id, ev_id),
            )
            unlocked = cur.fetchone() is not None
        if not unlocked:
            raise HTTPException(
                status_code=422,
                detail="Debes liberar el pick antes de indicar si lo tomaste.",
            )

        cur.execute(
            """INSERT INTO bt2_vault_pick_commitment
               (user_id, daily_pick_id, operating_day_key, commitment)
               VALUES (%s::uuid, %s, %s, %s)
               ON CONFLICT (user_id, daily_pick_id)
               DO UPDATE SET commitment = EXCLUDED.commitment,
                             committed_at = now()""",
            (user_id, dp_id, odk, body.commitment),
        )
        conn.commit()
        return VaultPickCommitmentOut(
            vault_pick_id=canonical_id,
            commitment=body.commitment,
        )
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _vault_redact_pick_preview(pick: Bt2VaultPickOut) -> Bt2VaultPickOut:
    """Vista previa Disponibles: oculta selección/cuota/racional (servidor autoritativo)."""
    return pick.model_copy(
        update={
            "selection_summary_es": "",
            "suggested_decimal_odds": 0.0,
            "traduccion_humana": "",
            "dsr_narrative_es": "",
            "curva_equidad": [0.0],
            "edge_bps": 0,
            "estimated_hit_probability": None,
            "evidence_quality": None,
            "predictive_tier": None,
            "action_tier": None,
        }
    )


def _build_bt2_vault_picks_page_out(user_id: str) -> Bt2VaultPicksPageOut:
    """Un solo barrido DB: todos los picks persistidos del día (hasta 20), sin LIMIT."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_utc_dt = datetime.now(timezone.utc)
    odk = _operating_day_key_for_user(user_id)
    tz_name = _user_timezone(user_id)
    try:
        from zoneinfo import ZoneInfo

        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.utc

    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                dp.id           AS dp_id,
                dp.access_tier,
                dp.suggested_at,
                dp.pipeline_version,
                dp.dsr_narrative_es,
                dp.dsr_confidence_label,
                dp.dsr_source,
                dp.model_market_canonical,
                dp.model_selection_canonical,
                dp.data_completeness_score,
                dp.slate_rank,
                dp.estimated_hit_probability,
                dp.evidence_quality,
                dp.predictive_tier,
                dp.action_tier,
                e.id            AS event_id,
                e.status        AS event_status,
                e.kickoff_utc,
                e.result_home,
                e.result_away,
                ht.name         AS home_team,
                at2.name        AS away_team,
                l.name          AS league_name,
                l.tier          AS league_tier,
                -- Mejor odd Home (1X2 / Match Winner / Full Time Result)
                (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
                 WHERE o.event_id = e.id
                   AND lower(o.market) IN ('1x2', 'match winner', 'full time result', 'fulltime result')
                   AND (o.selection IN ('1', 'Home') OR lower(o.selection) LIKE '%%home%%')
                ) AS odds_home,
                (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
                 WHERE o.event_id = e.id
                   AND lower(o.market) IN ('1x2', 'match winner', 'full time result', 'fulltime result')
                   AND (o.selection IN ('X', 'Draw') OR lower(o.selection) LIKE '%%draw%%')
                ) AS odds_draw,
                (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
                 WHERE o.event_id = e.id
                   AND lower(o.market) IN ('1x2', 'match winner', 'full time result', 'fulltime result')
                   AND (o.selection IN ('2', 'Away') OR lower(o.selection) LIKE '%%away%%')
                ) AS odds_away
            FROM bt2_daily_picks dp
            JOIN bt2_events e ON e.id = dp.event_id
            JOIN bt2_leagues l ON l.id = e.league_id
            LEFT JOIN bt2_teams ht ON ht.id = e.home_team_id
            LEFT JOIN bt2_teams at2 ON at2.id = e.away_team_id
            WHERE dp.user_id = %s::uuid
              AND dp.operating_day_key = %s
            ORDER BY
                dp.slate_rank ASC,
                CASE dp.access_tier WHEN 'standard' THEN 1 ELSE 2 END,
                dp.suggested_at ASC
        """,
            (user_id, odk),
        )
        rows = cur.fetchall()

        agg_by_eid: dict[int, Any] = {}
        if rows:
            seen_ev: set[int] = set()
            for _r in rows:
                _eid = int(_r["event_id"])
                if _eid in seen_ev:
                    continue
                seen_ev.add(_eid)
                _agg, _ = aggregated_odds_for_event_psycopg(
                    cur,
                    _eid,
                    min_decimal=MIN_ODDS_DECIMAL_DEFAULT,
                )
                agg_by_eid[_eid] = _agg

        cur.execute(
            """SELECT daily_pick_id FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        unlocked_dp_ids = {int(r["daily_pick_id"]) for r in cur.fetchall()}
        cur.execute(
            """SELECT daily_pick_id FROM bt2_vault_standard_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        standard_unlocked_dp_ids = {int(r["daily_pick_id"]) for r in cur.fetchall()}
        cur.execute(
            """SELECT daily_pick_id, commitment FROM bt2_vault_pick_commitment
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        commitment_by_dp: dict[int, str] = {
            int(r["daily_pick_id"]): str(r["commitment"])
            for r in cur.fetchall()
        }
        cur.execute(
            """SELECT DISTINCT event_id FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'""",
            (user_id,),
        )
        legacy_open_event_ids = {int(r["event_id"]) for r in cur.fetchall()}
        cur.execute(
            """
            SELECT dsr_signal_degraded, limited_coverage, operational_empty_hard,
                   vault_empty_message_es, fallback_disclaimer_es,
                   future_events_in_window_count, fallback_eligible_pool_count,
                   COALESCE(slate_band_cycle, 0) AS slate_band_cycle
            FROM bt2_vault_day_metadata
            WHERE user_id = %s::uuid AND operating_day_key = %s
            """,
            (user_id, odk),
        )
        meta_row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    free_unlocks_today = len(standard_unlocked_dp_ids)
    premium_unlocks_today = len(unlocked_dp_ids)
    total_unlocks_today = free_unlocks_today + premium_unlocks_today

    vm = meta_row or {}
    vm_degraded = bool(vm.get("dsr_signal_degraded"))
    vm_limited = bool(vm.get("limited_coverage"))
    vm_hard = bool(vm.get("operational_empty_hard"))
    vm_empty_msg = vm.get("vault_empty_message_es")
    vm_disc = vm.get("fallback_disclaimer_es")
    vm_fec = int(vm.get("future_events_in_window_count") or 0)
    vm_pool = int(vm.get("fallback_eligible_pool_count") or 0)
    vm_slate_cycle = int(vm.get("slate_band_cycle") or 0)

    if not rows:
        empty_msg = (
            "No hay ítems en la bóveda para hoy. Si aún no abriste la estación, hacelo para generar el snapshot."
        )
        if vm_hard:
            empty_msg = str(vm_empty_msg or _VAULT_HARD_EMPTY_MESSAGE_ES)
        return Bt2VaultPicksPageOut(
            picks=[],
            generated_at_utc=now,
            message=empty_msg,
            pool_item_count=0,
            pool_below_target=True,
            vault_universe_persisted_count=0,
            slate_band_cycle=vm_slate_cycle,
            dsr_signal_degraded=vm_degraded,
            limited_coverage=vm_limited,
            operational_empty_hard=vm_hard,
            vault_operational_message_es=str(vm_empty_msg) if vm_empty_msg else None,
            fallback_disclaimer_es=str(vm_disc) if vm_disc else None,
            future_events_in_window_count=vm_fec,
            fallback_eligible_pool_count=vm_pool,
            free_picks_unlocked_today=free_unlocks_today,
            premium_picks_unlocked_today=premium_unlocks_today,
            total_picks_unlocked_today=total_unlocks_today,
        )

    picks: list[Bt2VaultPickOut] = []
    for row in rows:
        home_team = row["home_team"] or "Local"
        away_team = row["away_team"] or "Visitante"
        league_name = row["league_name"] or "Liga"
        kickoff = row["kickoff_utc"]
        event_status_raw = row["event_status"]
        event_status_str = event_status_raw if event_status_raw is not None else ""
        time_band = kickoff_utc_to_time_band(kickoff, user_tz)
        is_available = is_event_available_for_pick_strict(
            event_status=str(event_status_raw or ""),
            kickoff_utc=kickoff,
            now_utc=now_utc_dt,
        )
        unlock_eligible = is_event_unlockable_for_vault(
            event_status=str(event_status_raw or ""),
            kickoff_utc=kickoff,
            now_utc=now_utc_dt,
        )
        kickoff_iso = _kickoff_utc_iso_z(kickoff)

        odds_home = float(row["odds_home"] or 0.0)
        odds_draw = float(row["odds_draw"] or 0.0)
        odds_away = float(row["odds_away"] or 0.0)
        ev_id = int(row["event_id"])
        mmc_row = row.get("model_market_canonical")
        msc_row = row.get("model_selection_canonical")
        mc, selection, odds_val = _vault_line_from_consensus_or_ml(
            agg=agg_by_eid.get(ev_id),
            model_market_canonical=str(mmc_row) if mmc_row is not None else None,
            model_selection_canonical=str(msc_row) if msc_row is not None else None,
            home_team=home_team,
            away_team=away_team,
            odds_home=odds_home,
            odds_draw=odds_draw,
            odds_away=odds_away,
        )

        # URL de búsqueda externa
        kickoff_date = kickoff.strftime("%Y-%m-%d") if kickoff else odk
        search_q = f"{home_team}+vs+{away_team}+{kickoff_date}".replace(" ", "+")
        external_url = f"https://www.google.com/search?q={search_q}"

        titulo = f"{league_name} · {kickoff.strftime('%d/%m') if kickoff else odk}"
        tier_label = row["access_tier"]  # "standard" | "premium"
        dp_id = int(row["dp_id"])
        premium_unlocked = False
        standard_unlocked = False
        if tier_label == "premium":
            premium_unlocked = dp_id in unlocked_dp_ids or ev_id in legacy_open_event_ids
        if tier_label == "standard":
            standard_unlocked = dp_id in standard_unlocked_dp_ids or ev_id in legacy_open_event_ids
        content_unlocked = (
            premium_unlocked if tier_label == "premium" else standard_unlocked
        )
        uc_raw = commitment_by_dp.get(dp_id)
        user_pick_commitment: Optional[Literal["taken", "not_taken"]] = None
        if uc_raw == "taken":
            user_pick_commitment = "taken"
        elif uc_raw == "not_taken":
            user_pick_commitment = "not_taken"

        mmc = str(mmc_row or "") if mmc_row is not None else ""
        msc = str(msc_row or "") if msc_row is not None else ""
        mcl_es = market_canonical_label_es(mmc or None)
        dsr_narr = (row.get("dsr_narrative_es") or "").strip()
        # Misma cadena que `dsr_narrative_es` si existe; si no, vacío (el FE usa `modelWhyReading`).
        trad_human = dsr_narr
        pipe_v = str(row.get("pipeline_version") or PIPELINE_VERSION_DEFAULT)
        dsr_src = str(row.get("dsr_source") or "rules_fallback")
        dsr_conf = str(row.get("dsr_confidence_label") or "")
        raw_ehp = row.get("estimated_hit_probability")
        try:
            est_hit_f = float(raw_ehp) if raw_ehp is not None else None
        except (TypeError, ValueError):
            est_hit_f = None
        if est_hit_f is None:
            est_hit_f = 0.5
        ev_q_out = (row.get("evidence_quality") or "").strip().lower()
        pred_out = (row.get("predictive_tier") or "").strip().lower()
        act_out = (row.get("action_tier") or "").strip().lower()
        conf_l = (dsr_conf or "low").strip().lower()
        if conf_l not in ("high", "medium", "low"):
            conf_l = "low"
        if ev_q_out not in ("high", "medium", "low"):
            ev_q_out = conf_l
        if pred_out not in ("high", "medium", "low"):
            pred_out = conf_l
        if act_out not in ("free", "premium"):
            act_out = "free" if tier_label == "standard" else "premium"

        pick_row = Bt2VaultPickOut(
            id=f"dp-{dp_id}",
            event_id=ev_id,
            market_class=mc,
            market_label_es=(
                mcl_es if mmc and mmc != "UNKNOWN" else _MARKET_LABEL_ES.get(mc, mc)
            ),
            event_label=f"{home_team} vs {away_team}",
            titulo=titulo,
            suggested_decimal_odds=round(float(odds_val), 2),
            edge_bps=0,
            selection_summary_es=selection,
            traduccion_humana=trad_human,
            curva_equidad=[0.0],
            access_tier=tier_label,
            unlock_cost_dp=0 if tier_label == "standard" else _UNLOCK_DP_PREMIUM,
            operating_day_key=odk,
            is_available=is_available,
            unlock_eligible=unlock_eligible,
            kickoff_utc=kickoff_iso,
            event_status=event_status_str,
            external_search_url=external_url,
            premium_unlocked=premium_unlocked,
            standard_unlocked=standard_unlocked,
            content_unlocked=content_unlocked,
            user_pick_commitment=user_pick_commitment,
            time_band=time_band,
            pipeline_version=pipe_v,
            dsr_narrative_es=dsr_narr,
            dsr_confidence_label=dsr_conf,
            estimated_hit_probability=est_hit_f,
            evidence_quality=ev_q_out,
            predictive_tier=pred_out,
            action_tier=act_out,
            dsr_source=dsr_src,
            market_canonical=mmc or "UNKNOWN",
            market_canonical_label_es=mcl_es,
            model_market_canonical=mmc,
            model_selection_canonical=msc,
            data_completeness_score=(
                int(row["data_completeness_score"])
                if row.get("data_completeness_score") is not None
                else None
            ),
            slate_rank=(
                int(row["slate_rank"])
                if row.get("slate_rank") is not None
                else None
            ),
        )
        if not content_unlocked:
            pick_row = _vault_redact_pick_preview(pick_row)
        picks.append(pick_row)

    n = len(picks)
    page_msg: Optional[str] = None
    if vm_disc:
        page_msg = str(vm_disc)
    return Bt2VaultPicksPageOut(
        picks=picks,
        generated_at_utc=now,
        message=page_msg,
        pool_item_count=n,
        pool_below_target=n < VAULT_POOL_TARGET,
        vault_universe_persisted_count=n,
        slate_band_cycle=vm_slate_cycle,
        dsr_signal_degraded=vm_degraded,
        limited_coverage=vm_limited,
        operational_empty_hard=vm_hard,
        vault_operational_message_es=str(vm_empty_msg) if vm_empty_msg else None,
        fallback_disclaimer_es=str(vm_disc) if vm_disc else None,
        future_events_in_window_count=vm_fec,
        fallback_eligible_pool_count=vm_pool,
        free_picks_unlocked_today=free_unlocks_today,
        premium_picks_unlocked_today=premium_unlocks_today,
        total_picks_unlocked_today=total_unlocks_today,
    )


@router.get("/vault/picks", response_model=Bt2VaultPicksPageOut, response_model_by_alias=True)
def bt2_vault_picks(user_id: Bt2UserId) -> Bt2VaultPicksPageOut:
    return _build_bt2_vault_picks_page_out(user_id)


@router.get("/metrics/behavioral", response_model=Bt2BehavioralMetricsOut, response_model_by_alias=True)
def bt2_behavioral_metrics(user_id: Bt2UserId) -> Bt2BehavioralMetricsOut:
    return Bt2BehavioralMetricsOut(
        roi_pct=4.2,
        roi_human_es=(
            "Crecimiento sostenible: por cada 100 COP invertidos, el sistema genera "
            "4.2 COP de ganancia limpia (demo)."
        ),
        max_drawdown_units=3.5,
        max_drawdown_human_es=(
            "Control de daños: tu peor racha costó 3.5 unidades; el capital principal "
            "sigue protegido si respetaste el protocolo (demo)."
        ),
        behavioral_block_count=2,
        estimated_loss_avoided_cop=180_000.0,
        behavioral_human_es=(
            "Intervenciones de protección: el sistema pausó 2 impulsos y evitó una pérdida "
            "estimada de 180000 COP (demo)."
        ),
        hit_rate_pct=58.0,
        hit_rate_human_es=(
            "Constancia: aciertas 6 de cada 10 análisis; tu disciplina habilita mejores "
            "recomendaciones (demo)."
        ),
    )


# ── Endpoints nuevos (T-086) ──────────────────────────────────────────────────

class UpcomingEventOut(BaseModel):
    event_id: int
    league: str
    home_team: str
    away_team: str
    kickoff_utc: str
    odds_1x2: dict


class BankrollIn(BaseModel):
    amount: float
    currency: str


class BankrollOut(BaseModel):
    user_id: str
    bankroll_amount: Optional[float]
    bankroll_currency: Optional[str]


class ProfileOut(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str]
    bankroll_amount: Optional[float]
    bankroll_currency: Optional[str]
    created_at: str


@router.get("/events/upcoming", response_model=list[UpcomingEventOut])
def bt2_events_upcoming(user_id: Bt2UserId, hours: int = 48) -> list[UpcomingEventOut]:
    events = _fetch_upcoming_events(hours=hours, require_active_league=False)
    out = []
    for ev in events:
        out.append(
            UpcomingEventOut(
                event_id=ev["id"],
                league=ev["league"],
                home_team=ev["home_team"],
                away_team=ev["away_team"],
                kickoff_utc=ev["kickoff_utc"].isoformat() if ev["kickoff_utc"] else "",
                odds_1x2={
                    "home": ev.get("odds_home"),
                    "draw": ev.get("odds_draw"),
                    "away": ev.get("odds_away"),
                },
            )
        )
    return out


@router.post("/user/bankroll", response_model=BankrollOut)
def bt2_set_bankroll(body: BankrollIn, user_id: Bt2UserId) -> BankrollOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """UPDATE bt2_users
               SET bankroll_amount = %s, bankroll_currency = %s
               WHERE id = %s::uuid
               RETURNING id, bankroll_amount, bankroll_currency""",
            (body.amount, body.currency.upper()[:10], user_id),
        )
        row = cur.fetchone()
        conn.commit()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    finally:
        cur.close()
        conn.close()

    return BankrollOut(
        user_id=str(row[0]),
        bankroll_amount=float(row[1]) if row[1] is not None else None,
        bankroll_currency=row[2],
    )


@router.get("/user/profile", response_model=ProfileOut)
def bt2_user_profile(user_id: Bt2UserId) -> ProfileOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, email, display_name, bankroll_amount, bankroll_currency, created_at
               FROM bt2_users WHERE id = %s::uuid""",
            (user_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return ProfileOut(
        user_id=str(row[0]),
        email=row[1],
        display_name=row[2],
        bankroll_amount=float(row[3]) if row[3] is not None else None,
        bankroll_currency=row[4],
        created_at=row[5].isoformat() if row[5] else "",
    )


# ── Helpers dominio conductual ────────────────────────────────────────────────


def _normalize_bt2_user_uuid_param(raw: str) -> str:
    """
    Acepta UUID puro o el sufijo erróneo `_BT2` que a veces se copia desde la UI.
    """
    s = (raw or "").strip()
    if len(s) >= 5 and s.lower().endswith("_bt2"):
        s = s[:-4]
    try:
        return str(uuid.UUID(s))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "userId debe ser un UUID válido de bt2_users (36 caracteres con guiones), "
                "p. ej. b42d899a-8ec0-40ec-a9b9-674a5fe8f2d1. No añadas sufijos como _BT2."
            ),
        )


def _user_timezone(user_id: str) -> str:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT timezone FROM bt2_user_settings WHERE user_id = %s::uuid",
            (user_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    return row[0] if row else "America/Bogota"


def _operating_day_key_for_user(user_id: str) -> str:
    tz_name = _user_timezone(user_id)
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz=tz).date().isoformat()


def _get_dp_balance(cur, user_id: str) -> int:
    cur.execute(
        "SELECT COALESCE(SUM(delta_dp), 0) FROM bt2_dp_ledger WHERE user_id = %s::uuid",
        (user_id,),
    )
    return max(0, int(cur.fetchone()[0]))


def _get_dp_ledger_sum(cur, user_id: str) -> int:
    """Suma real de delta_dp (sin clamp); para cargos y balance_after_dp."""
    cur.execute(
        "SELECT COALESCE(SUM(delta_dp), 0) FROM bt2_dp_ledger WHERE user_id = %s::uuid",
        (user_id,),
    )
    return int(cur.fetchone()[0])


def _ledger_move_exists(cur, user_id: str, reason: str, reference_id: int) -> bool:
    cur.execute(
        """SELECT 1 FROM bt2_dp_ledger
           WHERE user_id = %s::uuid AND reason = %s AND reference_id = %s
           LIMIT 1""",
        (user_id, reason, reference_id),
    )
    return cur.fetchone() is not None


def _append_dp_ledger_move(
    cur, user_id: str, delta_dp: int, reason: str, reference_id: Optional[int]
) -> int:
    """Inserta movimiento; balance_after_dp = suma acumulada tras este delta."""
    raw = _get_dp_ledger_sum(cur, user_id)
    actual_delta = delta_dp
    if delta_dp < 0 and reason in _DP_PENALTY_REASONS:
        debt = -delta_dp
        take = min(debt, max(0, raw))
        actual_delta = -take
    new_raw = raw + actual_delta
    cur.execute(
        """INSERT INTO bt2_dp_ledger (user_id, delta_dp, reason, reference_id, balance_after_dp)
           VALUES (%s::uuid, %s, %s, %s, %s)""",
        (user_id, actual_delta, reason, reference_id, new_raw),
    )
    return new_raw


def _day_bounds_utc_for_odk(odk: str, tz_name: str) -> Tuple[datetime, datetime]:
    """Ventana [start, end) en UTC para operating_day_key en TZ del usuario."""
    try:
        d = date.fromisoformat(odk)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="operatingDayKey debe ser una fecha YYYY-MM-DD válida",
        )
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    start_local = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = start_utc + timedelta(hours=24)
    return start_utc, end_utc


def _close_orphan_sessions_and_station_penalties(
    cur, user_id: str, odk: str, now: datetime, tz_name: str
) -> None:
    """
    Sesiones con operating_day_key < odk aún abiertas → cierre automático.

    Penalización −50 solo si hubo al menos un pick registrado (`bt2_picks`) en ese día
    operativo (TZ usuario). Abrir la estación sin tomar picks no genera cargo.
    Idempotente por reason + reference_id. D-05-002 / US-BE-017 (recalibrado).
    """
    cur.execute(
        """SELECT id, operating_day_key FROM bt2_operating_sessions
           WHERE user_id = %s::uuid AND status = 'open' AND operating_day_key < %s
           ORDER BY operating_day_key ASC""",
        (user_id, odk),
    )
    for orphan_id, orphan_odk in cur.fetchall():
        cur.execute(
            """UPDATE bt2_operating_sessions
               SET status = 'closed', station_closed_at = %s, grace_until_iso = %s
               WHERE id = %s AND user_id = %s::uuid AND status = 'open'""",
            (now, now + timedelta(hours=24), orphan_id, user_id),
        )
        if _ledger_move_exists(cur, user_id, REASON_PENALTY_STATION_UNCLOSED, orphan_id):
            continue
        day_start, day_end = _day_bounds_utc_for_odk(str(orphan_odk), tz_name)
        cur.execute(
            """SELECT 1 FROM bt2_picks
               WHERE user_id = %s::uuid AND opened_at >= %s AND opened_at < %s
               LIMIT 1""",
            (user_id, day_start, day_end),
        )
        if not cur.fetchone():
            logger.info(
                "penalty_station_unclosed skipped: user=%s session_id=%s odk=%s (sin picks ese día)",
                user_id,
                orphan_id,
                orphan_odk,
            )
            continue
        bal_after = _append_dp_ledger_move(
            cur, user_id, PENALTY_STATION_UNCLOSED_DP, REASON_PENALTY_STATION_UNCLOSED, orphan_id
        )
        logger.info(
            "penalty_station_unclosed: user=%s session_id=%s (estación sin cerrar con actividad de picks) balance_after=%s",
            user_id,
            orphan_id,
            bal_after,
        )


def _apply_grace_unsettled_penalties(cur, user_id: str, now: datetime) -> None:
    """
    penalty_unsettled_picks −25 si la gracia venció y había pick **abierto tomado durante
    esa sesión** (entre station_opened_at y station_closed_at). No cuenta picks viejos
    abiertos de otros días. Idempotente por sesión. US-BE-017 (recalibrado).
    """
    cur.execute(
        """SELECT id, station_opened_at, station_closed_at FROM bt2_operating_sessions
           WHERE user_id = %s::uuid AND status = 'closed' AND grace_until_iso < %s""",
        (user_id, now),
    )
    for sess_id, opened_at, closed_at in cur.fetchall():
        if _ledger_move_exists(cur, user_id, REASON_PENALTY_UNSETTLED_PICKS, sess_id):
            continue
        if _ledger_move_exists(cur, user_id, REASON_PENALTY_UNSETTLED_NOT_APPLICABLE, sess_id):
            continue
        if closed_at is None or opened_at is None:
            continue
        cur.execute(
            """SELECT 1 FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'
                 AND opened_at >= %s AND opened_at <= %s
               LIMIT 1""",
            (user_id, opened_at, closed_at),
        )
        if not cur.fetchone():
            _append_dp_ledger_move(
                cur, user_id, 0, REASON_PENALTY_UNSETTLED_NOT_APPLICABLE, sess_id
            )
            logger.info(
                "penalty_unsettled_picks skipped: user=%s session_id=%s (sin picks abiertos en intervalo sesión)",
                user_id,
                sess_id,
            )
            continue
        bal_after = _append_dp_ledger_move(
            cur, user_id, PENALTY_UNSETTLED_DP, REASON_PENALTY_UNSETTLED_PICKS, sess_id
        )
        logger.info(
            "penalty_unsettled_picks: user=%s session_id=%s balance_after=%s",
            user_id,
            sess_id,
            bal_after,
        )


def _determine_outcome(market: str, selection: str, result_home: int, result_away: int) -> str:
    """
    Determina 'won', 'lost' o 'void' (US-DX-001 — mercados mínimos settle, Sprint 05).

    Soportado hoy (sinónimos en selection):
    - Match Winner / 1X2 / Winner: selección 1|Home|home, X|Draw|…, 2|Away|away.
    - Over/Under goals: selección con OVER|UNDER y umbral numérico (default 2.5).
    Entrada típica ya normalizada vía `_normalize_market_selection_for_pick` (POST /bt2/picks): ML_SIDE,
    ML_AWAY, ML_TOTAL, textos «Más de …», «Victoria {equipo}», etc.

    Sprint 06: enum único en CDM/API. Implementación compartida: `determine_settlement_outcome`.
    """
    return determine_settlement_outcome(market, selection, result_home, result_away)


def _normalize_market_selection_for_pick(
    cur,
    event_id: int,
    market: str,
    selection: str,
) -> Tuple[str, str]:
    """
    US-BE-023: mapea mercado/selección del cliente hacia forma entendida por `_determine_outcome`.
    Falla con 422 si no hay mapeo determinista.
    """
    m0 = market.strip()
    s0 = selection.strip()
    if not m0 or not s0:
        raise HTTPException(
            status_code=422,
            detail="market y selection no pueden estar vacíos tras normalizar",
        )
    mu = m0.upper()
    sl = s0.lower()

    cur.execute(
        """SELECT COALESCE(th.name,''), COALESCE(ta.name,'')
           FROM bt2_events e
           LEFT JOIN bt2_teams th ON e.home_team_id = th.id
           LEFT JOIN bt2_teams ta ON e.away_team_id = ta.id
           WHERE e.id = %s""",
        (event_id,),
    )
    row = cur.fetchone()
    home = (row[0] or "").strip()
    away = (row[1] or "").strip()
    hl = home.lower()
    al = away.lower()

    is_total = any(
        k in mu
        for k in (
            "ML_TOTAL",
            "TOTAL_OVER",
            "TOTAL_UNDER",
            "TOTAL",
            "GOALS",
            "OVER",
            "UNDER",
            "O/U",
            "OU",
        )
    )
    if is_total:
        num_m = re.search(r"(\d+\.?\d*)", s0)
        line = float(num_m.group(1)) if num_m else 2.5
        overish = (
            "mas" in sl
            or "más" in sl
            or "over" in sl
            or "more" in sl
            or mu.endswith("_OVER")
            or "TOTAL_OVER" in mu
        )
        underish = (
            "menos" in sl
            or "under" in sl
            or mu.endswith("_UNDER")
            or "TOTAL_UNDER" in mu
        )
        if overish and not underish:
            return ("TOTAL GOALS", f"OVER {line}")
        if underish and not overish:
            return ("TOTAL GOALS", f"UNDER {line}")
        if overish and underish:
            raise HTTPException(
                status_code=422,
                detail="Selección de totales ambigua (mezcla over/under).",
            )
        raise HTTPException(
            status_code=422,
            detail=(
                "No se pudo normalizar mercado de totales: indique explícitamente más/menos, "
                "over/under, o use ML_TOTAL / TOTAL_OVER / TOTAL_UNDER."
            ),
        )

    if any(k in mu for k in ("SPREAD", "PROP", "HANDICAP", "PLAYER")):
        raise HTTPException(
            status_code=422,
            detail="Mercado no soportado para registro de pick en esta versión (spread / prop / hándicap).",
        )

    # 1X2 / moneyline
    canon_market = "1X2"
    if s0 in ("1", "2", "X", "x"):
        return (canon_market, "X" if s0.lower() == "x" else s0)
    if s0 in ("Home", "home", "Away", "away", "Draw", "draw"):
        return (canon_market, s0[0].upper() + s0[1:].lower() if s0.lower() != "draw" else "Draw")

    if "empate" in sl or sl in ("draw", "x"):
        return (canon_market, "X")
    if hl and hl in sl:
        return (canon_market, "1")
    if al and al in sl:
        return (canon_market, "2")
    if "local" in sl and "visitante" not in sl:
        return (canon_market, "1")
    if "visitante" in sl:
        return (canon_market, "2")
    if mu in ("ML_AWAY",) or "ML_AWAY" in mu:
        return (canon_market, "2")
    if "victoria" in sl or "gana" in sl:
        if al and al in sl:
            return (canon_market, "2")
        if hl and hl in sl:
            return (canon_market, "1")

    raise HTTPException(
        status_code=422,
        detail=(
            "No se pudo mapear market/selection a un mercado soportado para liquidación. "
            "Use 1X2 (1/X/2, local/visitante, empate) o totales explícitos (más/menos, over/under)."
        ),
    )


# ── Picks schemas (Sprint 04 US-BE-010) ──────────────────────────────────────

class PickIn(BaseModel):
    event_id: int
    market: str
    selection: str
    odds_accepted: float
    stake_units: float


class PickOut(BaseModel):
    """US-BE-018 §9 / US-BE-022 — campos nuevos con alias camelCase (rutas con response_model_by_alias)."""

    model_config = ConfigDict(populate_by_name=True)

    pick_id: int
    status: str
    opened_at: str
    stake_units: float
    odds_accepted: float
    event_label: str
    event_id: int
    market: str
    selection: str
    settled_at: Optional[str] = None
    pnl_units: Optional[float] = None
    earned_dp: Optional[int] = None
    result_home: Optional[int] = Field(None, serialization_alias="resultHome")
    result_away: Optional[int] = Field(None, serialization_alias="resultAway")
    kickoff_utc: Optional[str] = Field(None, serialization_alias="kickoffUtc")
    event_status: Optional[str] = Field(None, serialization_alias="eventStatus")
    settlement_source: str = Field("user", serialization_alias="settlementSource")
    market_canonical: Optional[str] = Field(None, serialization_alias="marketCanonical")
    market_canonical_label_es: Optional[str] = Field(
        None, serialization_alias="marketCanonicalLabelEs"
    )
    model_market_canonical: Optional[str] = Field(
        None, serialization_alias="modelMarketCanonical"
    )
    model_selection_canonical: Optional[str] = Field(
        None, serialization_alias="modelSelectionCanonical"
    )
    model_prediction_result: Optional[str] = Field(
        None, serialization_alias="modelPredictionResult"
    )
    bankroll_after_units: Optional[float] = Field(
        None,
        serialization_alias="bankrollAfterUnits",
        description="Tras tomar el pick: bankroll con stake ya descontado (solo POST /bt2/picks).",
    )


class PicksListOut(BaseModel):
    picks: List[PickOut]


class SettleIn(BaseModel):
    result_home: int
    result_away: int


class SettleOut(BaseModel):
    """Respuesta POST /bt2/picks/{id}/settle — alias camelCase como el resto de rutas BT2."""

    model_config = ConfigDict(populate_by_name=True)

    pick_id: int = Field(serialization_alias="pickId")
    status: str
    pnl_units: float = Field(serialization_alias="pnlUnits")
    bankroll_after_units: Optional[float] = Field(
        None,
        serialization_alias="bankrollAfterUnits",
    )
    earned_dp: int = Field(serialization_alias="earnedDp")
    dp_balance_after: int = Field(serialization_alias="dpBalanceAfter")


# ── Picks endpoints (T-098, T-099) ───────────────────────────────────────────

@router.post(
    "/picks",
    status_code=201,
    response_model=PickOut,
    response_model_by_alias=True,
)
def bt2_create_pick(body: PickIn, user_id: Bt2UserId) -> PickOut:
    if body.odds_accepted <= 1.0:
        raise HTTPException(status_code=422, detail="odds_accepted debe ser > 1.0")
    if body.stake_units <= 0:
        raise HTTPException(status_code=422, detail="stake_units debe ser > 0")

    odk = _operating_day_key_for_user(user_id)
    conn = _db_conn()
    cur = conn.cursor()
    try:
        # Validar que el evento existe y está scheduled
        cur.execute(
            "SELECT id, status, kickoff_utc FROM bt2_events WHERE id = %s",
            (body.event_id,),
        )
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento no encontrado")
        ev_status = ev[1]
        ev_kickoff = ev[2]
        if ev_status != "scheduled":
            raise HTTPException(
                status_code=422,
                detail=f"El evento no está disponible para picks (status={ev_status})",
            )
        now_pick = datetime.now(timezone.utc)
        if not is_event_available_for_pick_strict(
            event_status=str(ev_status or ""),
            kickoff_utc=ev_kickoff,
            now_utc=now_pick,
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": BT2_ERR_PICK_KICKOFF_ELAPSED,
                    "message": (
                        "El partido ya inició respecto al horario de kickoff; "
                        "no es posible tomar el pick (D-05.2-001)."
                    ),
                    "kickoffUtc": _kickoff_utc_iso_z(ev_kickoff),
                },
            )

        norm_market, norm_selection = _normalize_market_selection_for_pick(
            cur, body.event_id, body.market, body.selection
        )
        m_canon, s_canon = normalized_pick_to_canonical(norm_market, norm_selection)
        m_label_es = market_canonical_label_es(m_canon)

        cur.execute(
            """SELECT model_market_canonical, model_selection_canonical
               FROM bt2_daily_picks
               WHERE user_id = %s::uuid AND operating_day_key = %s AND event_id = %s
                 AND slate_rank <= %s
               ORDER BY slate_rank ASC LIMIT 1""",
            (user_id, odk, body.event_id, VAULT_POOL_HARD_CAP),
        )
        snap_model = cur.fetchone()
        snap_mm = snap_model[0] if snap_model else None
        snap_ms = snap_model[1] if snap_model else None

        # Prevenir pick duplicado (mismo usuario, evento, mercado canónico)
        cur.execute(
            """SELECT id FROM bt2_picks
               WHERE user_id = %s::uuid AND event_id = %s
                 AND market = %s AND selection = %s AND status = 'open'""",
            (user_id, body.event_id, norm_market, norm_selection),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe un pick abierto para este evento/mercado/selección")

        # Premium snapshot (D-05-004 / US-BE-029): −50 solo si no hubo unlock previo ni legado con pick abierto.
        cur.execute(
            """SELECT id FROM bt2_daily_picks
               WHERE user_id = %s::uuid AND operating_day_key = %s AND event_id = %s
                 AND access_tier = 'premium'
                 AND slate_rank <= %s
               ORDER BY slate_rank ASC LIMIT 1""",
            (user_id, odk, body.event_id, VAULT_POOL_HARD_CAP),
        )
        dp_prem = cur.fetchone()
        needs_premium_snapshot = dp_prem is not None
        daily_pick_id = int(dp_prem[0]) if dp_prem else None

        already_premium_unlocked = False
        if needs_premium_snapshot and daily_pick_id is not None:
            cur.execute(
                """SELECT 1 FROM bt2_vault_premium_unlocks
                   WHERE user_id = %s::uuid AND daily_pick_id = %s""",
                (user_id, daily_pick_id),
            )
            already_premium_unlocked = cur.fetchone() is not None
            if not already_premium_unlocked:
                cur.execute(
                    """SELECT 1 FROM bt2_picks
                       WHERE user_id = %s::uuid AND event_id = %s AND status = 'open'
                       LIMIT 1""",
                    (user_id, body.event_id),
                )
                already_premium_unlocked = cur.fetchone() is not None

        charge_premium_unlock = needs_premium_snapshot and not already_premium_unlocked

        if charge_premium_unlock:
            bal_raw = _get_dp_ledger_sum(cur, user_id)
            if bal_raw < DP_PREMIUM_UNLOCK_COST:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "code": BT2_ERR_DP_INSUFFICIENT_PREMIUM,
                        "message": (
                            "Saldo de Discipline Points insuficiente para desbloquear la señal premium "
                            f"del día (se requieren {DP_PREMIUM_UNLOCK_COST} DP)."
                        ),
                        "requiredDp": DP_PREMIUM_UNLOCK_COST,
                        "currentDp": max(0, bal_raw),
                    },
                )

        cur.execute(
            """SELECT COALESCE(bankroll_amount, 0) FROM bt2_users WHERE id = %s::uuid FOR UPDATE""",
            (user_id,),
        )
        br_bank = cur.fetchone()
        if not br_bank:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        balance_pre = float(br_bank[0])
        stake_amt = float(body.stake_units)
        if balance_pre + 1e-9 < stake_amt:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": BT2_ERR_INSUFFICIENT_BANKROLL_STAKE,
                    "message": (
                        f"Saldo insuficiente para registrar este stake: bankroll {balance_pre:.2f}, "
                        f"stake requerido {stake_amt:.2f}."
                    ),
                    "bankroll": balance_pre,
                    "requiredStake": stake_amt,
                },
            )

        cur.execute(
            """INSERT INTO bt2_picks
               (user_id, event_id, market, selection, odds_taken, stake_units, status,
                market_canonical, model_market_canonical, model_selection_canonical)
               VALUES (%s::uuid, %s, %s, %s, %s, %s, 'open', %s, %s, %s)
               RETURNING id, status, opened_at""",
            (
                user_id,
                body.event_id,
                norm_market,
                norm_selection,
                body.odds_accepted,
                body.stake_units,
                m_canon,
                snap_mm,
                snap_ms,
            ),
        )
        row = cur.fetchone()
        pick_id, pick_status, opened_at = row

        new_bal_out = round(balance_pre - stake_amt, 2)
        cur.execute(
            """UPDATE bt2_users SET bankroll_amount = %s WHERE id = %s::uuid RETURNING bankroll_amount""",
            (new_bal_out, user_id),
        )
        nb_row = cur.fetchone()
        if nb_row and nb_row[0] is not None:
            new_bal_out = float(nb_row[0])

        cur.execute(
            """INSERT INTO bt2_bankroll_snapshots
               (user_id, snapshot_date, balance_units, event_type, reference_id)
               VALUES (%s::uuid, %s, %s, %s, %s)""",
            (
                user_id,
                now_pick.date(),
                new_bal_out,
                "pick_stake_committed",
                pick_id,
            ),
        )

        if charge_premium_unlock:
            _append_dp_ledger_move(
                cur,
                user_id,
                -DP_PREMIUM_UNLOCK_COST,
                REASON_PICK_PREMIUM_UNLOCK,
                pick_id,
            )
            logger.info(
                "pick_premium_unlock: user=%s pick_id=%s delta_dp=-%s (desbloqueo + pick mismo commit)",
                user_id,
                pick_id,
                DP_PREMIUM_UNLOCK_COST,
            )
        elif needs_premium_snapshot:
            logger.info(
                "pick_create_skip_premium_charge: user=%s pick_id=%s event_id=%s (US-BE-029 unlock previo o legado)",
                user_id,
                pick_id,
                body.event_id,
            )

        logger.info(
            "pick_stake_committed: user=%s pick_id=%s stake=%s bankroll_after=%s",
            user_id,
            pick_id,
            stake_amt,
            new_bal_out,
        )

        conn.commit()

        cur.execute(
            """SELECT th.name, ta.name, e.kickoff_utc, e.status FROM bt2_events e
               JOIN bt2_teams th ON e.home_team_id = th.id
               JOIN bt2_teams ta ON e.away_team_id = ta.id
               WHERE e.id = %s""",
            (body.event_id,),
        )
        teams = cur.fetchone()
        if teams:
            event_label = f"{teams[0]} vs {teams[1]}"
            kickoff_iso = (
                _kickoff_utc_iso_z(teams[2]) if teams[2] is not None else ""
            )
            ev_status = str(teams[3]) if teams[3] is not None else ""
        else:
            event_label = f"Evento {body.event_id}"
            kickoff_iso = ""
            ev_status = ""
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return PickOut(
        pick_id=pick_id,
        status=pick_status,
        opened_at=opened_at.isoformat(),
        stake_units=float(body.stake_units),
        odds_accepted=float(body.odds_accepted),
        event_label=event_label,
        event_id=body.event_id,
        market=norm_market,
        selection=norm_selection,
        settlement_source="user",
        kickoff_utc=kickoff_iso if kickoff_iso else None,
        event_status=ev_status if ev_status else None,
        market_canonical=m_canon,
        market_canonical_label_es=m_label_es,
        model_market_canonical=snap_mm,
        model_selection_canonical=snap_ms,
        model_prediction_result=None,
        bankroll_after_units=new_bal_out,
    )


@router.get(
    "/picks",
    response_model=PicksListOut,
    response_model_by_alias=True,
)
def bt2_list_picks(
    user_id: Bt2UserId,
    status: Optional[str] = Query(default="all"),
    date_filter: Optional[str] = Query(default=None, alias="date"),
) -> PicksListOut:
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        where = ["p.user_id = %s::uuid"]
        params: list = [user_id]

        if status and status != "all":
            where.append("p.status = %s")
            params.append(status)

        if date_filter:
            try:
                d = date.fromisoformat(date_filter)
                where.append("DATE(p.opened_at AT TIME ZONE 'UTC') = %s")
                params.append(d)
            except ValueError:
                pass

        ledger_params = [user_id, REASON_PICK_SETTLE]
        cur.execute(
            f"""SELECT p.id, p.event_id, p.market, p.selection,
                       p.odds_taken, p.stake_units, p.status,
                       p.opened_at, p.settled_at, p.pnl_units,
                       p.result_home, p.result_away, p.settlement_source,
                       p.market_canonical, p.model_market_canonical,
                       p.model_selection_canonical, p.model_prediction_result,
                       e.kickoff_utc, e.status AS ev_status,
                       COALESCE(th.name,'?') || ' vs ' || COALESCE(ta.name,'?') AS event_label,
                       CASE WHEN p.status = 'open' THEN NULL
                            ELSE COALESCE(l.delta_sum, 0)::int END AS earned_dp
                FROM bt2_picks p
                LEFT JOIN bt2_events e ON p.event_id = e.id
                LEFT JOIN bt2_teams th ON e.home_team_id = th.id
                LEFT JOIN bt2_teams ta ON e.away_team_id = ta.id
                LEFT JOIN (
                    SELECT reference_id, SUM(delta_dp) AS delta_sum
                    FROM bt2_dp_ledger
                    WHERE user_id = %s::uuid AND reason = %s AND reference_id IS NOT NULL
                    GROUP BY reference_id
                ) l ON l.reference_id = p.id
                WHERE {' AND '.join(where)}
                ORDER BY p.opened_at DESC""",
            ledger_params + params,
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    picks = [
        PickOut(
            pick_id=r["id"],
            event_id=r["event_id"],
            event_label=r["event_label"],
            market=r["market"],
            selection=r["selection"],
            odds_accepted=float(r["odds_taken"]),
            stake_units=float(r["stake_units"]),
            status=r["status"],
            opened_at=r["opened_at"].isoformat(),
            settled_at=r["settled_at"].isoformat() if r["settled_at"] else None,
            pnl_units=float(r["pnl_units"]) if r["pnl_units"] is not None else None,
            earned_dp=r["earned_dp"],
            result_home=r["result_home"],
            result_away=r["result_away"],
            settlement_source=r["settlement_source"] or "user",
            kickoff_utc=_kickoff_utc_iso_z(r["kickoff_utc"]) or None,
            event_status=str(r["ev_status"]) if r["ev_status"] is not None else None,
            market_canonical=r.get("market_canonical"),
            market_canonical_label_es=market_canonical_label_es(r.get("market_canonical"))
            if r.get("market_canonical")
            else None,
            model_market_canonical=r.get("model_market_canonical"),
            model_selection_canonical=r.get("model_selection_canonical"),
            model_prediction_result=r.get("model_prediction_result"),
        )
        for r in rows
    ]
    return PicksListOut(picks=picks)


@router.get(
    "/picks/{pick_id}",
    response_model=PickOut,
    response_model_by_alias=True,
)
def bt2_get_pick(pick_id: int, user_id: Bt2UserId) -> PickOut:
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """SELECT p.id, p.event_id, p.market, p.selection,
                      p.odds_taken, p.stake_units, p.status,
                      p.opened_at, p.settled_at, p.pnl_units,
                      p.result_home, p.result_away, p.settlement_source,
                      p.market_canonical, p.model_market_canonical,
                      p.model_selection_canonical, p.model_prediction_result,
                      e.kickoff_utc, e.status AS ev_status,
                      COALESCE(th.name,'?') || ' vs ' || COALESCE(ta.name,'?') AS event_label,
                      CASE WHEN p.status = 'open' THEN NULL
                           ELSE COALESCE(l.delta_sum, 0)::int END AS earned_dp
               FROM bt2_picks p
               LEFT JOIN bt2_events e ON p.event_id = e.id
               LEFT JOIN bt2_teams th ON e.home_team_id = th.id
               LEFT JOIN bt2_teams ta ON e.away_team_id = ta.id
               LEFT JOIN (
                   SELECT reference_id, SUM(delta_dp) AS delta_sum
                   FROM bt2_dp_ledger
                   WHERE user_id = %s::uuid AND reason = %s AND reference_id IS NOT NULL
                   GROUP BY reference_id
               ) l ON l.reference_id = p.id
               WHERE p.id = %s AND p.user_id = %s::uuid""",
            (user_id, REASON_PICK_SETTLE, pick_id, user_id),
        )
        r = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Pick no encontrado")

    return PickOut(
        pick_id=r["id"],
        event_id=r["event_id"],
        event_label=r["event_label"],
        market=r["market"],
        selection=r["selection"],
        odds_accepted=float(r["odds_taken"]),
        stake_units=float(r["stake_units"]),
        status=r["status"],
        opened_at=r["opened_at"].isoformat(),
        settled_at=r["settled_at"].isoformat() if r["settled_at"] else None,
        pnl_units=float(r["pnl_units"]) if r["pnl_units"] is not None else None,
        earned_dp=r["earned_dp"],
        result_home=r["result_home"],
        result_away=r["result_away"],
        settlement_source=r["settlement_source"] or "user",
        kickoff_utc=_kickoff_utc_iso_z(r["kickoff_utc"]) or None,
        event_status=str(r["ev_status"]) if r["ev_status"] is not None else None,
        market_canonical=r.get("market_canonical"),
        market_canonical_label_es=market_canonical_label_es(r.get("market_canonical"))
        if r.get("market_canonical")
        else None,
        model_market_canonical=r.get("model_market_canonical"),
        model_selection_canonical=r.get("model_selection_canonical"),
        model_prediction_result=r.get("model_prediction_result"),
    )


@router.post(
    "/picks/{pick_id}/settle",
    response_model=SettleOut,
    response_model_by_alias=True,
)
def bt2_settle_pick(pick_id: int, body: SettleIn, user_id: Bt2UserId) -> SettleOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, status, market, selection, odds_taken, stake_units,
                      model_market_canonical, model_selection_canonical
               FROM bt2_picks WHERE id = %s AND user_id = %s::uuid""",
            (pick_id, user_id),
        )
        pick = cur.fetchone()
        if not pick:
            raise HTTPException(status_code=404, detail="Pick no encontrado")
        if pick[1] != "open":
            raise HTTPException(status_code=409, detail="El pick ya está liquidado")

        outcome = _determine_outcome(pick[2], pick[3], body.result_home, body.result_away)
        model_pred = evaluate_model_vs_result(
            pick[6],
            pick[7],
            body.result_home,
            body.result_away,
            _determine_outcome,
        )
        odds = float(pick[4])
        stake = float(pick[5])

        # Stake ya descontado al abrir el pick (POST /bt2/picks). Liquidación:
        # - won: reintegrar stake×cuota (apuesta + beneficio).
        # - lost: sin movimiento adicional de bankroll.
        # - void: reembolsar stake.
        # pnl_units en fila = resultado económico neto del pick (para historial / UI).
        if outcome == "won":
            pnl = round(stake * (odds - 1), 2)
            bankroll_delta = round(stake * odds, 2)
            event_type = "pick_win"
        elif outcome == "lost":
            pnl = round(-stake, 2)
            bankroll_delta = 0.0
            event_type = "pick_loss"
        else:
            pnl = 0.0
            bankroll_delta = round(stake, 2)
            event_type = "pick_void"

        # US-BE-020 (D-04-011 / D-05-012): +10 DP en ledger para won, lost y void.
        dp_earned = PICK_SETTLE_DP_REWARD

        now = datetime.now(tz=timezone.utc)

        cur.execute(
            """UPDATE bt2_picks
               SET status = %s, settled_at = %s,
                   result_home = %s, result_away = %s, pnl_units = %s,
                   settlement_source = 'user',
                   model_prediction_result = %s
               WHERE id = %s""",
            (outcome, now, body.result_home, body.result_away, pnl, model_pred, pick_id),
        )

        cur.execute(
            """UPDATE bt2_users SET bankroll_amount = COALESCE(bankroll_amount, 0) + %s
               WHERE id = %s::uuid
               RETURNING bankroll_amount""",
            (bankroll_delta, user_id),
        )
        bankroll_row = cur.fetchone()
        new_bankroll = (
            float(bankroll_row[0])
            if bankroll_row is not None and bankroll_row[0] is not None
            else None
        )

        cur.execute(
            """INSERT INTO bt2_bankroll_snapshots
               (user_id, snapshot_date, balance_units, event_type, reference_id)
               VALUES (%s::uuid, %s, %s, %s, %s)""",
            (user_id, now.date(), new_bankroll or 0, event_type, pick_id),
        )

        _append_dp_ledger_move(
            cur, user_id, PICK_SETTLE_DP_REWARD, REASON_PICK_SETTLE, pick_id
        )
        dp_balance_after = _get_dp_balance(cur, user_id)

        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return SettleOut(
        pick_id=pick_id,
        status=outcome,
        pnl_units=pnl,
        bankroll_after_units=new_bankroll,
        earned_dp=dp_earned,
        dp_balance_after=dp_balance_after,
    )


# ── Sesión operativa schemas (Sprint 04 US-BE-011) ────────────────────────────

class SessionOpenOut(BaseModel):
    session_id: int
    operating_day_key: str
    station_opened_at: str
    grace_until_iso: Optional[str] = None


class SessionCloseOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: int
    status: str
    grace_until_iso: str
    pending_settlements: int
    earned_dp_session_close: int = Field(
        ...,
        serialization_alias="earnedDpSessionClose",
        description="DP acreditados por este cierre (session_close_discipline; típicamente +20).",
    )
    dp_balance_after: int = Field(
        ...,
        serialization_alias="dpBalanceAfter",
        description="Saldo DP tras el movimiento (suma ledger, clamp ≥0 en lectura).",
    )


class Bt2DevResetOperatingDayOut(BaseModel):
    """Respuesta de POST /bt2/dev/reset-operating-day-for-tests (solo si BT2_DEV_OPERATING_DAY_RESET)."""

    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    operating_day_key: str = Field(..., serialization_alias="operatingDayKey")
    daily_picks_deleted: int = Field(
        ...,
        serialization_alias="dailyPicksDeleted",
        description="Filas borradas de bt2_daily_picks para ese día.",
    )
    server_session_closed: bool = Field(
        ...,
        serialization_alias="serverSessionClosed",
        description="True si había sesión abierta y se marcó closed.",
    )
    sm_fixtures_refreshed: int = Field(
        0,
        serialization_alias="smFixturesRefreshed",
        description="Payloads UPSERT en raw_sportmonks_fixtures (pool valor hoy) antes del borrado snapshot.",
    )
    sm_refresh_log: list[str] = Field(
        default_factory=list,
        serialization_alias="smRefreshLog",
        description="Notas / errores del refresco SM (acotado en servidor).",
    )
    sfs_auto_ingest: Optional[dict[str, Any]] = Field(
        None,
        serialization_alias="sfsAutoIngest",
        description=(
            "Tras reset: ingest SofaScore → bt2_provider_odds_snapshot para eventos del pool valor "
            "(fusion + prob_coherence en ds_input cuando BT2_SFS_MARKETS_FUSION_ENABLED)."
        ),
    )
    message_es: str = Field(..., serialization_alias="messageEs")


# ── Sesión endpoints (T-100, T-101) ──────────────────────────────────────────


def _fetch_event_context_for_dsr(cur, event_id: int) -> Optional[tuple]:
    """Odds 1X2 + O/U 2.5 y metadatos para stub DSR (US-BE-025)."""
    cur.execute(
        """
        SELECT
            COALESCE(th.name, ''),
            COALESCE(ta.name, ''),
            COALESCE(l.name, ''),
            (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
             WHERE o.event_id = e.id
               AND lower(o.market) IN ('1x2','match winner','full time result','fulltime result')
               AND (o.selection IN ('1','Home') OR lower(o.selection) LIKE '%%home%%')),
            (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
             WHERE o.event_id = e.id
               AND lower(o.market) IN ('1x2','match winner','full time result','fulltime result')
               AND (o.selection IN ('X','Draw') OR lower(o.selection) LIKE '%%draw%%')),
            (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
             WHERE o.event_id = e.id
               AND lower(o.market) IN ('1x2','match winner','full time result','fulltime result')
               AND (o.selection IN ('2','Away') OR lower(o.selection) LIKE '%%away%%')),
            (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
             WHERE o.event_id = e.id
               AND (lower(o.market) LIKE '%%goals over/under%%' OR lower(o.market) LIKE '%%over%%under%%')
               AND (lower(o.selection) LIKE '%%over%%' AND lower(o.selection) NOT LIKE '%%under%%')),
            (SELECT MAX(o.odds) FROM bt2_odds_snapshot o
             WHERE o.event_id = e.id
               AND (lower(o.market) LIKE '%%goals over/under%%' OR lower(o.market) LIKE '%%over%%under%%')
               AND lower(o.selection) LIKE '%%under%%')
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.id = %s
        """,
        (event_id,),
    )
    row = cur.fetchone()
    return row


def _upsert_vault_day_metadata(
    cur,
    user_id: str,
    odk: str,
    *,
    dsr_signal_degraded: bool,
    limited_coverage: bool,
    operational_empty_hard: bool,
    vault_empty_message_es: Optional[str],
    fallback_disclaimer_es: Optional[str],
    future_events_in_window_count: int,
    fallback_eligible_pool_count: int,
    slate_band_cycle: int = 0,
) -> None:
    cur.execute(
        """
        INSERT INTO bt2_vault_day_metadata (
            user_id, operating_day_key, dsr_signal_degraded, limited_coverage,
            operational_empty_hard, vault_empty_message_es, fallback_disclaimer_es,
            future_events_in_window_count, fallback_eligible_pool_count, slate_band_cycle
        )
        VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, operating_day_key) DO UPDATE SET
            dsr_signal_degraded = EXCLUDED.dsr_signal_degraded,
            limited_coverage = EXCLUDED.limited_coverage,
            operational_empty_hard = EXCLUDED.operational_empty_hard,
            vault_empty_message_es = EXCLUDED.vault_empty_message_es,
            fallback_disclaimer_es = EXCLUDED.fallback_disclaimer_es,
            future_events_in_window_count = EXCLUDED.future_events_in_window_count,
            fallback_eligible_pool_count = EXCLUDED.fallback_eligible_pool_count,
            slate_band_cycle = EXCLUDED.slate_band_cycle
        """,
        (
            user_id,
            odk,
            dsr_signal_degraded,
            limited_coverage,
            operational_empty_hard,
            vault_empty_message_es,
            fallback_disclaimer_es,
            future_events_in_window_count,
            fallback_eligible_pool_count,
            slate_band_cycle,
        ),
    )


def _generate_daily_picks_snapshot(cur, user_id: str, odk: str, tz_name: str) -> int:
    """
    US-BE-030 + S6.1: pool valor (T-177), builder ds_input (T-174/175), Post-DSR (T-181/182),
    orquestación DSR → fallback SQL (D-06-022) y vacío duro (D-06-026 §6).
    Idempotente: si ya existe snapshot para (user_id, odk), no hace nada.
    """
    cur.execute(
        "SELECT COUNT(*) FROM bt2_daily_picks WHERE user_id = %s::uuid AND operating_day_key = %s",
        (user_id, odk),
    )
    if int(cur.fetchone()[0]) > 0:
        return 0
    return _materialize_daily_picks_snapshot(
        cur,
        user_id,
        odk,
        tz_name,
        band_cycle_offset=0,
        slate_band_cycle_to_store=0,
        replace_existing_slate=False,
    )


def _materialize_daily_picks_snapshot(
    cur,
    user_id: str,
    odk: str,
    tz_name: str,
    *,
    band_cycle_offset: int,
    slate_band_cycle_to_store: int,
    replace_existing_slate: bool,
) -> int:
    """
    Construye y persiste hasta 20 filas en bt2_daily_picks (orden franjas + calidad) desde el pool
    valor del día (≤20 candidatos). Las filas 1–5 (`slate_rank`) son la cartelera visible en GET.

    `replace_existing_slate`: True = borra snapshot y desbloqueos premium del día y vuelve a
    materializar (rotación de franja vía `band_cycle_offset`). Misma corrida DSR que el snapshot inicial.
    """
    if replace_existing_slate:
        cur.execute(
            """DELETE FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        cur.execute(
            """DELETE FROM bt2_daily_picks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )

    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc

    local_today = datetime.now(tz=tz).date()
    day_start_utc = datetime.combine(local_today, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    day_end_utc = day_start_utc + timedelta(hours=24)

    league_filter = parse_priority_league_ids(bt2_settings.bt2_priority_league_ids)
    future_ec = count_future_events_window(cur, day_start_utc, day_end_utc)
    limited_cov = future_ec < 5

    pool, _pre_n = build_value_pool_for_snapshot(
        cur, day_start_utc, day_end_utc, league_filter=league_filter
    )
    if len(pool) > VAULT_VALUE_POOL_UNIVERSE_MAX:
        pool = pool[:VAULT_VALUE_POOL_UNIVERSE_MAX]
    fallback_pool_count = len(pool)

    if not pool:
        _upsert_vault_day_metadata(
            cur,
            user_id,
            odk,
            dsr_signal_degraded=False,
            limited_coverage=limited_cov,
            operational_empty_hard=True,
            vault_empty_message_es=_VAULT_HARD_EMPTY_MESSAGE_ES,
            fallback_disclaimer_es=None,
            future_events_in_window_count=future_ec,
            fallback_eligible_pool_count=0,
            slate_band_cycle=slate_band_cycle_to_store,
        )
        return 0

    rows_for_compose = [(eid, ko, hm) for eid, ko, hm, _agg, _lt in pool]
    composed = compose_vault_daily_picks(
        rows_for_compose,
        tz,
        None,
        band_cycle_offset=band_cycle_offset,
    )
    tier_by_eid_pre = {
        int(eid): (lt or "").strip().upper() for eid, _ko, _hm, _agg, lt in pool
    }
    composed_sa = [
        (eid, b) for eid, b in composed if league_eligible_for_snapshot(tier_by_eid_pre.get(eid))
    ]

    plan: list[tuple[int, Any, dict, Any]] = []
    for event_id, band in composed_sa:
        built = build_ds_input_item_from_db(cur, event_id, selection_tier="A")
        if not built:
            continue
        item, agg = built
        plan.append((event_id, band, item, agg))

    ds_resolved: dict[int, tuple[str, str, str, str, str, str, str]] = {}
    prov = (bt2_settings.bt2_dsr_provider or "rules").strip().lower()
    dkey = (bt2_settings.deepseek_api_key or "").strip()
    dsr_api_enabled = bool(bt2_settings.bt2_dsr_enabled)
    global_sql_fallback = False
    dsr_any_success = False

    if not dsr_api_enabled and prov == "deepseek" and dkey and plan:
        logger.info(
            "bt2_dsr_skipped BT2_DSR_ENABLED=false — snapshot usa sql_stat_fallback (sin llamada API)"
        )
        global_sql_fallback = True
    elif prov == "deepseek" and dkey and plan and dsr_api_enabled:
        batch_size = max(1, int(bt2_settings.bt2_dsr_batch_size))
        for i in range(0, len(plan), batch_size):
            chunk = plan[i : i + batch_size]
            items = [p[2] for p in chunk]
            part = deepseek_suggest_batch(
                items,
                operating_day_key=odk,
                api_key=dkey,
                base_url=bt2_settings.bt2_dsr_deepseek_base_url,
                model=bt2_settings.bt2_dsr_deepseek_model,
                timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                max_retries=int(bt2_settings.bt2_dsr_max_retries),
            )
            for event_id, _b, item, _agg in chunk:
                raw = part.get(event_id)
                if raw is None:
                    continue
                narr, conf, mmc, msc, mod_o = raw
                consensus = item["processed"]["odds_featured"]["consensus"]
                m_cov = item["diagnostics"]["market_coverage"]
                ctx = item["event_context"]
                ppc = postprocess_dsr_pick(
                    narrative_es=narr,
                    confidence_label=conf,
                    market_canonical=mmc,
                    selection_canonical=msc,
                    model_declared_odds=mod_o,
                    consensus=consensus,
                    market_coverage=m_cov,
                    event_id=event_id,
                    home_team=str(ctx.get("home_team") or ""),
                    away_team=str(ctx.get("away_team") or ""),
                )
                if ppc:
                    n2, c2, m2, s2 = ppc
                    h2 = hash_for_ds_input_item(item)
                    ds_resolved[event_id] = (
                        n2,
                        c2,
                        m2,
                        s2,
                        PIPELINE_VERSION_DEEPSEEK,
                        "dsr_api",
                        h2,
                    )
                    dsr_any_success = True
        if not dsr_any_success:
            global_sql_fallback = True
    elif prov == "deepseek" and not dkey:
        logger.warning("bt2_dsr_missing_api_key provider=deepseek (lotes no invocados)")
        global_sql_fallback = bool(plan)

    disclaimer = _VAULT_FALLBACK_DISCLAIMER_ES if global_sql_fallback else None
    degraded = bool(global_sql_fallback)

    home_away_league: dict[int, tuple[str, str, str]] = {}
    for event_id, _b, item, _agg in plan:
        ctx = item["event_context"]
        home_away_league[event_id] = (
            str(ctx.get("home_team") or "Local"),
            str(ctx.get("away_team") or "Visitante"),
            str(ctx.get("league_name") or "Liga"),
        )

    row_payloads: list[dict[str, Any]] = []
    for event_id, _band, item, agg in plan:
        home, away, league = home_away_league[event_id]
        score_v = int(data_completeness_score(agg))
        if global_sql_fallback:
            narr, conf, mmc, msc, pver, dsrc, dhash = suggest_sql_stat_fallback_from_consensus(
                event_id,
                agg.consensus,
                agg.market_coverage,
                home,
                away,
                league,
            )
        elif event_id in ds_resolved:
            narr, conf, mmc, msc, pver, dsrc, dhash = ds_resolved[event_id]
        else:
            oh, od, oa, ov, un = consensus_to_legacy_odds(agg.consensus)
            narr, conf, mmc, msc, pver, dsrc, dhash = suggest_for_snapshot_row(
                event_id,
                oh,
                od,
                oa,
                ov,
                un,
                home,
                away,
                league,
            )
        ref_odds = consensus_decimal_for_canonical_pick(agg.consensus, mmc, msc)
        row_payloads.append(
            {
                "event_id": event_id,
                "score_v": score_v,
                "narr": narr,
                "conf": conf,
                "mmc": mmc,
                "msc": msc,
                "pver": pver,
                "dsrc": dsrc,
                "dhash": dhash,
                "ref_odds": ref_odds,
            }
        )

    mix_order = order_indices_for_top_slate_diversity(
        [str(p["mmc"]) for p in row_payloads],
        top_k=VAULT_POOL_TARGET,
    )
    reordered = [row_payloads[i] for i in mix_order]

    plan_agg_by_eid = {int(eid): agg for eid, _band, item, agg in plan}
    tier_by_event = {
        int(eid): (lt or "").strip().upper() for eid, _ko, _hm, _agg, lt in pool
    }
    hm_by_event = {int(eid): float(hm or 0.1) for eid, _ko, hm, _agg, _lt in pool}

    score_by_event: dict[int, float] = {}
    for p in reordered:
        _eid = int(p["event_id"])
        _agg = plan_agg_by_eid[_eid]
        score_by_event[_eid] = strength_score(
            hm_by_event.get(_eid, 0.1),
            int(p["score_v"]),
            prob_coherence_flag_for_agg(_agg),
        )

    access_map = assign_standard_premium_access(
        ordered_row_payloads=reordered,
        tier_by_event=tier_by_event,
        hm_by_event=hm_by_event,
        score_by_event=score_by_event,
    )

    ranked_pred = sorted(score_by_event.items(), key=lambda x: -x[1])
    predictive_map = assign_predictive_tier([(str(eid), sc) for eid, sc in ranked_pred])

    inserted = 0
    for rank, p in enumerate(reordered, start=1):
        _eid = int(p["event_id"])
        agg_row = plan_agg_by_eid[_eid]
        access_tier = access_map[_eid]
        p_hat, ev_q, _pcf = compute_row_signal_fields(
            agg=agg_row,
            data_completeness=int(p["score_v"]),
            market_canonical=str(p["mmc"]),
            selection_canonical=str(p["msc"]),
        )
        pred_t = predictive_map.get(str(_eid), "medium")
        action_tier_val = "premium" if access_tier == "premium" else "free"

        cur.execute(
            """
            INSERT INTO bt2_daily_picks (
                user_id, event_id, operating_day_key, access_tier,
                pipeline_version, dsr_input_hash, dsr_narrative_es, dsr_confidence_label,
                model_market_canonical, model_selection_canonical, reference_decimal_odds, dsr_source,
                data_completeness_score, slate_rank,
                estimated_hit_probability, evidence_quality, predictive_tier, action_tier
            )
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, event_id, operating_day_key) DO NOTHING
            """,
            (
                user_id,
                _eid,
                odk,
                access_tier,
                p["pver"],
                p["dhash"],
                p["narr"],
                "",
                p["mmc"],
                p["msc"],
                p.get("ref_odds"),
                p["dsrc"],
                p["score_v"],
                rank,
                float(p_hat),
                ev_q,
                pred_t,
                action_tier_val,
            ),
        )
        if cur.rowcount:
            inserted += 1

    _upsert_vault_day_metadata(
        cur,
        user_id,
        odk,
        dsr_signal_degraded=degraded,
        limited_coverage=limited_cov,
        operational_empty_hard=False,
        vault_empty_message_es=None,
        fallback_disclaimer_es=disclaimer,
        future_events_in_window_count=future_ec,
        fallback_eligible_pool_count=fallback_pool_count,
        slate_band_cycle=slate_band_cycle_to_store,
    )
    return inserted


@router.post(
    "/vault/regenerate-slate",
    status_code=200,
    tags=["bt2"],
    response_model=Bt2VaultPicksPageOut,
    response_model_by_alias=True,
)
def bt2_vault_regenerate_slate(user_id: Bt2UserId) -> Bt2VaultPicksPageOut:
    """
    Recompone hasta 20 picks persistidos y devuelve el **mismo cuerpo que GET /vault/picks**
    (un solo round-trip; sin GET adicional).

    Requiere sesión operativa **abierta**. No conserva picks ya tomados en DB (MVP).
    """
    odk = _operating_day_key_for_user(user_id)
    tz_name = _user_timezone(user_id)
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT 1 FROM bt2_operating_sessions
               WHERE user_id = %s::uuid AND operating_day_key = %s AND status = 'open'""",
            (user_id, odk),
        )
        if not cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Abre la estación operativa del día para regenerar la cartelera.",
            )
        cur.execute(
            """SELECT COALESCE(slate_band_cycle, 0) FROM bt2_vault_day_metadata
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        row = cur.fetchone()
        prev_cycle = int(row[0]) if row else 0
        next_cycle = (prev_cycle + 1) % 4
        inserted = _materialize_daily_picks_snapshot(
            cur,
            user_id,
            odk,
            tz_name,
            band_cycle_offset=next_cycle,
            slate_band_cycle_to_store=next_cycle,
            replace_existing_slate=True,
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    logger.info(
        "vault_regenerate_slate ok user=%s day=%s cycle=%s inserted=%s",
        user_id,
        odk,
        next_cycle,
        inserted,
    )
    return _build_bt2_vault_picks_page_out(user_id)


@router.post("/session/open", status_code=201, response_model=SessionOpenOut)
def bt2_session_open(user_id: Bt2UserId) -> SessionOpenOut:
    odk = _operating_day_key_for_user(user_id)
    tz_name = _user_timezone(user_id)
    conn = _db_conn()
    cur = conn.cursor()
    now = datetime.now(tz=timezone.utc)
    try:
        cur.execute(
            """SELECT id FROM bt2_operating_sessions
               WHERE user_id = %s::uuid AND operating_day_key = %s AND status = 'open'""",
            (user_id, odk),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Ya existe una sesión abierta para {odk}")

        _close_orphan_sessions_and_station_penalties(cur, user_id, odk, now, tz_name)
        _apply_grace_unsettled_penalties(cur, user_id, now)

        # Una fila por (user_id, operating_day_key) — el cierre solo pone status=closed.
        # Reabrir el mismo día operativo debe ser UPDATE, no INSERT (evita UniqueViolation).
        cur.execute(
            """SELECT id FROM bt2_operating_sessions
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        existing_row = cur.fetchone()
        if existing_row:
            session_id = int(existing_row[0])
            cur.execute(
                """UPDATE bt2_operating_sessions
                   SET status = 'open',
                       station_opened_at = %s,
                       station_closed_at = NULL,
                       grace_until_iso = NULL
                   WHERE id = %s AND user_id = %s::uuid
                   RETURNING station_opened_at""",
                (now, session_id, user_id),
            )
            upd = cur.fetchone()
            if not upd:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo reabrir la sesión operativa del día.",
                )
            opened_at = upd[0]
        else:
            cur.execute(
                """INSERT INTO bt2_operating_sessions (user_id, operating_day_key, status)
                   VALUES (%s::uuid, %s, 'open')
                   RETURNING id, station_opened_at""",
                (user_id, odk),
            )
            row = cur.fetchone()
            session_id, opened_at = int(row[0]), row[1]

        # Generar snapshot diario de picks (idempotente)
        _generate_daily_picks_snapshot(cur, user_id, odk, tz_name)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return SessionOpenOut(
        session_id=session_id,
        operating_day_key=odk,
        station_opened_at=opened_at.isoformat(),
    )


@router.post(
    "/session/close",
    status_code=200,
    response_model=SessionCloseOut,
    response_model_by_alias=True,
)
def bt2_session_close(user_id: Bt2UserId) -> SessionCloseOut:
    odk = _operating_day_key_for_user(user_id)
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id FROM bt2_operating_sessions
               WHERE user_id = %s::uuid AND operating_day_key = %s AND status = 'open'""",
            (user_id, odk),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No hay sesión abierta para hoy")
        session_id = row[0]

        now = datetime.now(tz=timezone.utc)
        grace = now + timedelta(hours=24)
        cur.execute(
            """UPDATE bt2_operating_sessions
               SET status = 'closed', station_closed_at = %s, grace_until_iso = %s
               WHERE id = %s
               RETURNING id, grace_until_iso""",
            (now, grace, session_id),
        )
        _ = cur.fetchone()

        # US-BE-021 / D-05-018: recompensa por cierre con protocolo (no en cierre huérfano session/open).
        earned_close = 0
        if not _ledger_move_exists(cur, user_id, REASON_SESSION_CLOSE_DISCIPLINE, session_id):
            _append_dp_ledger_move(
                cur,
                user_id,
                SESSION_CLOSE_DISCIPLINE_REWARD_DP,
                REASON_SESSION_CLOSE_DISCIPLINE,
                session_id,
            )
            earned_close = SESSION_CLOSE_DISCIPLINE_REWARD_DP

        conn.commit()

        cur.execute(
            """SELECT COUNT(*) FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'
                 AND DATE(opened_at AT TIME ZONE 'UTC') = %s""",
            (user_id, date.fromisoformat(odk)),
        )
        pending = int(cur.fetchone()[0])
        dp_balance_after = _get_dp_balance(cur, user_id)
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return SessionCloseOut(
        session_id=session_id,
        status="closed",
        grace_until_iso=grace.isoformat(),
        pending_settlements=pending,
        earned_dp_session_close=earned_close,
        dp_balance_after=dp_balance_after,
    )


@router.post(
    "/dev/reset-operating-day-for-tests",
    response_model=Bt2DevResetOperatingDayOut,
    response_model_by_alias=True,
    tags=["bt2-dev"],
)
def bt2_dev_reset_operating_day_for_tests(user_id: Bt2UserId) -> Bt2DevResetOperatingDayOut:
    """
    Solo desarrollo: borra snapshot de bóveda del **día operativo actual** del usuario,
    desbloqueos premium de ese día y cierra la sesión operativa en BD **sin** acreditar
    DP de cierre (UPDATE directo). Así el siguiente `POST /bt2/session/open` vuelve a
    ejecutar el pipeline de snapshot (DSR / fallback) sin usar curl admin.

    Requiere `BT2_DEV_OPERATING_DAY_RESET=1` en `.env`; si no, 404 (no aparece en OpenAPI
    de clientes que ignoren rutas ocultas).
    """
    if not bt2_settings.bt2_dev_operating_day_reset:
        raise HTTPException(status_code=404, detail="Not found")

    odk = _operating_day_key_for_user(user_id)
    tz_name = _user_timezone(user_id)
    now = datetime.now(timezone.utc)
    grace = now + timedelta(hours=24)

    conn = _db_conn()
    cur = conn.cursor()
    session_closed = False
    picks_deleted = 0
    sm_ok = 0
    sm_log: list[str] = []
    pool_event_ids: list[int] = []
    try:
        sm_ok, sm_log, pool_event_ids = refresh_raw_sportmonks_for_value_pool_today(
            cur,
            tz_name=tz_name,
            sportmonks_api_key=bt2_settings.sportmonks_api_key,
            priority_league_ids_csv=bt2_settings.bt2_priority_league_ids,
        )
        cur.execute(
            """DELETE FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        cur.execute(
            """DELETE FROM bt2_daily_picks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        picks_deleted = cur.rowcount
        cur.execute(
            """DELETE FROM bt2_vault_day_metadata
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        cur.execute(
            """UPDATE bt2_operating_sessions
               SET status = 'closed', station_closed_at = %s, grace_until_iso = %s
               WHERE user_id = %s::uuid AND operating_day_key = %s AND status = 'open'
               RETURNING id""",
            (now, grace, user_id, odk),
        )
        session_closed = cur.fetchone() is not None
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    sfs_auto: Optional[dict[str, Any]] = None
    if pool_event_ids and getattr(bt2_settings, "bt2_sfs_auto_ingest_enabled", True):
        try:
            sfs_auto = run_sfs_auto_ingest_after_cdm_fetch(pool_event_ids)
        except Exception as exc:
            logger.warning("[bt2-dev-reset] SFS auto-ingest falló: %s", exc)
            sfs_auto = {"skipped": False, "error": str(exc)}
    elif pool_event_ids and not getattr(bt2_settings, "bt2_sfs_auto_ingest_enabled", True):
        sfs_auto = {"skipped": True, "reason": "bt2_sfs_auto_ingest_disabled"}

    sfs_line = ""
    if isinstance(sfs_auto, dict):
        if sfs_auto.get("error"):
            sfs_line = f" SFS ingest error: {sfs_auto.get('error')!s}."
        elif sfs_auto.get("skipped") and sfs_auto.get("reason") == "bt2_sfs_auto_ingest_disabled":
            sfs_line = " SFS ingest omitido (BT2_SFS_AUTO_INGEST_ENABLED=false)."
        elif sfs_auto.get("snapshots_upserted") is not None:
            su = sfs_auto.get("snapshots_upserted")
            sj = sfs_auto.get("skipped_no_join")
            sfs_line = f" SFS ok: snapshots={su} sin_join={sj}."

    msg = (
        f"Día {odk}: SM raw refrescados {sm_ok} fixture(s); "
        f"eliminadas {picks_deleted} filas de bóveda; "
        f"servidor {'cerró sesión abierta' if session_closed else 'sin sesión abierta (OK)'}."
        f"{sfs_line} "
        f"Abrí la bóveda o POST session/open para regenerar snapshot (ds_input + prob_coherence + DSR)."
    )
    return Bt2DevResetOperatingDayOut(
        ok=True,
        operating_day_key=odk,
        daily_picks_deleted=picks_deleted,
        server_session_closed=session_closed,
        sm_fixtures_refreshed=sm_ok,
        sm_refresh_log=sm_log[:25],
        sfs_auto_ingest=sfs_auto,
        message_es=msg,
    )


# ── Settings schemas (Sprint 04 US-BE-012) ────────────────────────────────────

class SettingsOut(BaseModel):
    risk_per_pick_pct: float
    dp_unlock_premium_threshold: int
    timezone: str
    display_currency: str


class SettingsIn(BaseModel):
    risk_per_pick_pct: Optional[float] = None
    dp_unlock_premium_threshold: Optional[int] = None
    timezone: Optional[str] = None


class DpBalanceOut(BaseModel):
    dp_balance: int
    pending_settlements: int
    behavioral_block_count: int


class OnboardingPhaseACompleteOut(BaseModel):
    """Respuesta idempotente: primera vez inserta +250 en bt2_dp_ledger."""

    dp_balance: int
    granted_dp: int


class DpLedgerEntry(BaseModel):
    id: int
    delta_dp: int
    reason: str
    reference_id: Optional[int]
    created_at: str
    balance_after_dp: int


class DpLedgerOut(BaseModel):
    entries: List[DpLedgerEntry]


# ── Settings + DP endpoints (T-102, T-103) ────────────────────────────────────

def _ensure_user_settings(cur, user_id: str) -> None:
    """Crea bt2_user_settings con defaults si no existe (US-BE-012 Regla 4)."""
    cur.execute(
        "INSERT INTO bt2_user_settings (user_id) VALUES (%s::uuid) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )


@router.get("/user/settings", response_model=SettingsOut)
def bt2_get_settings(user_id: Bt2UserId) -> SettingsOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        _ensure_user_settings(cur, user_id)
        cur.execute(
            """SELECT risk_per_pick_pct, dp_unlock_premium_threshold, timezone, display_currency
               FROM bt2_user_settings WHERE user_id = %s::uuid""",
            (user_id,),
        )
        row = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return SettingsOut(
        risk_per_pick_pct=float(row[0]),
        dp_unlock_premium_threshold=int(row[1]),
        timezone=row[2],
        display_currency=row[3],
    )


@router.put("/user/settings", response_model=SettingsOut)
def bt2_update_settings(body: SettingsIn, user_id: Bt2UserId) -> SettingsOut:
    if body.risk_per_pick_pct is not None:
        if not (0.5 <= body.risk_per_pick_pct <= 10.0):
            raise HTTPException(status_code=422, detail="risk_per_pick_pct debe estar entre 0.5 y 10.0")
    if body.dp_unlock_premium_threshold is not None:
        if not (10 <= body.dp_unlock_premium_threshold <= 500):
            raise HTTPException(status_code=422, detail="dp_unlock_premium_threshold debe estar entre 10 y 500")

    conn = _db_conn()
    cur = conn.cursor()
    try:
        _ensure_user_settings(cur, user_id)
        updates = []
        params = []
        if body.risk_per_pick_pct is not None:
            updates.append("risk_per_pick_pct = %s")
            params.append(body.risk_per_pick_pct)
        if body.dp_unlock_premium_threshold is not None:
            updates.append("dp_unlock_premium_threshold = %s")
            params.append(body.dp_unlock_premium_threshold)
        if body.timezone is not None:
            updates.append("timezone = %s")
            params.append(body.timezone[:50])

        if updates:
            params.append(user_id)
            cur.execute(
                f"UPDATE bt2_user_settings SET {', '.join(updates)} WHERE user_id = %s::uuid",
                params,
            )

        cur.execute(
            """SELECT risk_per_pick_pct, dp_unlock_premium_threshold, timezone, display_currency
               FROM bt2_user_settings WHERE user_id = %s::uuid""",
            (user_id,),
        )
        row = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return SettingsOut(
        risk_per_pick_pct=float(row[0]),
        dp_unlock_premium_threshold=int(row[1]),
        timezone=row[2],
        display_currency=row[3],
    )


@router.post(
    "/user/onboarding-phase-a-complete",
    response_model=OnboardingPhaseACompleteOut,
    status_code=200,
)
def bt2_onboarding_phase_a_complete(user_id: Bt2UserId) -> OnboardingPhaseACompleteOut:
    """Acredita una sola vez el bono de fase A en el ledger; el saldo es siempre la suma del ledger."""
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT 1 FROM bt2_dp_ledger
               WHERE user_id = %s::uuid AND reason = %s
               LIMIT 1""",
            (user_id, ONBOARDING_PHASE_A_LEDGER_REASON),
        )
        already = cur.fetchone() is not None
        granted = 0
        if not already:
            balance_before = _get_dp_balance(cur, user_id)
            new_balance = balance_before + ONBOARDING_PHASE_A_DP_GRANT
            cur.execute(
                """INSERT INTO bt2_dp_ledger
                   (user_id, delta_dp, reason, reference_id, balance_after_dp)
                   VALUES (%s::uuid, %s, %s, NULL, %s)""",
                (
                    user_id,
                    ONBOARDING_PHASE_A_DP_GRANT,
                    ONBOARDING_PHASE_A_LEDGER_REASON,
                    new_balance,
                ),
            )
            granted = ONBOARDING_PHASE_A_DP_GRANT
        conn.commit()
        dp_balance = _get_dp_balance(cur, user_id)
    finally:
        cur.close()
        conn.close()

    return OnboardingPhaseACompleteOut(dp_balance=dp_balance, granted_dp=granted)


@router.get("/user/dp-balance", response_model=DpBalanceOut)
def bt2_dp_balance(user_id: Bt2UserId) -> DpBalanceOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        dp_balance = _get_dp_balance(cur, user_id)

        # Picks open de días anteriores (pendientes de liquidar)
        odk = _operating_day_key_for_user(user_id)
        cur.execute(
            """SELECT COUNT(*) FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'
                 AND DATE(opened_at AT TIME ZONE 'UTC') < %s""",
            (user_id, date.fromisoformat(odk)),
        )
        pending = int(cur.fetchone()[0])

        cur.execute(
            "SELECT COUNT(*) FROM bt2_behavioral_blocks WHERE user_id = %s::uuid",
            (user_id,),
        )
        blocks = int(cur.fetchone()[0])
    finally:
        cur.close()
        conn.close()

    return DpBalanceOut(
        dp_balance=dp_balance,
        pending_settlements=pending,
        behavioral_block_count=blocks,
    )


@router.get("/user/dp-ledger", response_model=DpLedgerOut)
def bt2_dp_ledger(user_id: Bt2UserId, limit: int = Query(default=20, ge=1, le=200)) -> DpLedgerOut:
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """SELECT id, delta_dp, reason, reference_id, created_at, balance_after_dp
               FROM bt2_dp_ledger
               WHERE user_id = %s::uuid
               ORDER BY created_at DESC
               LIMIT %s""",
            (user_id, limit),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return DpLedgerOut(
        entries=[
            DpLedgerEntry(
                id=r["id"],
                delta_dp=r["delta_dp"],
                reason=r["reason"],
                reference_id=r["reference_id"],
                created_at=r["created_at"].isoformat(),
                balance_after_dp=r["balance_after_dp"],
            )
            for r in rows
        ]
    )


# ── Diagnóstico conductual (US-BE-016) ───────────────────────────────────────

@router.post("/user/diagnostic", status_code=200, response_model=DiagnosticOut, response_model_by_alias=True)
def bt2_post_diagnostic(body: DiagnosticIn, user_id: Bt2UserId) -> DiagnosticOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO bt2_user_diagnostics
               (user_id, operator_profile, system_integrity, answers_hash)
               VALUES (%s::uuid, %s, %s, %s)
               RETURNING operator_profile, system_integrity, created_at""",
            (user_id, body.operator_profile, body.system_integrity, body.answers_hash),
        )
        row = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return DiagnosticOut(
        operator_profile=row[0],
        system_integrity=float(row[1]),
        completed_at=row[2].isoformat(),
    )


@router.get("/user/diagnostic", status_code=200, response_model=DiagnosticOut, response_model_by_alias=True)
def bt2_get_diagnostic(user_id: Bt2UserId) -> DiagnosticOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT operator_profile, system_integrity, created_at
               FROM bt2_user_diagnostics
               WHERE user_id = %s::uuid
               ORDER BY created_at DESC
               LIMIT 1""",
            (user_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="El usuario aún no ha completado el diagnóstico conductual")

    return DiagnosticOut(
        operator_profile=row[0],
        system_integrity=float(row[1]),
        completed_at=row[2].isoformat(),
    )


def _require_bt2_admin(
    x_bt2_admin_key: Optional[str] = Header(None, alias="X-BT2-Admin-Key"),
) -> None:
    """US-BE-028 — MVP admin (D-06-015); sustituir por rol de usuario en S6.1+."""
    # Usar bt2_settings: el .env raíz solo lo hidrata Pydantic en campos del modelo;
    # BT2_ADMIN_API_KEY no llegaba a os.environ y la clave parecía “no funcionar”.
    expected = (bt2_settings.bt2_admin_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin analytics deshabilitado: defina BT2_ADMIN_API_KEY en el entorno.",
        )
    if (x_bt2_admin_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Clave admin inválida")


@router.get(
    "/admin/analytics/dsr-day",
    response_model=Bt2AdminDsrDayOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_analytics_dsr_day(
    operating_day_key: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description="YYYY-MM-DD día operativo a auditar.",
    ),
) -> Bt2AdminDsrDayOut:
    """
    US-BE-028 / D-06-004 — agregados y filas de auditoría para vista admin precisión DSR.
    Header: **X-BT2-Admin-Key** = `BT2_ADMIN_API_KEY`.
    """
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """SELECT COUNT(DISTINCT event_id) AS n FROM bt2_daily_picks
               WHERE operating_day_key = %s""",
            (operating_day_key,),
        )
        n_events = int(cur.fetchone()["n"] or 0)

        cur.execute(
            """
            SELECT DISTINCT ON (p.id)
                   p.id AS pick_id, p.user_id::text AS user_id, p.event_id,
                   dp.operating_day_key, p.status, p.model_prediction_result,
                   p.model_market_canonical, p.model_selection_canonical
            FROM bt2_picks p
            INNER JOIN bt2_daily_picks dp
              ON dp.user_id = p.user_id AND dp.event_id = p.event_id
             AND dp.operating_day_key = %s
            WHERE p.settled_at IS NOT NULL
            ORDER BY p.id, dp.suggested_at DESC
            LIMIT 500
            """,
            (operating_day_key,),
        )
        audit_rows = cur.fetchall()

        cur.execute(
            """
            SELECT p.model_prediction_result AS r, COUNT(*) AS c
            FROM bt2_picks p
            INNER JOIN bt2_daily_picks dp
              ON dp.user_id = p.user_id AND dp.event_id = p.event_id
             AND dp.operating_day_key = %s
            WHERE p.settled_at IS NOT NULL AND p.model_prediction_result IS NOT NULL
            GROUP BY p.model_prediction_result
            """,
            (operating_day_key,),
        )
        agg = {str(row["r"]): int(row["c"]) for row in cur.fetchall()}
    finally:
        cur.close()
        conn.close()

    hits = agg.get("hit", 0)
    misses = agg.get("miss", 0)
    voids = agg.get("void", 0)
    na_c = agg.get("n_a", 0)
    denom = hits + misses
    rate = round(100.0 * hits / denom, 2) if denom else None
    settled_model = hits + misses + voids + na_c

    summary_human = (
        f"Día operativo {operating_day_key}: {n_events} eventos distintos publicados en snapshots. "
        f"Picks liquidados vinculados a ese día: {len(audit_rows)} filas de auditoría. "
        f"Modelo — aciertos: {hits}, fallos: {misses}, void: {voids}, sin dato: {na_c}."
    )
    if rate is not None:
        summary_human += f" Tasa de acierto (aciertos / aciertos+fallos): {rate} %."
    else:
        summary_human += " Aún no hay aciertos+fallos para calcular tasa."

    rows_out = [
        Bt2AdminDsrAuditRowOut(
            pick_id=int(r["pick_id"]),
            user_id=r["user_id"],
            event_id=int(r["event_id"]),
            operating_day_key=r["operating_day_key"],
            status=r["status"],
            model_prediction_result=r.get("model_prediction_result"),
            model_market_canonical=r.get("model_market_canonical"),
            model_selection_canonical=r.get("model_selection_canonical"),
        )
        for r in audit_rows
    ]

    return Bt2AdminDsrDayOut(
        summary=Bt2AdminDsrDaySummaryOut(
            operating_day_key=operating_day_key,
            distinct_events_in_vault=n_events,
            picks_settled_with_model=settled_model,
            model_hits=hits,
            model_misses=misses,
            model_voids=voids,
            model_na=na_c,
            hit_rate_pct=rate,
            summary_human_es=summary_human,
        ),
        audit_rows=rows_out,
    )


@router.get(
    "/admin/analytics/official-evaluation-loop",
    response_model=Bt2AdminOfficialEvaluationLoopOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_official_evaluation_loop(
    operating_day_key: Optional[str] = Query(
        None,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description="Opcional YYYY-MM-DD: acota métricas a picks de ese día operativo.",
    ),
) -> Bt2AdminOfficialEvaluationLoopOut:
    """
    T-233 / base US-BE-052 — contadores del loop de evaluación oficial (sin mezclar pendientes
    ni no evaluables en el hit rate). Header: **X-BT2-Admin-Key**.
    """
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        raw = fetch_official_evaluation_loop_metrics(
            cur, operating_day_key=operating_day_key
        )
    finally:
        cur.close()
        conn.close()
    return Bt2AdminOfficialEvaluationLoopOut(**raw)


@router.get(
    "/admin/analytics/fase1-operational-summary",
    response_model=Bt2AdminFase1OperationalSummaryOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_fase1_operational_summary(
    operating_day_key: Optional[str] = Query(
        None,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description=(
            "YYYY-MM-DD — misma ventana para pool, loop y buckets. "
            "Omitir si `accumulated=true`."
        ),
    ),
    accumulated: bool = Query(
        False,
        alias="accumulated",
        description=(
            "Si true: métricas acumuladas sobre todos los picks/eventos históricos "
            "(sin filtrar por día). Ignora `operatingDayKey`."
        ),
    ),
) -> Bt2AdminFase1OperationalSummaryOut:
    """
    US-BE-052 / T-238–T-240 — tres bloques: cobertura pool (auditoría), loop oficial, precisión
    por mercado y por confianza. Header: **X-BT2-Admin-Key**.
    """
    if not accumulated and not (operating_day_key and len(operating_day_key) == 10):
        raise HTTPException(
            status_code=422,
            detail="operatingDayKey (YYYY-MM-DD) es obligatorio salvo accumulated=true",
        )
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        raw = build_fase1_operational_summary(
            cur,
            operating_day_key,
            accumulated=accumulated,
        )
    finally:
        cur.close()
        conn.close()
    return Bt2AdminFase1OperationalSummaryOut(
        operating_day_key=raw["operating_day_key"],
        pool_coverage=Bt2AdminPoolCoverageOut(**raw["pool_coverage"]),
        official_evaluation_loop=Bt2AdminOfficialEvaluationLoopOut(
            **raw["official_evaluation_loop"]
        ),
        precision_by_market=[
            Bt2AdminOfficialPrecisionBucketOut(**x) for x in raw["precision_by_market"]
        ],
        precision_by_confidence=[
            Bt2AdminOfficialPrecisionBucketOut(**x) for x in raw["precision_by_confidence"]
        ],
        summary_human_es=raw["summary_human_es"],
        pool_eligibility_min_families_required=raw["pool_eligibility_min_families_required"],
        pool_eligibility_official_reference_s63=raw["pool_eligibility_official_reference_s63"],
        pool_eligibility_observability_relaxed=raw["pool_eligibility_observability_relaxed"],
        pool_eligibility_config_note_es=raw.get("pool_eligibility_config_note_es") or "",
    )


@router.get(
    "/admin/analytics/f2-pool-eligibility-metrics",
    response_model=Bt2AdminF2PoolMetricsOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_f2_pool_eligibility_metrics(
    operating_day_key: Optional[str] = Query(
        None,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description=(
            "Opcional: un solo día YYYY-MM-DD — eventos F2 cuyo kickoff (fecha Bogotá) cae ese día."
        ),
    ),
    days: int = Query(
        30,
        ge=1,
        le=366,
        alias="days",
        description=(
            "Ventana rolling en días calendario Bogotá sobre kickoff de bt2_events en 5 ligas F2; "
            "fin anclado a MAX(operating_day_key) en picks o hoy Bogota si no hay picks."
        ),
    ),
) -> Bt2AdminF2PoolMetricsOut:
    """
    T-263 — KPI F2: `pool_eligibility_rate_official` vs relajado (min familias = 1), umbrales 60/40.
    """
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        raw = build_f2_pool_eligibility_metrics(
            cur,
            operating_day_key=operating_day_key,
            days=days,
        )
    finally:
        cur.close()
        conn.close()
    return Bt2AdminF2PoolMetricsOut(
        league_bt2_ids_resolved=list(raw.get("league_bt2_ids_resolved") or []),
        window_from=raw.get("window_from"),
        window_to=raw.get("window_to"),
        operating_day_key_filter=raw.get("operating_day_key_filter"),
        metrics_global=dict(raw.get("metrics_global") or {}),
        metrics_by_league=list(raw.get("metrics_by_league") or []),
        thresholds=dict(raw.get("thresholds") or {}),
        insufficient_market_families_dominant=raw.get("insufficient_market_families_dominant"),
        note_es=raw.get("note_es") or "",
    )


@router.post(
    "/admin/operations/refresh-cdm-from-sm-for-operating-day",
    response_model=Bt2AdminRefreshCdmFromSmOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_post_refresh_cdm_from_sm_for_operating_day(
    operating_day_key: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description="Mismo YYYY-MM-DD que la vista Fase 1 (picks sugeridos de ese día).",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Máximo de eventos distintos (bt2_events) a refrescar.",
    ),
    run_official_evaluation: bool = Query(
        True,
        alias="runOfficialEvaluation",
        description="Si true, tras actualizar CDM ejecuta backfill+evaluate del job oficial.",
    ),
) -> Bt2AdminRefreshCdmFromSmOut:
    """
    SportMonks en vivo → `raw_sportmonks_fixtures` → normaliza `bt2_events` (resultados/status).

    No depende del snapshot de bóveda. Requiere `SPORTMONKS_API_KEY` en el servidor.
    Tras el refresh, opcionalmente cierra filas `pending_result` en `bt2_pick_official_evaluation`
    usando la verdad CDM actualizada.
    """
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        raw = admin_refresh_cdm_from_sm_for_operating_day(
            cur,
            operating_day_key=operating_day_key.strip(),
            sportmonks_api_key=bt2_settings.sportmonks_api_key,
            limit=limit,
            run_official_evaluation=run_official_evaluation,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return Bt2AdminRefreshCdmFromSmOut(**raw)


_BT2_ADMIN_MONITOR_MAX_DAYS = 366
_BT2_ADMIN_MONITOR_SM_SYNC_MAX_SPAN_DAYS = 31


@router.get(
    "/admin/analytics/monitor-resultados",
    response_model=Bt2AdminMonitorResultadosOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_monitor_resultados(
    operating_day_key_from: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKeyFrom",
        description="Inicio inclusive YYYY-MM-DD (`operating_day_key` en bt2_daily_picks).",
    ),
    operating_day_key_to: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKeyTo",
        description="Fin inclusive YYYY-MM-DD.",
    ),
    monitor_user_id: Optional[str] = Query(
        None,
        alias="monitorUserId",
        description=(
            "UUID del operador: si se envía, `yours` agrega solo picks operados "
            "(bt2_picks el mismo día operativo en America/Bogota)."
        ),
    ),
    sync_from_sportmonks: bool = Query(
        False,
        alias="syncFromSportmonks",
        description=(
            "Si true: antes de responder, refresca desde SportMonks cada evento con picks "
            "en el rango [from,to], actualiza bt2_events y ejecuta evaluación oficial pending. "
            "Usa cuota SM; máximo "
            + str(_BT2_ADMIN_MONITOR_SM_SYNC_MAX_SPAN_DAYS)
            + " días de rango."
        ),
    ),
    sm_sync_event_limit: int = Query(
        250,
        ge=1,
        le=500,
        alias="smSyncEventLimit",
        description="Máximo eventos distintos a refrescar cuando syncFromSportmonks=true.",
    ),
    rows_offset: int = Query(0, ge=0, alias="rowsOffset"),
    rows_limit: int = Query(1500, ge=1, le=3000, alias="rowsLimit"),
    outcome_filter: Optional[str] = Query(
        None,
        alias="outcomeFilter",
        description="Filtra filas por resultado UI: si | no | pendiente | void | ne.",
    ),
    market_substring: Optional[str] = Query(
        None,
        alias="marketSubstring",
        description="Substring insensible a mayúsculas sobre mercado canónico/materializado.",
    ),
    search: Optional[str] = Query(
        None,
        description="Busca en nombres local/visitante (ILIKE).",
    ),
) -> Bt2AdminMonitorResultadosOut:
    """
    Monitor de resultados — evaluación oficial por fila de bóveda (`bt2_daily_picks`).

    Tasa del sistema = hits / (hits + misses) sobre filas con estado evaluated_hit|evaluated_miss.
    Pendientes, void y N.E. no entran en el denominador.
    Header: **X-BT2-Admin-Key** = `BT2_ADMIN_API_KEY`.
    """
    try:
        d0 = date.fromisoformat(operating_day_key_from)
        d1 = date.fromisoformat(operating_day_key_to)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="operatingDayKeyFrom y operatingDayKeyTo deben ser YYYY-MM-DD válidos.",
        )
    if d0 > d1:
        raise HTTPException(
            status_code=400,
            detail="operatingDayKeyFrom no puede ser posterior a operatingDayKeyTo.",
        )
    span = (d1 - d0).days + 1
    if span > _BT2_ADMIN_MONITOR_MAX_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Rango máximo {_BT2_ADMIN_MONITOR_MAX_DAYS} días.",
        )
    if sync_from_sportmonks and span > _BT2_ADMIN_MONITOR_SM_SYNC_MAX_SPAN_DAYS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"syncFromSportmonks: rango máximo {_BT2_ADMIN_MONITOR_SM_SYNC_MAX_SPAN_DAYS} días "
                f"(recibido {span}). Acortá el periodo o usa sync en un solo día."
            ),
        )

    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        sm_sync = {
            "attempted": False,
            "ok": True,
            "message_es": "",
            "fixtures_targeted": 0,
            "unique_fixtures_processed": 0,
            "closed_pending_to_final": None,
        }
        if sync_from_sportmonks:
            rr = admin_refresh_cdm_from_sm_for_daily_pick_day_range(
                cur,
                operating_day_key_from=operating_day_key_from,
                operating_day_key_to=operating_day_key_to,
                sportmonks_api_key=bt2_settings.sportmonks_api_key,
                limit=int(sm_sync_event_limit),
                run_official_evaluation=True,
            )
            ev = rr.get("official_evaluation") or {}
            sm_sync = {
                "attempted": True,
                "ok": bool(rr.get("ok")),
                "message_es": str(rr.get("message_es") or ""),
                "fixtures_targeted": int(rr.get("fixtures_targeted") or 0),
                "unique_fixtures_processed": int(rr.get("unique_sportmonks_fixtures_processed") or 0),
                "closed_pending_to_final": ev.get("closed_to_final_this_run"),
            }
        raw = build_monitor_resultados_payload(
            cur,
            operating_day_key_from=operating_day_key_from,
            operating_day_key_to=operating_day_key_to,
            monitor_user_id=monitor_user_id,
            rows_limit=int(rows_limit),
            rows_offset=int(rows_offset),
            outcome_filter=outcome_filter,
            market_substring=market_substring,
            search=search,
        )
        raw["sm_sync"] = sm_sync
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return Bt2AdminMonitorResultadosOut.model_validate(raw)


@router.get(
    "/admin/analytics/backtest-replay",
    response_model=Bt2AdminBacktestReplayOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_analytics_backtest_replay(
    operating_day_key_from: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKeyFrom",
        description="Inicio inclusive YYYY-MM-DD (día operativo America/Bogota).",
    ),
    operating_day_key_to: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKeyTo",
        description="Fin inclusive YYYY-MM-DD.",
    ),
    max_events_per_day: Optional[int] = Query(
        None,
        ge=1,
        le=80,
        alias="maxEventsPerDay",
        description="Techo de eventos por día (replay); default BT2_BACKTEST_MAX_EVENTS_PER_DAY.",
    ),
) -> Bt2AdminBacktestReplayOut:
    """
    Replay ciego: reconstruye ds_input desde Postgres con corte de cuotas por día, ejecuta DSR sin
    fecha real ni marcadores en el prompt, y puntúa contra CDM persistido.

    Header: **X-BT2-Admin-Key** = `BT2_ADMIN_API_KEY`.
    """
    try:
        d0 = date.fromisoformat(operating_day_key_from.strip())
        d1 = date.fromisoformat(operating_day_key_to.strip())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="operatingDayKeyFrom y operatingDayKeyTo deben ser YYYY-MM-DD válidos.",
        )
    if d0 > d1:
        raise HTTPException(
            status_code=400,
            detail="operatingDayKeyFrom no puede ser posterior a operatingDayKeyTo.",
        )

    max_span = int(getattr(bt2_settings, "bt2_backtest_max_span_days", 31) or 31)
    default_ev = int(getattr(bt2_settings, "bt2_backtest_max_events_per_day", 20) or 20)
    max_ev = int(max_events_per_day) if max_events_per_day is not None else default_ev

    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        try:
            raw = build_backtest_replay_payload(
                cur,
                operating_day_key_from=operating_day_key_from.strip(),
                operating_day_key_to=operating_day_key_to.strip(),
                max_events_per_day=max_ev,
                max_span_days=max_span,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return Bt2AdminBacktestReplayOut.model_validate(raw)


_BT2_ADMIN_DSR_RANGE_MAX_DAYS = 366


def _bt2_admin_dsr_day_summary_from_counts(
    operating_day_key: str,
    n_events: int,
    agg: dict,
) -> Bt2AdminDsrDaySummaryOut:
    hits = int(agg.get("hit", 0))
    misses = int(agg.get("miss", 0))
    voids = int(agg.get("void", 0))
    na_c = int(agg.get("n_a", 0))
    denom = hits + misses
    rate = round(100.0 * hits / denom, 2) if denom else None
    settled_model = hits + misses + voids + na_c
    summary_human = (
        f"Día {operating_day_key}: {n_events} eventos en bóveda. "
        f"Liquidados con modelo: {settled_model} "
        f"(aciertos {hits}, fallos {misses}, void {voids}, N/D {na_c})."
    )
    if rate is not None:
        summary_human += f" Tasa hit/(hit+miss): {rate} %."
    else:
        summary_human += " Sin par hit+miss para tasa."
    return Bt2AdminDsrDaySummaryOut(
        operating_day_key=operating_day_key,
        distinct_events_in_vault=n_events,
        picks_settled_with_model=settled_model,
        model_hits=hits,
        model_misses=misses,
        model_voids=voids,
        model_na=na_c,
        hit_rate_pct=rate,
        summary_human_es=summary_human,
    )


@router.get(
    "/admin/analytics/dsr-range",
    response_model=Bt2AdminDsrRangeOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_analytics_dsr_range(
    from_operating_day_key: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="fromOperatingDayKey",
        description="Inicio inclusive YYYY-MM-DD.",
    ),
    to_operating_day_key: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="toOperatingDayKey",
        description="Fin inclusive YYYY-MM-DD.",
    ),
) -> Bt2AdminDsrRangeOut:
    """
    Serie diaria de mismos KPIs que `dsr-day` + totales del rango.
    Header: **X-BT2-Admin-Key** = `BT2_ADMIN_API_KEY`.
    """
    try:
        d0 = date.fromisoformat(from_operating_day_key)
        d1 = date.fromisoformat(to_operating_day_key)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="fromOperatingDayKey y toOperatingDayKey deben ser YYYY-MM-DD válidos.",
        )
    if d0 > d1:
        raise HTTPException(
            status_code=400,
            detail="fromOperatingDayKey no puede ser posterior a toOperatingDayKey.",
        )
    span = (d1 - d0).days + 1
    if span > _BT2_ADMIN_DSR_RANGE_MAX_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Rango máximo {_BT2_ADMIN_DSR_RANGE_MAX_DAYS} días.",
        )

    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT operating_day_key AS odk, COUNT(DISTINCT event_id)::int AS n
            FROM bt2_daily_picks
            WHERE operating_day_key >= %s AND operating_day_key <= %s
            GROUP BY operating_day_key
            """,
            (from_operating_day_key, to_operating_day_key),
        )
        events_by_day = {str(r["odk"]): int(r["n"]) for r in cur.fetchall()}

        cur.execute(
            """
            SELECT dp.operating_day_key AS odk,
                   p.model_prediction_result AS r,
                   COUNT(*)::int AS c
            FROM bt2_picks p
            INNER JOIN bt2_daily_picks dp
              ON dp.user_id = p.user_id AND dp.event_id = p.event_id
            WHERE p.settled_at IS NOT NULL
              AND p.model_prediction_result IS NOT NULL
              AND dp.operating_day_key >= %s
              AND dp.operating_day_key <= %s
            GROUP BY dp.operating_day_key, p.model_prediction_result
            """,
            (from_operating_day_key, to_operating_day_key),
        )
        raw_rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    agg_by_day: dict[str, dict[str, int]] = {}
    for row in raw_rows:
        odk = str(row["odk"])
        rkey = str(row["r"])
        c = int(row["c"])
        if odk not in agg_by_day:
            agg_by_day[odk] = {}
        agg_by_day[odk][rkey] = agg_by_day[odk].get(rkey, 0) + c

    days_out: List[Bt2AdminDsrDaySummaryOut] = []
    total_hits = total_misses = total_voids = total_na = 0
    sum_events_daily = 0
    days_with_settled = 0
    d = d0
    while d <= d1:
        odk = d.isoformat()
        n_ev = events_by_day.get(odk, 0)
        agg = agg_by_day.get(odk, {})
        summary = _bt2_admin_dsr_day_summary_from_counts(odk, n_ev, agg)
        days_out.append(summary)
        total_hits += summary.model_hits
        total_misses += summary.model_misses
        total_voids += summary.model_voids
        total_na += summary.model_na
        sum_events_daily += n_ev
        if summary.picks_settled_with_model > 0:
            days_with_settled += 1
        d += timedelta(days=1)

    settled_all = total_hits + total_misses + total_voids + total_na
    g_denom = total_hits + total_misses
    g_rate = round(100.0 * total_hits / g_denom, 2) if g_denom else None
    totals_human = (
        f"Rango {from_operating_day_key} … {to_operating_day_key} ({span} días): "
        f"{days_with_settled} días con al menos una medición modelo. "
        f"Picks liquidados con modelo (total filas): {settled_all}. "
        f"Aciertos {total_hits}, fallos {total_misses}, void {total_voids}, N/D {total_na}."
    )
    if g_rate is not None:
        totals_human += f" Tasa global hit/(hit+miss): {g_rate} %."
    else:
        totals_human += " Sin par hit+miss global."

    totals = Bt2AdminDsrRangeTotalsOut(
        day_count=span,
        days_with_settled_model=days_with_settled,
        sum_distinct_events_daily=sum_events_daily,
        picks_settled_with_model=settled_all,
        model_hits=total_hits,
        model_misses=total_misses,
        model_voids=total_voids,
        model_na=total_na,
        hit_rate_pct=g_rate,
        summary_human_es=totals_human,
    )

    return Bt2AdminDsrRangeOut(
        from_operating_day_key=from_operating_day_key,
        to_operating_day_key=to_operating_day_key,
        days=days_out,
        totals=totals,
    )


@router.get(
    "/admin/analytics/vault-pick-distribution",
    response_model=Bt2AdminVaultPickDistributionOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_vault_pick_distribution(
    operating_day_key: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description="YYYY-MM-DD día operativo.",
    ),
) -> Bt2AdminVaultPickDistributionOut:
    """
    US-BE-035 / T-183 — conteos por `dsr_confidence_label`, `dsr_source` y buckets de `data_completeness_score`.
    Header: **X-BT2-Admin-Key** = `BT2_ADMIN_API_KEY`.
    """
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(dsr_confidence_label), ''), '(sin etiqueta)') AS k,
                   COUNT(*)::int AS c
            FROM bt2_daily_picks
            WHERE operating_day_key = %s
            GROUP BY 1
            ORDER BY c DESC
            """,
            (operating_day_key,),
        )
        by_conf = [
            Bt2AdminCountRowOut(key=str(r["k"]), count=int(r["c"])) for r in cur.fetchall()
        ]
        cur.execute(
            """
            SELECT dsr_source AS k, COUNT(*)::int AS c
            FROM bt2_daily_picks
            WHERE operating_day_key = %s
            GROUP BY dsr_source
            ORDER BY c DESC
            """,
            (operating_day_key,),
        )
        by_src = [
            Bt2AdminCountRowOut(key=str(r["k"]), count=int(r["c"])) for r in cur.fetchall()
        ]
        cur.execute(
            """
            SELECT COALESCE(data_completeness_score, -1) AS b, COUNT(*)::int AS c
            FROM bt2_daily_picks
            WHERE operating_day_key = %s
            GROUP BY 1
            ORDER BY b ASC
            """,
            (operating_day_key,),
        )
        score_b = [
            Bt2AdminScoreBucketOut(score_bucket=int(r["b"]), count=int(r["c"]))
            for r in cur.fetchall()
        ]
        cur.execute(
            "SELECT COUNT(*)::int AS n FROM bt2_daily_picks WHERE operating_day_key = %s",
            (operating_day_key,),
        )
        total = int(cur.fetchone()["n"] or 0)
    finally:
        cur.close()
        conn.close()

    summary = (
        f"Día {operating_day_key}: {total} filas en bt2_daily_picks. "
        f"Desglose por etiqueta de confianza y fuente listo para leyenda admin (no mezclar con % acierto)."
    )
    return Bt2AdminVaultPickDistributionOut(
        operating_day_key=operating_day_key,
        by_dsr_confidence_label=by_conf,
        by_dsr_source=by_src,
        score_buckets=score_b,
        total_daily_pick_rows=total,
        summary_human_es=summary,
    )


@router.post(
    "/admin/vault/regenerate-daily-snapshot",
    response_model=Bt2AdminVaultRegenerateSnapshotOut,
    response_model_by_alias=True,
    dependencies=[Depends(_require_bt2_admin)],
    tags=["bt2-admin"],
)
def bt2_admin_regenerate_daily_snapshot(
    user_id: str = Query(
        ...,
        min_length=32,
        max_length=48,
        alias="userId",
        description="UUID del usuario BT2 (mismo que en JWT / bt2_users.id). Opcional: se ignora sufijo _BT2 si se copia por error.",
    ),
    operating_day_key: str = Query(
        ...,
        min_length=10,
        max_length=10,
        alias="operatingDayKey",
        description="YYYY-MM-DD del día operativo cuyo snapshot se borra y regenera.",
    ),
) -> Bt2AdminVaultRegenerateSnapshotOut:
    """
    Desarrollo / operación: el snapshot es **idempotente** (`session/open` no regenera si ya hay filas).
    Este endpoint borra `bt2_daily_picks` + metadata de bóveda para ese usuario y día, y vuelve a ejecutar
    el mismo pipeline que `session/open` (pool, DSR, Post-DSR, fallback).

    Header: **X-BT2-Admin-Key** = `BT2_ADMIN_API_KEY`.
    """
    try:
        date.fromisoformat(operating_day_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="operatingDayKey debe ser YYYY-MM-DD válido")

    uid = _normalize_bt2_user_uuid_param(user_id)
    tz_name = _user_timezone(uid)
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """DELETE FROM bt2_daily_picks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (uid, operating_day_key),
        )
        cur.execute(
            """DELETE FROM bt2_vault_day_metadata
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (uid, operating_day_key),
        )
        inserted = _generate_daily_picks_snapshot(cur, uid, operating_day_key, tz_name)
        cur.execute(
            """SELECT COUNT(*)::int FROM bt2_daily_picks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (uid, operating_day_key),
        )
        total_after = int(cur.fetchone()[0] or 0)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    msg = (
        f"Snapshot regenerado para {operating_day_key}: {inserted} filas insertadas en esta corrida; "
        f"{total_after} filas totales en bóveda para ese día."
    )
    if total_after == 0:
        msg += (
            " Si es 0, el pool valor no encontró eventos elegibles (CDM vacío, umbrales 1.30, "
            "o `BT2_PRIORITY_LEAGUE_IDS` demasiado restrictivo)."
        )
    return Bt2AdminVaultRegenerateSnapshotOut(
        user_id=uid,
        operating_day_key=operating_day_key,
        picks_inserted_this_run=inserted,
        picks_total_after=total_after,
        message_es=msg,
    )
