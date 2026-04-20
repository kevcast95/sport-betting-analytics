from datetime import date, datetime
from typing import Any, Optional
import uuid as _uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawSportmonksFixture(Base):
    __tablename__ = "raw_sportmonks_fixtures"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    fixture_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    league_id: Mapped[Optional[int]] = mapped_column(Integer)
    home_team: Mapped[Optional[str]] = mapped_column(String(200))
    away_team: Mapped[Optional[str]] = mapped_column(String(200))
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RawTheoddsapiSnapshot(Base):
    __tablename__ = "raw_theoddsapi_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sport_key: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    commence_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    home_team: Mapped[Optional[str]] = mapped_column(String(200))
    away_team: Mapped[Optional[str]] = mapped_column(String(200))
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_theoddsapi_sport_commence", "sport_key", "commence_time"),
    )


class Bt2EventIdentityMap(Base):
    __tablename__ = "bt2_event_identity_map"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sportmonks_fixture_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    theoddsapi_event_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    home_team: Mapped[Optional[str]] = mapped_column(String(200))
    away_team: Mapped[Optional[str]] = mapped_column(String(200))
    commence_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    league_slug: Mapped[Optional[str]] = mapped_column(String(100))
    mapped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confidence: Mapped[str] = mapped_column(String(20), server_default="low")


# ── CDM (Common Data Model) — Sprint 03 ──────────────────────────────────────

class Bt2League(Base):
    __tablename__ = "bt2_leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    tier: Mapped[str] = mapped_column(String(20), server_default="unknown", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    sportmonks_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)


class Bt2Team(Base):
    __tablename__ = "bt2_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(100))
    sportmonks_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    league_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bt2_leagues.id"), nullable=True
    )


class Bt2Event(Base):
    __tablename__ = "bt2_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sportmonks_fixture_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    league_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bt2_leagues.id"), nullable=True
    )
    home_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bt2_teams.id"), nullable=True
    )
    away_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bt2_teams.id"), nullable=True
    )
    kickoff_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sofascore_event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), server_default="scheduled", nullable=False)
    result_home: Mapped[Optional[int]] = mapped_column(Integer)
    result_away: Mapped[Optional[int]] = mapped_column(Integer)
    season: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_bt2_events_kickoff", "kickoff_utc"),
        Index("ix_bt2_events_status_kickoff", "status", "kickoff_utc"),
    )


class Bt2OddsSnapshot(Base):
    __tablename__ = "bt2_odds_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id"), nullable=False
    )
    bookmaker: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(100), nullable=False)
    selection: Mapped[str] = mapped_column(String(100), nullable=False)
    odds: Mapped[Any] = mapped_column(Numeric(10, 4), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_bt2_odds_event_market", "event_id", "market"),
        UniqueConstraint("event_id", "market", "selection", "bookmaker",
                         name="uq_bt2_odds_event_market_sel_book"),
    )


# ── Auth (Sprint 03 US-BE-006) ────────────────────────────────────────────────

class Bt2User(Base):
    __tablename__ = "bt2_users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    bankroll_amount: Mapped[Optional[Any]] = mapped_column(Numeric(14, 2), nullable=True)
    bankroll_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    __table_args__ = (
        Index("ix_bt2_users_email", "email"),
    )


class Bt2Session(Base):
    __tablename__ = "bt2_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    __table_args__ = (
        Index("ix_bt2_sessions_user_revoked", "user_id", "revoked"),
    )


# ── Dominio conductual (Sprint 04 US-BE-009) ──────────────────────────────────

class Bt2Pick(Base):
    __tablename__ = "bt2_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id"), nullable=False
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    selection: Mapped[str] = mapped_column(String(50), nullable=False)
    odds_taken: Mapped[Any] = mapped_column(Numeric(10, 4), nullable=False)
    stake_units: Mapped[Any] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="open", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    result_home: Mapped[Optional[int]] = mapped_column(Integer)
    result_away: Mapped[Optional[int]] = mapped_column(Integer)
    pnl_units: Mapped[Optional[Any]] = mapped_column(Numeric(14, 2))
    settlement_source: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="user"
    )
    market_canonical: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model_market_canonical: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model_selection_canonical: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model_prediction_result: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    #: Criterio declarado por el operador (`pending`|`won`|`lost`|`void`); no reemplaza `status`/liquidación.
    user_result_claim: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_bt2_picks_user_status", "user_id", "status"),
        Index("ix_bt2_picks_event", "event_id"),
    )


