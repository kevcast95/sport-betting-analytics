"""
Rutas BT2 — Sprint 03 / Sprint 04.
Sprint 04 añade dominio conductual: picks, sesión operativa, settings, DP ledger.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Literal, Optional, Tuple, cast

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from apps.api.bt2_dx_constants import (
    BT2_ERR_DP_INSUFFICIENT_PREMIUM,
    BT2_ERR_PICK_KICKOFF_ELAPSED,
    DP_PREMIUM_UNLOCK_COST,
    PICK_SETTLE_DP_REWARD,
    PENALTY_STATION_UNCLOSED_DP,
    PENALTY_UNSETTLED_DP,
    REASON_PENALTY_STATION_UNCLOSED,
    REASON_PENALTY_UNSETTLED_PICKS,
    REASON_PICK_PREMIUM_UNLOCK,
    REASON_PICK_SETTLE,
    REASON_SESSION_CLOSE_DISCIPLINE,
    SESSION_CLOSE_DISCIPLINE_REWARD_DP,
)
from apps.api.bt2_dsr_contract import (
    PIPELINE_VERSION_DEFAULT,
    assert_no_forbidden_ds_keys,
    hash_dsr_input_payload,
)
from apps.api.bt2_dsr_deepseek import DsrBatchCandidate, deepseek_suggest_batch
from apps.api.bt2_dsr_suggest import (
    PIPELINE_VERSION_DEEPSEEK,
    suggest_for_snapshot_row,
)
from apps.api.bt2_market_canonical import (
    evaluate_model_vs_result,
    market_canonical_label_es,
    normalized_pick_to_canonical,
)
from apps.api.bt2_schemas import (
    Bt2AdminDsrDayOut,
    Bt2AdminDsrAuditRowOut,
    Bt2AdminDsrDaySummaryOut,
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
)
from apps.api.bt2_settings import bt2_settings
from apps.api.bt2_vault_pool import (
    VAULT_POOL_TARGET,
    compose_vault_daily_picks,
    is_event_available_for_pick_strict,
    kickoff_utc_to_time_band,
)
from apps.api.deps import Bt2UserId

router = APIRouter(prefix="/bt2", tags=["bt2"])
logger = logging.getLogger("bt2_router")

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
    return Bt2MetaOut(settlement_verification_mode=cast(Literal["trust", "verified"], mode))


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


@router.get("/vault/picks", response_model=Bt2VaultPicksPageOut, response_model_by_alias=True)
def bt2_vault_picks(user_id: Bt2UserId) -> Bt2VaultPicksPageOut:
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
                CASE dp.access_tier WHEN 'standard' THEN 1 ELSE 2 END,
                dp.suggested_at ASC
        """, (user_id, odk))
        rows = cur.fetchall()

        cur.execute(
            """SELECT daily_pick_id FROM bt2_vault_premium_unlocks
               WHERE user_id = %s::uuid AND operating_day_key = %s""",
            (user_id, odk),
        )
        unlocked_dp_ids = {int(r["daily_pick_id"]) for r in cur.fetchall()}
        cur.execute(
            """SELECT DISTINCT event_id FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'""",
            (user_id,),
        )
        legacy_open_event_ids = {int(r["event_id"]) for r in cur.fetchall()}
    finally:
        cur.close()
        conn.close()

    if not rows:
        return Bt2VaultPicksPageOut(
            picks=[],
            generated_at_utc=now,
            message="No hay eventos disponibles para hoy. El sistema actualiza la cartelera cada mañana.",
            pool_item_count=0,
            pool_below_target=True,
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
        kickoff_iso = _kickoff_utc_iso_z(kickoff)

        # Odds
        odds_home = float(row["odds_home"] or 0.0)
        odds_draw = float(row["odds_draw"] or 0.0)
        odds_away = float(row["odds_away"] or 0.0)
        best_odds = max(odds_home, odds_draw, odds_away)

        if best_odds > 1.0:
            if odds_home == best_odds:
                mc = "ML_SIDE"
                selection = f"Victoria {home_team}"
                odds_val = odds_home
            elif odds_away == best_odds:
                mc = "ML_AWAY"
                selection = f"Victoria {away_team}"
                odds_val = odds_away
            else:
                mc = "ML_SIDE"
                selection = "Empate"
                odds_val = odds_draw
        else:
            mc = "ML_SIDE"
            selection = f"{home_team} vs {away_team}"
            odds_val = 2.0

        # URL de búsqueda externa
        kickoff_date = kickoff.strftime("%Y-%m-%d") if kickoff else odk
        search_q = f"{home_team}+vs+{away_team}+{kickoff_date}".replace(" ", "+")
        external_url = f"https://www.google.com/search?q={search_q}"

        titulo = f"{league_name} · {kickoff.strftime('%d/%m') if kickoff else odk}"
        tier_label = row["access_tier"]  # "standard" | "premium"
        dp_id = int(row["dp_id"])
        ev_id = int(row["event_id"])
        premium_unlocked = False
        if tier_label == "premium":
            premium_unlocked = dp_id in unlocked_dp_ids or ev_id in legacy_open_event_ids

        mmc = row.get("model_market_canonical") or ""
        msc = row.get("model_selection_canonical") or ""
        mcl_es = market_canonical_label_es(mmc or None)
        dsr_narr = (row.get("dsr_narrative_es") or "").strip()
        trad_human = (
            dsr_narr
            if dsr_narr
            else "Señal basada en reglas CDM — sin narrativa DSR extendida para este ítem."
        )
        pipe_v = str(row.get("pipeline_version") or PIPELINE_VERSION_DEFAULT)
        dsr_src = str(row.get("dsr_source") or "rules_fallback")
        dsr_conf = str(row.get("dsr_confidence_label") or "")

        picks.append(
            Bt2VaultPickOut(
                id=f"dp-{dp_id}",
                event_id=ev_id,
                market_class=mc,
                market_label_es=_MARKET_LABEL_ES.get(mc, mc),
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
                kickoff_utc=kickoff_iso,
                event_status=event_status_str,
                external_search_url=external_url,
                premium_unlocked=premium_unlocked,
                time_band=time_band,
                pipeline_version=pipe_v,
                dsr_narrative_es=dsr_narr,
                dsr_confidence_label=dsr_conf,
                dsr_source=dsr_src,
                market_canonical=mmc or "UNKNOWN",
                market_canonical_label_es=mcl_es,
                model_market_canonical=mmc,
                model_selection_canonical=msc,
            )
        )

    n = len(picks)
    return Bt2VaultPicksPageOut(
        picks=picks,
        generated_at_utc=now,
        pool_item_count=n,
        pool_below_target=n < VAULT_POOL_TARGET,
    )


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
    new_raw = raw + delta_dp
    cur.execute(
        """INSERT INTO bt2_dp_ledger (user_id, delta_dp, reason, reference_id, balance_after_dp)
           VALUES (%s::uuid, %s, %s, %s, %s)""",
        (user_id, delta_dp, reason, reference_id, new_raw),
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


def _close_orphan_sessions_and_station_penalties(cur, user_id: str, odk: str, now: datetime) -> None:
    """
    Sesiones con operating_day_key < odk aún abiertas → cierre + penalty_station_unclosed −50
    una sola vez por sesión (idempotente por reason + reference_id). D-05-002 / US-BE-017.
    """
    cur.execute(
        """SELECT id FROM bt2_operating_sessions
           WHERE user_id = %s::uuid AND status = 'open' AND operating_day_key < %s
           ORDER BY operating_day_key ASC""",
        (user_id, odk),
    )
    for (orphan_id,) in cur.fetchall():
        cur.execute(
            """UPDATE bt2_operating_sessions
               SET status = 'closed', station_closed_at = %s, grace_until_iso = %s
               WHERE id = %s AND user_id = %s::uuid AND status = 'open'""",
            (now, now + timedelta(hours=24), orphan_id, user_id),
        )
        if not _ledger_move_exists(cur, user_id, REASON_PENALTY_STATION_UNCLOSED, orphan_id):
            _append_dp_ledger_move(
                cur, user_id, PENALTY_STATION_UNCLOSED_DP, REASON_PENALTY_STATION_UNCLOSED, orphan_id
            )
            logger.info(
                "penalty_station_unclosed: user=%s session_id=%s delta_dp=%s (estación día anterior sin cerrar)",
                user_id,
                orphan_id,
                PENALTY_STATION_UNCLOSED_DP,
            )


def _apply_grace_unsettled_penalties(cur, user_id: str, now: datetime) -> None:
    """
    penalty_unsettled_picks −25 por sesión cerrada con gracia vencida, si había pick abierto
    al cierre; idempotente por (reason, reference_id=session.id). US-BE-017.
    """
    cur.execute(
        """SELECT id, station_closed_at FROM bt2_operating_sessions
           WHERE user_id = %s::uuid AND status = 'closed' AND grace_until_iso < %s""",
        (user_id, now),
    )
    for sess_id, station_closed_at in cur.fetchall():
        if _ledger_move_exists(cur, user_id, REASON_PENALTY_UNSETTLED_PICKS, sess_id):
            continue
        cur.execute(
            """SELECT 1 FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open' AND opened_at <= %s
               LIMIT 1""",
            (user_id, station_closed_at),
        )
        if not cur.fetchone():
            continue
        _append_dp_ledger_move(
            cur, user_id, PENALTY_UNSETTLED_DP, REASON_PENALTY_UNSETTLED_PICKS, sess_id
        )
        logger.info(
            "penalty_unsettled_picks: user=%s session_id=%s delta_dp=%s (picks abiertos tras gracia)",
            user_id,
            sess_id,
            PENALTY_UNSETTLED_DP,
        )


def _determine_outcome(market: str, selection: str, result_home: int, result_away: int) -> str:
    """
    Determina 'won', 'lost' o 'void' (US-DX-001 — mercados mínimos settle, Sprint 05).

    Soportado hoy (sinónimos en selection):
    - Match Winner / 1X2 / Winner: selección 1|Home|home, X|Draw|…, 2|Away|away.
    - Over/Under goals: selección con OVER|UNDER y umbral numérico (default 2.5).
    Entrada típica ya normalizada vía `_normalize_market_selection_for_pick` (POST /bt2/picks): ML_SIDE,
    ML_AWAY, ML_TOTAL, textos «Más de …», «Victoria {equipo}», etc.

    Sprint 06: enum único en CDM/API.
    """
    m = market.upper()
    s = selection.strip()
    total = result_home + result_away

    if any(k in m for k in ("MATCH WINNER", "1X2", "WINNER")):
        if s in ("1", "Home", "home"):
            return "won" if result_home > result_away else "lost"
        if s in ("X", "Draw", "draw", "Empate", "empate"):
            return "won" if result_home == result_away else "lost"
        if s in ("2", "Away", "away"):
            return "won" if result_away > result_home else "lost"
        return "void"

    if any(k in m for k in ("OVER", "UNDER", "GOALS", "TOTAL")):
        num = re.search(r"(\d+\.?\d*)", s)
        threshold = float(num.group(1)) if num else 2.5
        if "OVER" in s.upper():
            return "won" if total > threshold else "lost"
        if "UNDER" in s.upper():
            return "won" if total < threshold else "lost"
        return "void"

    return "void"


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


class PicksListOut(BaseModel):
    picks: List[PickOut]


class SettleIn(BaseModel):
    result_home: int
    result_away: int


class SettleOut(BaseModel):
    pick_id: int
    status: str
    pnl_units: float
    bankroll_after_units: Optional[float]
    earned_dp: int
    dp_balance_after: int


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
               ORDER BY id DESC LIMIT 1""",
            (user_id, odk, body.event_id),
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
               LIMIT 1""",
            (user_id, odk, body.event_id),
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


@router.post("/picks/{pick_id}/settle", response_model=SettleOut)
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

        if outcome == "won":
            pnl = round(stake * (odds - 1), 2)
            event_type = "pick_win"
        elif outcome == "lost":
            pnl = round(-stake, 2)
            event_type = "pick_loss"
        else:
            pnl = 0.0
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
            (pnl, user_id),
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


def _generate_daily_picks_snapshot(cur, user_id: str, odk: str, tz_name: str) -> int:
    """
    US-BE-030 / D-05.2-002: pool diario ~15 candidatos (tope 20), franjas por TZ usuario.
    Idempotente: si ya existe snapshot para (user_id, odk), no hace nada.
    """
    cur.execute(
        "SELECT COUNT(*) FROM bt2_daily_picks WHERE user_id = %s::uuid AND operating_day_key = %s",
        (user_id, odk),
    )
    if int(cur.fetchone()[0]) > 0:
        return 0

    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc

    local_today = datetime.now(tz=tz).date()
    day_start_utc = datetime.combine(local_today, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    day_end_utc = day_start_utc + timedelta(hours=24)

    cur.execute(
        """
        SELECT
            e.id AS event_id,
            e.kickoff_utc,
            COALESCE((
                SELECT MIN(1.0 / NULLIF(o.odds, 0))
                FROM bt2_odds_snapshot o
                WHERE o.event_id = e.id
                  AND lower(o.market) IN ('1x2','match winner','full time result','fulltime result')
                  AND (o.selection IN ('1','Home') OR lower(o.selection) LIKE '%%home%%')
            ), 999) AS house_margin
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        WHERE
            e.kickoff_utc >= %s
            AND e.kickoff_utc < %s
            AND e.status = 'scheduled'
            AND l.is_active = true
            AND EXISTS (
                SELECT 1 FROM bt2_odds_snapshot o2
                WHERE o2.event_id = e.id
                  AND o2.odds >= 1.30
            )
        ORDER BY
            CASE l.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END ASC,
            house_margin ASC
        LIMIT 80
        """,
        (day_start_utc, day_end_utc),
    )

    rows = cur.fetchall()
    if not rows:
        return 0

    composed = compose_vault_daily_picks(
        [(int(r[0]), r[1], float(r[2])) for r in rows],
        tz,
    )

    def _dsr_hash(
        eid: int,
        oh: Optional[float],
        od: Optional[float],
        oa: Optional[float],
        ov: Optional[float],
        un: Optional[float],
    ) -> str:
        payload = {
            "event_id": eid,
            "odds": {
                "home": oh,
                "draw": od,
                "away": oa,
                "over25": ov,
                "under25": un,
            },
        }
        assert_no_forbidden_ds_keys(payload)
        return hash_dsr_input_payload(payload)

    plan: list[
        tuple[int, str, Any, Optional[tuple]]
    ] = []
    for event_id, access_tier, band in composed:
        ctx = _fetch_event_context_for_dsr(cur, event_id)
        plan.append((event_id, access_tier, band, ctx))

    ds_by_eid: dict[int, tuple[str, str, str, str]] = {}
    prov = (bt2_settings.bt2_dsr_provider or "rules").strip().lower()
    dkey = (bt2_settings.deepseek_api_key or "").strip()
    if prov == "deepseek" and dkey:
        batch_size = max(1, int(bt2_settings.bt2_dsr_batch_size))
        eligible = [(eid, at, b, ctx) for eid, at, b, ctx in plan if ctx]
        for i in range(0, len(eligible), batch_size):
            chunk = eligible[i : i + batch_size]
            cands: list[DsrBatchCandidate] = []
            for eid, _at, _b, ctx in chunk:
                assert ctx is not None
                home, away, league, oh, od, oa, ov, un = ctx
                cands.append(
                    DsrBatchCandidate(
                        event_id=eid,
                        tournament=league or "Liga",
                        home_team=home or "Local",
                        away_team=away or "Visitante",
                        odds_home=float(oh) if oh is not None else None,
                        odds_draw=float(od) if od is not None else None,
                        odds_away=float(oa) if oa is not None else None,
                        odds_over25=float(ov) if ov is not None else None,
                        odds_under25=float(un) if un is not None else None,
                    )
                )
            part = deepseek_suggest_batch(
                cands,
                operating_day_key=odk,
                api_key=dkey,
                base_url=bt2_settings.bt2_dsr_deepseek_base_url,
                model=bt2_settings.bt2_dsr_deepseek_model,
                timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                max_retries=int(bt2_settings.bt2_dsr_max_retries),
            )
            for eid, _at, _b, _ctx in chunk:
                tup = part.get(eid)
                if tup is not None:
                    ds_by_eid[eid] = tup
    elif prov == "deepseek" and not dkey:
        logging.getLogger(__name__).warning(
            "bt2_dsr_missing_api_key provider=deepseek (lotes no invocados)"
        )

    inserted = 0
    for event_id, access_tier, _band, ctx in plan:
        if ctx:
            home, away, league, oh, od, oa, ov, un = ctx
            oh_f = float(oh) if oh is not None else None
            od_f = float(od) if od is not None else None
            oa_f = float(oa) if oa is not None else None
            ov_f = float(ov) if ov is not None else None
            un_f = float(un) if un is not None else None
            batch_hit = ds_by_eid.get(event_id)
            if batch_hit is not None:
                narr, conf, mmc, msc = batch_hit
                pver = PIPELINE_VERSION_DEEPSEEK
                dsrc = "dsr_api"
                dhash = _dsr_hash(event_id, oh_f, od_f, oa_f, ov_f, un_f)
            else:
                narr, conf, mmc, msc, pver, dsrc, dhash = suggest_for_snapshot_row(
                    event_id,
                    oh_f,
                    od_f,
                    oa_f,
                    ov_f,
                    un_f,
                    home or "Local",
                    away or "Visitante",
                    league or "Liga",
                )
        else:
            narr = "Evento sin contexto CDM para DSR."
            conf = "low"
            mmc = "UNKNOWN"
            msc = "unknown_side"
            pver = PIPELINE_VERSION_DEFAULT
            dsrc = "rules_fallback"
            dhash = None

        cur.execute(
            """
            INSERT INTO bt2_daily_picks (
                user_id, event_id, operating_day_key, access_tier,
                pipeline_version, dsr_input_hash, dsr_narrative_es, dsr_confidence_label,
                model_market_canonical, model_selection_canonical, dsr_source
            )
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, event_id, operating_day_key) DO NOTHING
            """,
            (
                user_id,
                event_id,
                odk,
                access_tier,
                pver,
                dhash,
                narr,
                conf,
                mmc,
                msc,
                dsrc,
            ),
        )
        if cur.rowcount:
            inserted += 1

    return inserted


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

        _close_orphan_sessions_and_station_penalties(cur, user_id, odk, now)
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
