"""
Contratos JSON (US-DX-001) para BetTracker 2.0 — stub Sprint 01.
Serialización con alias camelCase para alinear con el cliente TypeScript.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.api.bt2_dsr_contract import CONTRACT_VERSION_PUBLIC
from apps.api.bt2_vault_pool import (
    VAULT_POOL_HARD_CAP,
    VAULT_POOL_TARGET,
    VAULT_VALUE_POOL_UNIVERSE_MAX,
)

VaultTimeBandLiteral = Literal["morning", "afternoon", "evening", "overnight"]


class Bt2MetaOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    contract_version: str = Field(
        default=CONTRACT_VERSION_PUBLIC,
        serialization_alias="contractVersion",
        description=(
            "S6.2: cubo A SM (includes/UPSERT raw), diagnostics raw_fixture_missing; "
            "S6.1 refinement ds_input / ingest_meta (D-06-027–030)."
        ),
    )
    settlement_verification_mode: Literal["trust", "verified"] = Field(
        ...,
        serialization_alias="settlementVerificationMode",
        description="MVP cliente = trust; verified requiere US-BE + resultado canónico CDM.",
    )


class Bt2SessionDayOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(
        ...,
        serialization_alias="operatingDayKey",
        description="YYYY-MM-DD del día operativo (zona del usuario).",
    )
    user_time_zone: str = Field(
        default="America/Bogota",
        serialization_alias="userTimeZone",
    )
    grace_until_iso: Optional[str] = Field(
        default=None,
        serialization_alias="graceUntilIso",
        description="Fin ISO 8601 de ventana de gracia 24 h respecto al día anterior.",
    )
    pending_settlements_previous_day: int = Field(
        default=0,
        serialization_alias="pendingSettlementsPreviousDay",
    )
    station_closed_for_operating_day: bool = Field(
        default=False,
        serialization_alias="stationClosedForOperatingDay",
    )


class Bt2VaultPickOut(BaseModel):
    """Pick CDM ampliado — misma semántica que `VaultPickCdm` en el cliente."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    event_id: int = Field(serialization_alias="eventId")
    market_class: str = Field(serialization_alias="marketClass")
    market_label_es: str = Field(serialization_alias="marketLabelEs")
    event_label: str = Field(serialization_alias="eventLabel")
    titulo: str
    suggested_decimal_odds: float = Field(serialization_alias="suggestedDecimalOdds")
    edge_bps: int = Field(serialization_alias="edgeBps")
    selection_summary_es: str = Field(serialization_alias="selectionSummaryEs")
    traduccion_humana: str = Field(serialization_alias="traduccionHumana")
    curva_equidad: List[float] = Field(serialization_alias="curvaEquidad")
    access_tier: str = Field(serialization_alias="accessTier")
    unlock_cost_dp: int = Field(serialization_alias="unlockCostDp")
    operating_day_key: str = Field(serialization_alias="operatingDayKey")
    is_available: bool = Field(True, serialization_alias="isAvailable")
    kickoff_utc: str = Field(
        "",
        serialization_alias="kickoffUtc",
        description="ISO 8601 UTC (…Z). Vacío si bt2_events.kickoff_utc es NULL.",
    )
    event_status: str = Field(
        "",
        serialization_alias="eventStatus",
        description="Valor crudo bt2_events.status (CDM).",
    )
    external_search_url: str = Field("", serialization_alias="externalSearchUrl")
    premium_unlocked: bool = Field(
        False,
        serialization_alias="premiumUnlocked",
        description="True si el usuario ya desbloqueó este ítem premium hoy (US-BE-029) o legado con pick abierto.",
    )
    time_band: VaultTimeBandLiteral = Field(
        ...,
        serialization_alias="timeBand",
        description=(
            "Franja local del kickoff (TZ usuario). D-06-032: mañana [06:00,12:00), tarde [12:00,18:00), "
            "noche [18:00,24:00), overnight [00:00,06:00)."
        ),
    )
    pipeline_version: str = Field(
        "",
        serialization_alias="pipelineVersion",
        description=(
            "Versión del pipeline DSR (US-BE-025 / T-170): p. ej. `s6-rules-v0`, `s6-deepseek-v1` "
            "cuando la señal vino de DeepSeek por lote (`picks_by_event`) con éxito."
        ),
    )
    dsr_narrative_es: str = Field(
        "",
        serialization_alias="dsrNarrativeEs",
        description="Narrativa modelo en español (sin payload crudo de proveedor).",
    )
    dsr_confidence_label: str = Field(
        "",
        serialization_alias="dsrConfidenceLabel",
        description="Etiqueta simbólica de confianza (p. ej. low, medium).",
    )
    dsr_source: str = Field(
        "",
        serialization_alias="dsrSource",
        description="Origen de la señal: rules_fallback, dsr_api, …",
    )
    market_canonical: str = Field(
        "",
        serialization_alias="marketCanonical",
        description="Código mercado canónico (US-BE-027).",
    )
    market_canonical_label_es: str = Field(
        "",
        serialization_alias="marketCanonicalLabelEs",
        description="Etiqueta humana del mercado canónico.",
    )
    model_market_canonical: str = Field(
        "",
        serialization_alias="modelMarketCanonical",
        description="Mercado de la sugerencia DSR (canónico).",
    )
    model_selection_canonical: str = Field(
        "",
        serialization_alias="modelSelectionCanonical",
        description="Selección sugerida por el modelo (canónico).",
    )
    data_completeness_score: Optional[int] = Field(
        None,
        serialization_alias="dataCompletenessScore",
        ge=0,
        le=100,
        description="Heurística servidor 0–100 de completitud de mercados en CDM (no es probabilidad de acierto).",
    )
    slate_rank: Optional[int] = Field(
        None,
        serialization_alias="slateRank",
        ge=1,
        le=100,
        description="Orden en el snapshot del día (1 = cabeza de cartelera tras compose/regenerar).",
    )


class VaultPremiumUnlockIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(
        ...,
        min_length=1,
        serialization_alias="vaultPickId",
        description="Id del ítem en vault (p. ej. dp-7).",
    )


class VaultPremiumUnlockOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(..., serialization_alias="vaultPickId")
    premium_unlocked: bool = Field(True, serialization_alias="premiumUnlocked")
    dp_balance_after: int = Field(..., serialization_alias="dpBalanceAfter")


class Bt2VaultPicksPageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    picks: List[Bt2VaultPickOut]
    generated_at_utc: str = Field(
        ...,
        serialization_alias="generatedAtUtc",
        description="Marca temporal de generación.",
    )
    message: Optional[str] = Field(None, serialization_alias="message")
    pool_target_count: int = Field(
        VAULT_POOL_TARGET,
        serialization_alias="poolTargetCount",
        description="Slate objetivo por usuario/día (D-06-032: 5 ítems visibles/persistidos).",
    )
    pool_hard_cap: int = Field(
        VAULT_POOL_HARD_CAP,
        serialization_alias="poolHardCap",
        description="Tope de ítems visibles en UI (D-06-032: 5); `picks` puede traer hasta valuePoolUniverseMax.",
    )
    value_pool_universe_max: int = Field(
        VAULT_VALUE_POOL_UNIVERSE_MAX,
        serialization_alias="valuePoolUniverseMax",
        description="Máx. candidatos valor considerados antes de componer el slate (D-06-032: 20).",
    )
    pool_item_count: int = Field(
        ...,
        serialization_alias="poolItemCount",
        description="Cantidad de ítems en `picks` (típ. hasta 20 persistidos); la UI recorta a poolHardCap.",
    )
    vault_universe_persisted_count: int = Field(
        0,
        serialization_alias="vaultUniversePersistedCount",
        description="Igual que poolItemCount (compat); filas del snapshot del día en servidor.",
    )
    slate_band_cycle: int = Field(
        0,
        serialization_alias="slateBandCycle",
        description="Ciclo 0–3 de prioridad de franja al componer/regenerar (D-06-032).",
    )
    pool_below_target: bool = Field(
        ...,
        serialization_alias="poolBelowTarget",
        description="True si hay menos ítems que `poolTargetCount` (falta de stock CDM u otra causa).",
    )
    dsr_signal_degraded: bool = Field(
        False,
        serialization_alias="dsrSignalDegraded",
        description="True si la bóveda incluye fallback SQL por ausencia de señal DSR válida (D-06-024).",
    )
    limited_coverage: bool = Field(
        False,
        serialization_alias="limitedCoverage",
        description="Heurística 'pocos eventos' (menos de 5 futuros en ventana día, D-06-026 §4); no bloquea fallback.",
    )
    operational_empty_hard: bool = Field(
        False,
        serialization_alias="operationalEmptyHard",
        description="Vacío duro: 0 filas elegibles en pool fallback (D-06-026 §6).",
    )
    vault_operational_message_es: Optional[str] = Field(
        None,
        serialization_alias="vaultOperationalMessageEs",
        description="Mensaje cuando no hay picks por causa operativa (p. ej. sin CDM elegible).",
    )
    fallback_disclaimer_es: Optional[str] = Field(
        None,
        serialization_alias="fallbackDisclaimerEs",
        description="Disclaimer cuando hay picks por fallback estadístico / datos limitados (D-06-025 §4).",
    )
    future_events_in_window_count: int = Field(
        0,
        serialization_alias="futureEventsInWindowCount",
        description="Conteo de eventos futuros en ventana día operativo (ligas activas).",
    )
    fallback_eligible_pool_count: int = Field(
        0,
        serialization_alias="fallbackEligiblePoolCount",
        description="Filas elegibles en pool SQL tras filtros T-177 al generar snapshot (≤ valuePoolUniverseMax al componer).",
    )