class Bt2OperatingSession(Base):
    __tablename__ = "bt2_operating_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    operating_day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    station_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    station_closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default="open", nullable=False)
    grace_until_iso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("user_id", "operating_day_key", name="uq_bt2_opsession_user_day"),
        Index("ix_bt2_opsession_user_status", "user_id", "status"),
    )


class Bt2BankrollSnapshot(Base):
    __tablename__ = "bt2_bankroll_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    balance_units: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_bt2_bankroll_user_date", "user_id", "snapshot_date"),
    )


class Bt2DpLedger(Base):
    __tablename__ = "bt2_dp_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    delta_dp: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    balance_after_dp: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_bt2_dp_ledger_user", "user_id"),
    )


class Bt2BehavioralBlock(Base):
    __tablename__ = "bt2_behavioral_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    context_json: Mapped[Optional[Any]] = mapped_column(JSONB)
    estimated_loss_avoided_units: Mapped[Optional[Any]] = mapped_column(Numeric(8, 2))


class Bt2UserSettings(Base):
    __tablename__ = "bt2_user_settings"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), primary_key=True
    )
    risk_per_pick_pct: Mapped[Any] = mapped_column(
        Numeric(5, 2), server_default="2.00", nullable=False
    )
    dp_unlock_premium_threshold: Mapped[int] = mapped_column(
        Integer, server_default="50", nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String(50), server_default="America/Bogota", nullable=False
    )
    display_currency: Mapped[str] = mapped_column(
        String(10), server_default="COP", nullable=False
    )


class Bt2UserDiagnostic(Base):
    __tablename__ = "bt2_user_diagnostics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id", ondelete="CASCADE"), nullable=False
    )
    operator_profile: Mapped[str] = mapped_column(String(50), nullable=False)
    system_integrity: Mapped[Any] = mapped_column(Numeric(4, 3), nullable=False)
    answers_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_user_diagnostics_user_created", "user_id", "created_at"),
    )


class Bt2DailyPick(Base):
    __tablename__ = "bt2_daily_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id"), nullable=False
    )
    operating_day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    access_tier: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    suggested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    pipeline_version: Mapped[str] = mapped_column(String(40), nullable=False)
    dsr_input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dsr_narrative_es: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    dsr_confidence_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    model_market_canonical: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model_selection_canonical: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    reference_decimal_odds: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    dsr_source: Mapped[str] = mapped_column(String(24), nullable=False)
    data_completeness_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    slate_rank: Mapped[int] = mapped_column(
        SmallInteger, server_default="1", nullable=False
    )
    estimated_hit_probability: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 8), nullable=True
    )
    evidence_quality: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    predictive_tier: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    action_tier: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "event_id", "operating_day_key", name="uq_daily_picks_user_event_day"),
        Index("ix_daily_picks_user_day", "user_id", "operating_day_key"),
        Index("ix_daily_picks_user_day_slate_rank", "user_id", "operating_day_key", "slate_rank"),
    )


class Bt2PickOfficialEvaluation(Base):
    """US-BE-049 — evaluación oficial vs resultado CDM; unidad = pick sugerido (`bt2_daily_picks`)."""

    __tablename__ = "bt2_pick_official_evaluation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    daily_pick_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_daily_picks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id"), nullable=False
    )
    market_canonical: Mapped[str] = mapped_column(String(64), nullable=False)
    selection_canonical: Mapped[str] = mapped_column(String(64), nullable=False)
    dsr_confidence_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    suggested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending_result"
    )
    truth_source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    truth_payload_ref: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    no_evaluable_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "evaluation_status IN ("
            "'pending_result','evaluated_hit','evaluated_miss','void','no_evaluable'"
            ")",
            name="ck_bt2_pick_official_evaluation_status_v1",
        ),
        Index("ix_bt2_pick_official_eval_status", "evaluation_status"),
        Index("ix_bt2_pick_official_eval_event", "event_id"),
    )


class Bt2PoolEligibilityAudit(Base):
    """T-236 — auditoría append-only de elegibilidad v1 del pool (Fase 0 §6)."""

    __tablename__ = "bt2_pool_eligibility_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id", ondelete="CASCADE"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    eligibility_rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    primary_discard_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    detail_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_bt2_pool_elig_audit_event_eval", "event_id", "evaluated_at"),
    )


