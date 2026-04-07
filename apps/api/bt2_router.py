"""
Rutas BT2 — Sprint 03 / Sprint 04.
Sprint 04 añade dominio conductual: picks, sesión operativa, settings, DP ledger.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, List, Literal, Optional, cast

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from apps.api.bt2_schemas import (
    Bt2BehavioralMetricsOut,
    Bt2MetaOut,
    Bt2SessionDayOut,
    Bt2VaultPickOut,
    Bt2VaultPicksPageOut,
)
from apps.api.bt2_settings import bt2_settings
from apps.api.deps import Bt2UserId

router = APIRouter(prefix="/bt2", tags=["bt2"])


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


@router.get("/vault/picks", response_model=Bt2VaultPicksPageOut, response_model_by_alias=True)
def bt2_vault_picks(user_id: Bt2UserId) -> Bt2VaultPicksPageOut:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    odk = _operating_day_key()
    events = _fetch_upcoming_events(hours=24, require_active_league=True)

    picks: list[Bt2VaultPickOut] = []
    for i, ev in enumerate(events):
        odds_home = ev.get("odds_home") or 0.0
        odds_away = ev.get("odds_away") or 0.0
        odds_draw = ev.get("odds_draw") or 0.0

        if max(odds_home, odds_draw, odds_away) <= 1.30:
            continue

        best_odds = max(odds_home, odds_draw, odds_away)
        if odds_home == best_odds:
            mc, selection, odds_val = "ML_SIDE", f"Victoria {ev['home_team']}", odds_home
        elif odds_away == best_odds:
            mc, selection, odds_val = "ML_AWAY", f"Victoria {ev['away_team']}", odds_away
        else:
            mc, selection, odds_val = "ML_SIDE", "Empate", odds_draw

        tier: Literal["open", "premium"] = "open" if i % 2 == 0 else "premium"
        picks.append(
            Bt2VaultPickOut(
                id=f"cdm-{ev['id']}",
                market_class=mc,
                market_label_es=_MARKET_LABEL_ES.get(mc, mc),
                event_label=f"{ev['home_team']} vs {ev['away_team']}",
                titulo=f"{ev['league']} · {ev['kickoff_utc'].strftime('%d/%m') if ev['kickoff_utc'] else ''}",
                suggested_decimal_odds=round(float(odds_val), 2),
                edge_bps=0,
                selection_summary_es=selection,
                traduccion_humana="Selección basada en datos CDM BT2 — modelo en construcción.",
                curva_equidad=[0.0],
                access_tier=tier,
                unlock_cost_dp=0 if tier == "open" else _UNLOCK_DP_PREMIUM,
                operating_day_key=odk,
            )
        )

    return Bt2VaultPicksPageOut(picks=picks, generated_at_utc=now)


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


def _determine_outcome(market: str, selection: str, result_home: int, result_away: int) -> str:
    """Determina 'won', 'lost' o 'void' basado en mercado, selección y resultado."""
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


# ── Picks schemas (Sprint 04 US-BE-010) ──────────────────────────────────────

class PickIn(BaseModel):
    event_id: int
    market: str
    selection: str
    odds_accepted: float
    stake_units: float


class PickOut(BaseModel):
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

@router.post("/picks", status_code=201, response_model=PickOut)
def bt2_create_pick(body: PickIn, user_id: Bt2UserId) -> PickOut:
    if body.odds_accepted <= 1.0:
        raise HTTPException(status_code=422, detail="odds_accepted debe ser > 1.0")
    if body.stake_units <= 0:
        raise HTTPException(status_code=422, detail="stake_units debe ser > 0")

    conn = _db_conn()
    cur = conn.cursor()
    try:
        # Validar que el evento existe y está scheduled
        cur.execute(
            "SELECT id, status FROM bt2_events WHERE id = %s",
            (body.event_id,),
        )
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento no encontrado")
        if ev[1] != "scheduled":
            raise HTTPException(
                status_code=422,
                detail=f"El evento no está disponible para picks (status={ev[1]})",
            )

        # Prevenir pick duplicado (mismo usuario, evento, mercado)
        cur.execute(
            """SELECT id FROM bt2_picks
               WHERE user_id = %s::uuid AND event_id = %s
                 AND market = %s AND selection = %s AND status = 'open'""",
            (user_id, body.event_id, body.market, body.selection),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe un pick abierto para este evento/mercado/selección")

        cur.execute(
            """INSERT INTO bt2_picks
               (user_id, event_id, market, selection, odds_taken, stake_units, status)
               VALUES (%s::uuid, %s, %s, %s, %s, %s, 'open')
               RETURNING id, status, opened_at""",
            (user_id, body.event_id, body.market, body.selection,
             body.odds_accepted, body.stake_units),
        )
        row = cur.fetchone()
        conn.commit()
        pick_id, pick_status, opened_at = row

        # Obtener label del evento
        cur.execute(
            """SELECT th.name, ta.name FROM bt2_events e
               JOIN bt2_teams th ON e.home_team_id = th.id
               JOIN bt2_teams ta ON e.away_team_id = ta.id
               WHERE e.id = %s""",
            (body.event_id,),
        )
        teams = cur.fetchone()
        event_label = f"{teams[0]} vs {teams[1]}" if teams else f"Evento {body.event_id}"
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
        market=body.market,
        selection=body.selection,
    )


@router.get("/picks", response_model=PicksListOut)
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

        cur.execute(
            f"""SELECT p.id, p.event_id, p.market, p.selection,
                       p.odds_taken, p.stake_units, p.status,
                       p.opened_at, p.settled_at, p.pnl_units,
                       COALESCE(th.name,'?') || ' vs ' || COALESCE(ta.name,'?') AS event_label
                FROM bt2_picks p
                LEFT JOIN bt2_events e ON p.event_id = e.id
                LEFT JOIN bt2_teams th ON e.home_team_id = th.id
                LEFT JOIN bt2_teams ta ON e.away_team_id = ta.id
                WHERE {' AND '.join(where)}
                ORDER BY p.opened_at DESC""",
            params,
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
        )
        for r in rows
    ]
    return PicksListOut(picks=picks)


@router.get("/picks/{pick_id}", response_model=PickOut)
def bt2_get_pick(pick_id: int, user_id: Bt2UserId) -> PickOut:
    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """SELECT p.id, p.event_id, p.market, p.selection,
                      p.odds_taken, p.stake_units, p.status,
                      p.opened_at, p.settled_at, p.pnl_units,
                      COALESCE(th.name,'?') || ' vs ' || COALESCE(ta.name,'?') AS event_label
               FROM bt2_picks p
               LEFT JOIN bt2_events e ON p.event_id = e.id
               LEFT JOIN bt2_teams th ON e.home_team_id = th.id
               LEFT JOIN bt2_teams ta ON e.away_team_id = ta.id
               WHERE p.id = %s AND p.user_id = %s::uuid""",
            (pick_id, user_id),
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
    )


@router.post("/picks/{pick_id}/settle", response_model=SettleOut)
def bt2_settle_pick(pick_id: int, body: SettleIn, user_id: Bt2UserId) -> SettleOut:
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, status, market, selection, odds_taken, stake_units FROM bt2_picks WHERE id = %s AND user_id = %s::uuid",
            (pick_id, user_id),
        )
        pick = cur.fetchone()
        if not pick:
            raise HTTPException(status_code=404, detail="Pick no encontrado")
        if pick[1] != "open":
            raise HTTPException(status_code=409, detail="El pick ya está liquidado")

        outcome = _determine_outcome(pick[2], pick[3], body.result_home, body.result_away)
        odds = float(pick[4])
        stake = float(pick[5])

        if outcome == "won":
            pnl = round(stake * (odds - 1), 2)
            dp_earned = 2
            event_type = "pick_win"
        elif outcome == "lost":
            pnl = round(-stake, 2)
            dp_earned = 1
            event_type = "pick_loss"
        else:
            pnl = 0.0
            dp_earned = 0
            event_type = "pick_void"

        now = datetime.now(tz=timezone.utc)

        # Actualizar pick
        cur.execute(
            """UPDATE bt2_picks
               SET status = %s, settled_at = %s,
                   result_home = %s, result_away = %s, pnl_units = %s
               WHERE id = %s""",
            (outcome, now, body.result_home, body.result_away, pnl, pick_id),
        )

        # Actualizar bankroll_amount del usuario
        cur.execute(
            """UPDATE bt2_users SET bankroll_amount = COALESCE(bankroll_amount, 0) + %s
               WHERE id = %s::uuid
               RETURNING bankroll_amount""",
            (pnl, user_id),
        )
        bankroll_row = cur.fetchone()
        new_bankroll = float(bankroll_row[0]) if bankroll_row and bankroll_row[0] else None

        # Snapshot de bankroll
        cur.execute(
            """INSERT INTO bt2_bankroll_snapshots
               (user_id, snapshot_date, balance_units, event_type, reference_id)
               VALUES (%s::uuid, %s, %s, %s, %s)""",
            (user_id, now.date(), new_bankroll or 0, event_type, pick_id),
        )

        # Acreditar DP si corresponde
        dp_balance_after = _get_dp_balance(cur, user_id)
        if dp_earned > 0:
            dp_balance_after += dp_earned
            cur.execute(
                """INSERT INTO bt2_dp_ledger
                   (user_id, delta_dp, reason, reference_id, balance_after_dp)
                   VALUES (%s::uuid, %s, 'pick_settle', %s, %s)""",
                (user_id, dp_earned, pick_id, dp_balance_after),
            )

        conn.commit()
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
    session_id: int
    status: str
    grace_until_iso: str
    pending_settlements: int


# ── Sesión endpoints (T-100, T-101) ──────────────────────────────────────────

@router.post("/session/open", status_code=201, response_model=SessionOpenOut)
def bt2_session_open(user_id: Bt2UserId) -> SessionOpenOut:
    odk = _operating_day_key_for_user(user_id)
    conn = _db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id FROM bt2_operating_sessions
               WHERE user_id = %s::uuid AND operating_day_key = %s AND status = 'open'""",
            (user_id, odk),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Ya existe una sesión abierta para {odk}")

        cur.execute(
            """INSERT INTO bt2_operating_sessions (user_id, operating_day_key, status)
               VALUES (%s::uuid, %s, 'open')
               RETURNING id, station_opened_at""",
            (user_id, odk),
        )
        row = cur.fetchone()
        conn.commit()
        session_id, opened_at = row
    finally:
        cur.close()
        conn.close()

    return SessionOpenOut(
        session_id=session_id,
        operating_day_key=odk,
        station_opened_at=opened_at.isoformat(),
    )


@router.post("/session/close", status_code=200, response_model=SessionCloseOut)
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
        conn.commit()

        # picks pendientes del día actual
        cur.execute(
            """SELECT COUNT(*) FROM bt2_picks
               WHERE user_id = %s::uuid AND status = 'open'
                 AND DATE(opened_at AT TIME ZONE 'UTC') = %s""",
            (user_id, date.fromisoformat(odk)),
        )
        pending = int(cur.fetchone()[0])
    finally:
        cur.close()
        conn.close()

    return SessionCloseOut(
        session_id=session_id,
        status="closed",
        grace_until_iso=grace.isoformat(),
        pending_settlements=pending,
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