class Bt2AdminCountRowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(..., serialization_alias="key")
    count: int = Field(..., serialization_alias="count")


class Bt2AdminScoreBucketOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    score_bucket: int = Field(
        ...,
        serialization_alias="scoreBucket",
        description="Valor de data_completeness_score o -1 si era NULL.",
    )
    count: int = Field(..., serialization_alias="count")


class Bt2AdminVaultPickDistributionOut(BaseModel):
    """US-BE-035 / T-183 — agregados por día operativo (MVP medición v0)."""

    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(..., serialization_alias="operatingDayKey")
    by_dsr_confidence_label: List[Bt2AdminCountRowOut] = Field(
        default_factory=list,
        serialization_alias="byDsrConfidenceLabel",
    )
    by_dsr_source: List[Bt2AdminCountRowOut] = Field(
        default_factory=list,
        serialization_alias="byDsrSource",
    )
    score_buckets: List[Bt2AdminScoreBucketOut] = Field(
        default_factory=list,
        serialization_alias="scoreBuckets",
    )
    total_daily_pick_rows: int = Field(
        0,
        serialization_alias="totalDailyPickRows",
        description="Total filas bt2_daily_picks del día (todas las sesiones usuario).",
    )
    summary_human_es: str = Field("", serialization_alias="summaryHumanEs")