class Bt2VaultDayMetadata(Base):
    """US-BE-036 — flags día bóveda (vacío operativo, degradación DSR, cobertura)."""

    __tablename__ = "bt2_vault_day_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id", ondelete="CASCADE"), nullable=False
    )
    operating_day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    dsr_signal_degraded: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    limited_coverage: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    operational_empty_hard: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    vault_empty_message_es: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_disclaimer_es: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    future_events_in_window_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    fallback_eligible_pool_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    slate_band_cycle: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "operating_day_key", name="uq_bt2_vault_meta_user_day"),
        Index("ix_bt2_vault_meta_user_day", "user_id", "operating_day_key"),
    )


class Bt2VaultPremiumUnlock(Base):
    """US-BE-029: desbloqueo premium sin crear bt2_picks (D-05.1-002)."""

    __tablename__ = "bt2_vault_premium_unlocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id", ondelete="CASCADE"), nullable=False
    )
    daily_pick_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_daily_picks.id", ondelete="CASCADE"), nullable=False
    )
    operating_day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "daily_pick_id", name="uq_vault_premium_unlock_user_dp"
        ),
        Index("ix_bt2_vault_premium_unlocks_user_day", "user_id", "operating_day_key"),
    )


class Bt2VaultStandardUnlock(Base):
    """Desbloqueo explícito de ítem estándar (sin DP); topes diarios en servidor."""

    __tablename__ = "bt2_vault_standard_unlocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id", ondelete="CASCADE"), nullable=False
    )
    daily_pick_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_daily_picks.id", ondelete="CASCADE"), nullable=False
    )
    operating_day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "daily_pick_id", name="uq_vault_standard_unlock_user_dp"
        ),
        Index("ix_bt2_vault_standard_unlocks_user_day", "user_id", "operating_day_key"),
    )


class Bt2VaultPickCommitment(Base):
    """Marcación manual tomó / no tomó tras liberar (no sustituye ledger bt2_picks)."""

    __tablename__ = "bt2_vault_pick_commitment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bt2_users.id", ondelete="CASCADE"), nullable=False
    )
    daily_pick_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_daily_picks.id", ondelete="CASCADE"), nullable=False
    )
    operating_day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    commitment: Mapped[str] = mapped_column(String(16), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "daily_pick_id", name="uq_vault_pick_commitment_user_dp"
        ),
        Index("ix_bt2_vault_pick_commitment_user_day", "user_id", "operating_day_key"),
    )


# ── S6.5 Validate SFS — experimento staging (D-06-069 / US-BE-058) ─────────────


class Bt2ProviderOddsSnapshot(Base):
    """Odds raw por proveedor y source_scope; idempotencia por (event, provider, scope, run)."""

    __tablename__ = "bt2_provider_odds_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bt2_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="s65-v0")
    provider_event_ref: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    ingested_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "bt2_event_id",
            "provider",
            "source_scope",
            "run_id",
            name="uq_bt2_provider_odds_snap_evt_prov_scope_run",
        ),
        Index("ix_bt2_prov_odds_snap_run", "run_id", "bt2_event_id"),
    )


class Bt2SfsEventOverride(Base):
    """Capa 3 join: override manual SM fixture → SofaScore event id."""

    __tablename__ = "bt2_sfs_event_override"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bt2_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    sofascore_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Bt2SfsJoinAudit(Base):
    """Auditoría de resolución join por corrida (T-280)."""

    __tablename__ = "bt2_sfs_join_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bt2_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id", ondelete="CASCADE"), nullable=False
    )
    sofascore_event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    match_layer: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    match_status: Mapped[str] = mapped_column(String(24), nullable=False)
    detail_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("run_id", "bt2_event_id", name="uq_bt2_sfs_join_audit_run_event"),
        Index("ix_bt2_sfs_join_audit_run", "run_id"),
    )


class Bt2DsrDsInputShadow(Base):
    """Fragmento ds_input experimental (D-06-070)."""

    __tablename__ = "bt2_dsr_ds_input_shadow"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bt2_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bt2_events.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_bt2_ds_input_shadow_run_event", "run_id", "bt2_event_id"),)