class Bt2AdminVaultRegenerateSnapshotOut(BaseModel):
    """Respuesta tras borrar y volver a ejecutar el pipeline de snapshot bóveda."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., serialization_alias="userId")
    operating_day_key: str = Field(..., serialization_alias="operatingDayKey")
    picks_inserted_this_run: int = Field(
        ...,
        serialization_alias="picksInsertedThisRun",
        description="Filas insertadas en esta corrida (puede ser 0 si pool vacío).",
    )
    picks_total_after: int = Field(
        ...,
        serialization_alias="picksTotalAfter",
        description="Total filas bt2_daily_picks para (user, día) tras regenerar.",
    )
    message_es: str = Field("", serialization_alias="messageEs")


class Bt2AdminDsrDaySummaryOut(BaseModel):
    """US-BE-028 — agregados MVP para vista admin precisión DSR (D-06-004 / D-06-015)."""

    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(..., serialization_alias="operatingDayKey")
    distinct_events_in_vault: int = Field(
        ...,
        serialization_alias="distinctEventsInVault",
        description="Eventos distintos en snapshot del día (todas las filas daily_picks).",
    )
    picks_settled_with_model: int = Field(
        0,
        serialization_alias="picksSettledWithModel",
    )
    model_hits: int = Field(0, serialization_alias="modelHits")
    model_misses: int = Field(0, serialization_alias="modelMisses")
    model_voids: int = Field(0, serialization_alias="modelVoids")
    model_na: int = Field(0, serialization_alias="modelNa")
    hit_rate_pct: Optional[float] = Field(
        None,
        serialization_alias="hitRatePct",
        description="Aciertos / (hits+misses) × 100 si hay denominador.",
    )
    summary_human_es: str = Field(
        "",
        serialization_alias="summaryHumanEs",
        description="Resumen legible para operador (US-BE-028 / identidad §B).",
    )


class Bt2AdminDsrAuditRowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pick_id: int = Field(..., serialization_alias="pickId")
    user_id: str = Field(..., serialization_alias="userId")
    event_id: int = Field(..., serialization_alias="eventId")
    operating_day_key: str = Field(..., serialization_alias="operatingDayKey")
    status: str
    model_prediction_result: Optional[str] = Field(
        None, serialization_alias="modelPredictionResult"
    )
    model_market_canonical: Optional[str] = Field(
        None, serialization_alias="modelMarketCanonical"
    )
    model_selection_canonical: Optional[str] = Field(
        None, serialization_alias="modelSelectionCanonical"
    )


class Bt2AdminDsrDayOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: Bt2AdminDsrDaySummaryOut
    audit_rows: List[Bt2AdminDsrAuditRowOut] = Field(
        default_factory=list,
        serialization_alias="auditRows",
    )


OPERATOR_PROFILE_VALUES = {
    "DISCIPLINE_TRADER",
    "IMPULSE_REACTIVE",
    "SYSTEMATIC_ANALYST",
    "RISK_SEEKER",
    "CONSERVATIVE_OBSERVER",
}


class DiagnosticIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operator_profile: str = Field(..., serialization_alias="operatorProfile")
    system_integrity: float = Field(..., ge=0.0, le=1.0, serialization_alias="systemIntegrity")
    answers_hash: Optional[str] = Field(None, serialization_alias="answersHash")

    @field_validator("operator_profile")
    @classmethod
    def validate_operator_profile(cls, v: str) -> str:
        if v not in OPERATOR_PROFILE_VALUES:
            raise ValueError(
                f"operator_profile debe ser uno de: {sorted(OPERATOR_PROFILE_VALUES)}"
            )
        return v


class DiagnosticOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operator_profile: str = Field(..., serialization_alias="operatorProfile")
    system_integrity: float = Field(..., serialization_alias="systemIntegrity")
    completed_at: str = Field(..., serialization_alias="completedAt")


class OperatingDaySummaryOut(BaseModel):
    """US-BE-018 — agregados del día operativo (zona horaria del usuario)."""

    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(..., serialization_alias="operatingDayKey")
    user_time_zone: str = Field(..., serialization_alias="userTimeZone")
    picks_opened_count: int = Field(0, serialization_alias="picksOpenedCount")
    picks_settled_count: int = Field(0, serialization_alias="picksSettledCount")
    won_count: int = Field(0, serialization_alias="wonCount")
    lost_count: int = Field(0, serialization_alias="lostCount")
    void_count: int = Field(0, serialization_alias="voidCount")
    total_stake_units_settled: float = Field(0.0, serialization_alias="totalStakeUnitsSettled")
    net_pnl_units: float = Field(0.0, serialization_alias="netPnlUnits")
    dp_earned_from_settlements: int = Field(0, serialization_alias="dpEarnedFromSettlements")
    dp_earned_from_session_close: int = Field(
        0,
        serialization_alias="dpEarnedFromSessionClose",
        description="Suma delta_dp con reason session_close_discipline en la ventana (US-BE-021 / US-BE-018).",
    )


class Bt2BehavioralMetricsOut(BaseModel):
    """
    Placeholder §B de `00_IDENTIDAD_PROYECTO.md`: métricas técnicas + copy humano demo.
    En producción el backend calculará valores; la UI solo traduce.
    """

    model_config = ConfigDict(populate_by_name=True)

    roi_pct: float = Field(serialization_alias="roiPct")
    roi_human_es: str = Field(serialization_alias="roiHumanEs")
    max_drawdown_units: float = Field(serialization_alias="maxDrawdownUnits")
    max_drawdown_human_es: str = Field(serialization_alias="maxDrawdownHumanEs")
    behavioral_block_count: int = Field(serialization_alias="behavioralBlockCount")
    estimated_loss_avoided_cop: float = Field(
        serialization_alias="estimatedLossAvoidedCop",
    )
    behavioral_human_es: str = Field(serialization_alias="behavioralHumanEs")
    hit_rate_pct: float = Field(serialization_alias="hitRatePct")
    hit_rate_human_es: str = Field(serialization_alias="hitRateHumanEs")
