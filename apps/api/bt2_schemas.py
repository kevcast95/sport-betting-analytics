"""
Contratos JSON (US-DX-001) para BetTracker 2.0 — stub Sprint 01.
Serialización con alias camelCase para alinear con el cliente TypeScript.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

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
    dsr_enabled: bool = Field(
        default=True,
        serialization_alias="dsrEnabled",
        description="Lo que el proceso del API leyó al arrancar; deepseek batch solo si true y clave.",
    )
    dsr_provider: str = Field(
        default="rules",
        serialization_alias="dsrProvider",
    )
    deepseek_configured: bool = Field(
        default=False,
        serialization_alias="deepseekConfigured",
        description="Clave no vacía (no se expone el valor).",
    )
    sfs_markets_fusion_enabled: bool = Field(
        default=False,
        serialization_alias="sfsMarketsFusionEnabled",
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
    unlock_eligible: bool = Field(
        True,
        serialization_alias="unlockEligible",
        description=(
            "True si POST /vault/standard-unlock y /vault/premium-unlock pueden aplicar "
            "(no estado terminal / kickoff futuro). Distinto de is_available (estricto para POST /picks)."
        ),
    )
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
        description="True si desbloqueó premium (DP) o legado con pick abierto en el evento.",
    )
    standard_unlocked: bool = Field(
        False,
        serialization_alias="standardUnlocked",
        description="True si liberó el ítem estándar explícitamente o legado con pick abierto en el evento.",
    )
    content_unlocked: bool = Field(
        False,
        serialization_alias="contentUnlocked",
        description="True si puede ver selección/cuota/racional completo (standard o premium liberado).",
    )
    user_pick_commitment: Optional[Literal["taken", "not_taken"]] = Field(
        None,
        serialization_alias="userPickCommitment",
        description="Marcación manual tomó apuesta / no tomó (solo tras liberar).",
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
        description="Legado; reemplazada en producto por evidence/predictive tiers.",
    )
    estimated_hit_probability: Optional[float] = Field(
        None,
        serialization_alias="estimatedHitProbability",
        description="Estimación 0–1 (no calibración definitiva).",
    )
    evidence_quality: Optional[str] = Field(
        None,
        serialization_alias="evidenceQuality",
        description="low | medium | high — respaldo del input.",
    )
    predictive_tier: Optional[str] = Field(
        None,
        serialization_alias="predictiveTier",
        description="low | medium | high — fuerza relativa en el ranking del día.",
    )
    action_tier: Optional[str] = Field(
        None,
        serialization_alias="actionTier",
        description="free | premium — tratamiento producto/bóveda.",
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
        validation_alias=AliasChoices("vaultPickId", "vault_pick_id"),
        serialization_alias="vaultPickId",
        description="Id del ítem en vault (p. ej. dp-7).",
    )


class VaultPremiumUnlockOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(..., serialization_alias="vaultPickId")
    premium_unlocked: bool = Field(True, serialization_alias="premiumUnlocked")
    dp_balance_after: int = Field(..., serialization_alias="dpBalanceAfter")


class VaultStandardUnlockIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("vaultPickId", "vault_pick_id"),
        serialization_alias="vaultPickId",
        description="Ítem vault (dp-12 o 12).",
    )


class VaultStandardUnlockOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(..., serialization_alias="vaultPickId")
    standard_unlocked: bool = Field(True, serialization_alias="standardUnlocked")


class VaultPickCommitmentIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(
        ...,
        validation_alias=AliasChoices("vaultPickId", "vault_pick_id"),
        serialization_alias="vaultPickId",
    )
    commitment: Literal["taken", "not_taken"] = Field(...)


class VaultPickCommitmentOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vault_pick_id: str = Field(..., serialization_alias="vaultPickId")
    commitment: Literal["taken", "not_taken"] = Field(...)


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
    free_picks_unlocked_today: int = Field(
        0,
        serialization_alias="freePicksUnlockedToday",
        description="Liberaciones estándar (sin DP) del día operativo.",
    )
    premium_picks_unlocked_today: int = Field(
        0,
        serialization_alias="premiumPicksUnlockedToday",
        description="Liberaciones premium (con DP) del día operativo.",
    )
    total_picks_unlocked_today: int = Field(
        0,
        serialization_alias="totalPicksUnlockedToday",
        description="Total ítems liberados hoy (≤5; conteo servidor).",
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


class Bt2AdminDsrRangeTotalsOut(BaseModel):
    """Agregado global sobre el rango [from, to] (misma semántica que dsr-day por fila)."""

    model_config = ConfigDict(populate_by_name=True)

    day_count: int = Field(..., serialization_alias="dayCount")
    days_with_settled_model: int = Field(
        ...,
        serialization_alias="daysWithSettledModel",
        description="Días con al menos un pick liquidado y model_prediction_result no null.",
    )
    sum_distinct_events_daily: int = Field(
        ...,
        serialization_alias="sumDistinctEventsDaily",
        description="Suma de eventos distintos por día (no deduplica eventos entre días).",
    )
    picks_settled_with_model: int = Field(
        ...,
        serialization_alias="picksSettledWithModel",
    )
    model_hits: int = Field(..., serialization_alias="modelHits")
    model_misses: int = Field(..., serialization_alias="modelMisses")
    model_voids: int = Field(..., serialization_alias="modelVoids")
    model_na: int = Field(..., serialization_alias="modelNa")
    hit_rate_pct: Optional[float] = Field(
        None,
        serialization_alias="hitRatePct",
        description="Suma hits / (suma hits + suma misses) × 100.",
    )
    summary_human_es: str = Field("", serialization_alias="summaryHumanEs")


class Bt2AdminDsrRangeOut(BaseModel):
    """Serie diaria + totales; útil para auditoría histórica en admin (D-06-004)."""

    model_config = ConfigDict(populate_by_name=True)

    from_operating_day_key: str = Field(
        ..., serialization_alias="fromOperatingDayKey"
    )
    to_operating_day_key: str = Field(..., serialization_alias="toOperatingDayKey")
    days: List[Bt2AdminDsrDaySummaryOut] = Field(
        default_factory=list,
        description="Una fila por día calendario en el rango (inclusive), orden ascendente.",
    )
    totals: Bt2AdminDsrRangeTotalsOut


class Bt2AdminOfficialEvaluationLoopOut(BaseModel):
    """T-233 / base T-238 — métricas del cierre de loop vs verdad oficial (ACTA T-244)."""

    model_config = ConfigDict(populate_by_name=True)

    suggested_picks_count: int = Field(
        ...,
        alias="suggestedPicksCount",
        description="Filas `bt2_daily_picks` (opcionalmente filtradas por día operativo).",
    )
    official_evaluation_enrolled: int = Field(
        ...,
        alias="officialEvaluationEnrolled",
        description="Filas en `bt2_pick_official_evaluation` (misma ventana que el filtro).",
    )
    pending_result: int = Field(..., alias="pendingResult")
    evaluated_hit: int = Field(..., alias="evaluatedHit")
    evaluated_miss: int = Field(..., alias="evaluatedMiss")
    void_count: int = Field(..., alias="voidCount")
    no_evaluable: int = Field(..., alias="noEvaluable")
    hit_rate_on_scored_pct: Optional[float] = Field(
        None,
        alias="hitRateOnScoredPct",
        description="hits / (hits + misses) × 100; excluye void, no_evaluable y pending.",
    )
    no_evaluable_by_reason: dict[str, int] = Field(
        default_factory=dict,
        alias="noEvaluableByReason",
    )
    summary_human_es: str = Field("", alias="summaryHumanEs")
    operating_day_key_filter: Optional[str] = Field(
        None,
        alias="operatingDayKeyFilter",
        description="Si se pasó filtro YYYY-MM-DD; None = global.",
    )


class Bt2AdminPoolCoverageOut(BaseModel):
    """Cobertura pool desde `bt2_pool_eligibility_audit` (última fila por evento)."""

    model_config = ConfigDict(populate_by_name=True)

    candidate_events_count: int = Field(
        ...,
        alias="candidateEventsCount",
        description="Eventos distintos en `bt2_daily_picks` para el día.",
    )
    eligible_events_count: int = Field(
        ...,
        alias="eligibleEventsCount",
        description="Candidatos cuya última auditoría marca `is_eligible=true`.",
    )
    events_with_latest_audit: int = Field(
        ...,
        alias="eventsWithLatestAudit",
        description="Candidatos con al menos una fila de auditoría.",
    )
    pool_eligibility_rate_pct: Optional[float] = Field(
        None,
        alias="poolEligibilityRatePct",
        description="elegibles / candidatos × 100 (sin auditoría cuenta como no elegible).",
    )
    pool_discard_reason_breakdown: dict[str, int] = Field(
        default_factory=dict,
        alias="poolDiscardReasonBreakdown",
        description="Solo filas ineligibles o sin auditoría; claves canónicas ACTA + `(sin auditoría reciente)`.",
    )


class Bt2AdminOfficialPrecisionBucketOut(BaseModel):
    """Desglose de precisión oficial por mercado o por bucket de confianza (T-239)."""

    model_config = ConfigDict(populate_by_name=True)

    bucket_key: str = Field(
        ...,
        alias="bucketKey",
        description="`market_canonical` o `dsr_confidence_label` normalizado.",
    )
    evaluated_hit: int = Field(..., alias="evaluatedHit")
    evaluated_miss: int = Field(..., alias="evaluatedMiss")
    pending_result: int = Field(..., alias="pendingResult")
    no_evaluable: int = Field(..., alias="noEvaluable")
    void_count: int = Field(..., alias="voidCount")
    hit_rate_on_scored_pct: Optional[float] = Field(
        None,
        alias="hitRateOnScoredPct",
        description="Solo hit/(hit+miss) en el bucket; no mezcla pending/no_evaluable.",
    )


class Bt2AdminFase1OperationalSummaryOut(BaseModel):
    """US-BE-052 / T-238 — resumen admin: pool, loop oficial, precisión por mercado y confianza."""

    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(
        ...,
        alias="operatingDayKey",
        description=(
            "YYYY-MM-DD del día operativo, o `__ALL__` cuando la petición usó "
            "`accumulated=true` (métricas sin filtrar por día)."
        ),
    )
    pool_coverage: Bt2AdminPoolCoverageOut = Field(..., alias="poolCoverage")
    official_evaluation_loop: Bt2AdminOfficialEvaluationLoopOut = Field(
        ...,
        alias="officialEvaluationLoop",
    )
    precision_by_market: List[Bt2AdminOfficialPrecisionBucketOut] = Field(
        default_factory=list,
        alias="precisionByMarket",
    )
    precision_by_confidence: List[Bt2AdminOfficialPrecisionBucketOut] = Field(
        default_factory=list,
        alias="precisionByConfidence",
    )
    summary_human_es: str = Field("", alias="summaryHumanEs")
    pool_eligibility_min_families_required: int = Field(
        ...,
        alias="poolEligibilityMinFamiliesRequired",
        description=(
            "Umbral activo leído de BT2_POOL_ELIGIBILITY_MIN_FAMILIES (default 2 = canónico S6.3). "
            "Las filas de `poolCoverage` siguen viniendo de la última auditoría en BD."
        ),
    )
    pool_eligibility_official_reference_s63: int = Field(
        ...,
        alias="poolEligibilityOfficialReferenceS63",
        description="Referencia fija de producto: mínimo 2 familias (S6.3); no depende del env.",
    )
    pool_eligibility_observability_relaxed: bool = Field(
        ...,
        alias="poolEligibilityObservabilityRelaxed",
        description="True si el umbral activo es menor que la referencia oficial (modo observabilidad).",
    )
    pool_eligibility_config_note_es: str = Field(
        "",
        alias="poolEligibilityConfigNoteEs",
        description="Nota cuando el umbral está relajado; vacío si modo oficial (min ≥ referencia).",
    )


class Bt2AdminF2PoolMetricsOut(BaseModel):
    """T-263 — KPI F2: oficial vs relajado, umbrales 60/40, desglose por liga (§6 norma F2)."""

    model_config = ConfigDict(populate_by_name=True)

    league_bt2_ids_resolved: List[int] = Field(
        default_factory=list,
        alias="leagueBt2IdsResolved",
        description="IDs `bt2_leagues` del universo de 5 ligas (env o resolución por sportmonks_id).",
    )
    window_from: Optional[str] = Field(None, alias="windowFrom")
    window_to: Optional[str] = Field(None, alias="windowTo")
    operating_day_key_filter: Optional[str] = Field(
        None,
        alias="operatingDayKeyFilter",
        description="Si se filtró un solo día; null = ventana rolling `days`.",
    )
    metrics_global: Dict[str, Any] = Field(default_factory=dict, alias="metricsGlobal")
    metrics_by_league: List[Dict[str, Any]] = Field(
        default_factory=list,
        alias="metricsByLeague",
    )
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    insufficient_market_families_dominant: Optional[bool] = Field(
        None,
        alias="insufficientMarketFamiliesDominant",
        description="True si INSUFFICIENT_MARKET_FAMILIES ≥ ~50% descartes oficiales.",
    )
    note_es: str = Field("", alias="noteEs")


class Bt2AdminRefreshCdmFromSmOut(BaseModel):
    """POST refresh SM → raw → CDM + evaluación oficial opcional (admin Fase 1)."""

    model_config = ConfigDict(populate_by_name=True)

    ok: bool
    operating_day_key: str = Field(..., alias="operatingDayKey")
    message_es: str = Field(..., alias="messageEs")
    fixtures_targeted: int = Field(..., alias="fixturesTargeted")
    unique_sportmonks_fixtures_processed: int = Field(
        0,
        alias="uniqueSportmonksFixturesProcessed",
    )
    sm_fetch_ok: int = Field(..., alias="smFetchOk")
    raw_upsert_ok: int = Field(..., alias="rawUpsertOk")
    cdm_normalized_ok: int = Field(..., alias="cdmNormalizedOk")
    cdm_skipped: int = Field(..., alias="cdmSkipped")
    cdm_errors: int = Field(..., alias="cdmErrors")
    official_evaluation: Optional[Dict[str, Any]] = Field(
        None,
        alias="officialEvaluation",
        description="Salida de `job_summary_dict` si se ejecutó evaluate; null si se omitió.",
    )
    notes: List[str] = Field(default_factory=list)


MonitorOutcomeLiteral = Literal["si", "no", "pendiente", "void", "ne"]


class Bt2AdminMonitorRoiFlatStakeOut(BaseModel):
    """ROI con stake fijo 1 unidad por pick y cuota decimal consenso CDM (mediana casas)."""

    model_config = ConfigDict(populate_by_name=True)

    net_units: float = Field(..., alias="netUnits")
    roi_pct: Optional[float] = Field(
        None,
        alias="roiPct",
        description="net_units / picks_counted × 100 sobre picks SI/NO con cuota.",
    )
    picks_counted: int = Field(
        ...,
        alias="picksCounted",
        description="Scored con cuota en consenso (entre en ROI).",
    )
    picks_missing_odds: int = Field(
        0,
        alias="picksMissingOdds",
        description="Scored sin selección encontrada en consenso.",
    )


class Bt2AdminMonitorSummaryOut(BaseModel):
    """Agregados monitor (sistema o «tus picks» operados)."""

    model_config = ConfigDict(populate_by_name=True)

    total_picks: int = Field(..., alias="totalPicks")
    hits: int
    misses: int
    pending: int
    void_count: int = Field(..., alias="voidCount")
    no_evaluable: int = Field(..., alias="noEvaluable")
    evaluated_scored: int = Field(
        ...,
        alias="evaluatedScored",
        description="aciertos + fallos (denominador de la tasa).",
    )
    hit_rate_pct: Optional[float] = Field(None, alias="hitRatePct")
    roi_flat_stake: Bt2AdminMonitorRoiFlatStakeOut = Field(..., alias="roiFlatStake")


class Bt2AdminMonitorTodayOut(BaseModel):
    """Resumen rápido del día operativo actual (America/Bogota)."""

    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(..., alias="operatingDayKey")
    total_picks: int = Field(..., alias="totalPicks")
    resolved: int = Field(
        ...,
        description="Filas con evaluación distinta de pending_result.",
    )
    pending: int


class Bt2AdminMonitorRowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    daily_pick_id: int = Field(..., alias="dailyPickId")
    operating_day_key: str = Field(..., alias="operatingDayKey")
    event_id: int = Field(..., alias="eventId")
    user_id: str = Field(..., alias="userId")
    event_label: str = Field(..., alias="eventLabel")
    market_label_es: str = Field(..., alias="marketLabelEs")
    selection_summary_es: str = Field(..., alias="selectionSummaryEs")
    score_text: str = Field(..., alias="scoreText")
    outcome: MonitorOutcomeLiteral
    i_operated: bool = Field(..., alias="iOperated")
    decimal_odds: Optional[float] = Field(
        None,
        alias="decimalOdds",
        description="Decimal consenso si existe en odds agregadas.",
    )
    flat_stake_return_units: Optional[float] = Field(
        None,
        alias="flatStakeReturnUnits",
        description="+(O−1) en acierto, −1 en fallo, stake 1 u.",
    )


class Bt2AdminMonitorSmSyncOut(BaseModel):
    """SportMonks → CDM + evaluación oficial (solo si `syncFromSportmonks` en el GET)."""

    model_config = ConfigDict(populate_by_name=True)

    attempted: bool
    ok: bool
    message_es: str = Field("", alias="messageEs")
    fixtures_targeted: int = Field(0, alias="fixturesTargeted")
    unique_fixtures_processed: int = Field(0, alias="uniqueFixturesProcessed")
    closed_pending_to_final: Optional[int] = Field(
        None,
        alias="closedPendingToFinal",
        description="Filas pending→final en la corrida de evaluación tras el sync.",
    )


class Bt2AdminBacktestReplayRangeOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    range_from: str = Field(..., alias="from")
    range_to: str = Field(..., alias="to")
    preset: str = Field("range", alias="preset")


class Bt2AdminBacktestReplaySummaryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_picks: int = Field(..., alias="totalPicks")
    hits: int
    misses: int
    pending: int
    void_count: int = Field(..., alias="voidCount")
    no_evaluable: int = Field(..., alias="noEvaluable")
    evaluated_scored: int = Field(..., alias="evaluatedScored")
    hit_rate_pct: Optional[float] = Field(None, alias="hitRatePct")
    candidate_events: int = Field(..., alias="candidateEvents")
    eligible_events: int = Field(..., alias="eligibleEvents")
    useful_input_events: int = Field(
        ...,
        alias="usefulInputEvents",
        description="Elegibles con completitud de mercados en consensus ≥ umbral replay.",
    )
    generated_days: int = Field(..., alias="generatedDays")


class Bt2AdminBacktestReplayDailyOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(..., alias="operatingDayKey")
    total_picks: int = Field(..., alias="totalPicks")
    hits: int
    misses: int
    pending: int
    void_count: int = Field(..., alias="voidCount")
    no_evaluable: int = Field(..., alias="noEvaluable")
    evaluated_scored: int = Field(..., alias="evaluatedScored")
    hit_rate_pct: Optional[float] = Field(None, alias="hitRatePct")
    candidate_events: int = Field(..., alias="candidateEvents")
    eligible_events: int = Field(..., alias="eligibleEvents")
    useful_input_events: int = Field(..., alias="usefulInputEvents")
    scored_picks: int = Field(..., alias="scoredPicks")
    by_market: dict[str, int] = Field(default_factory=dict, alias="byMarket")
    by_action_tier: dict[str, int] = Field(default_factory=dict, alias="byActionTier")


class Bt2AdminBacktestReplayDistributionRowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    market: Optional[str] = None
    action_tier: Optional[str] = Field(None, alias="actionTier")
    picks: int
    hits: int
    misses: int


class Bt2AdminBacktestReplayDistributionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    by_market: List[Bt2AdminBacktestReplayDistributionRowOut] = Field(
        default_factory=list,
        alias="byMarket",
    )
    by_action_tier: List[Bt2AdminBacktestReplayDistributionRowOut] = Field(
        default_factory=list,
        alias="byActionTier",
    )


class Bt2AdminBacktestReplayRowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operating_day_key: str = Field(..., alias="operatingDayKey")
    real_kickoff_day_key: str = Field(..., alias="realKickoffDayKey")
    daily_pick_id: int = Field(..., alias="dailyPickId")
    event_id: int = Field(..., alias="eventId")
    event_label: str = Field(..., alias="eventLabel")
    league_label: Optional[str] = Field(None, alias="leagueLabel")
    market_label_es: str = Field(..., alias="marketLabelEs")
    selection_summary_es: str = Field(..., alias="selectionSummaryEs")
    action_tier: str = Field(..., alias="actionTier")
    outcome: str
    score_text: str = Field(..., alias="scoreText")
    input_coverage_score: int = Field(..., alias="inputCoverageScore")


class Bt2AdminBacktestReplayOut(BaseModel):
    """GET admin — replay ciego del pipeline DSR sobre datos históricos en Postgres."""

    model_config = ConfigDict(populate_by_name=True)

    timezone_label: str = Field("America/Bogota", alias="timezoneLabel")
    summary_human_es: str = Field("", alias="summaryHumanEs")
    replay_range: Bt2AdminBacktestReplayRangeOut = Field(..., alias="range")
    summary: Bt2AdminBacktestReplaySummaryOut
    daily: List[Bt2AdminBacktestReplayDailyOut] = Field(default_factory=list)
    distribution: Bt2AdminBacktestReplayDistributionOut
    rows: List[Bt2AdminBacktestReplayRowOut] = Field(default_factory=list)
    replay_meta: dict[str, Any] = Field(default_factory=dict, alias="replayMeta")


class Bt2AdminMonitorResultadosOut(BaseModel):
    """GET admin — monitor de resultados (evaluación oficial vs `bt2_daily_picks`)."""

    model_config = ConfigDict(populate_by_name=True)

    operating_day_key_from: str = Field(..., alias="operatingDayKeyFrom")
    operating_day_key_to: str = Field(..., alias="operatingDayKeyTo")
    timezone_label: str = Field("America/Bogota", alias="timezoneLabel")
    today_operating_day_key: str = Field(..., alias="todayOperatingDayKey")
    focus_operating_day_key: str = Field(
        ...,
        alias="focusOperatingDayKey",
        description="Día del bloque «hoy»: coincide con el rango si from==to; si no, hoy calendario TZ ref.",
    )
    system: Bt2AdminMonitorSummaryOut
    yours: Optional[Bt2AdminMonitorSummaryOut] = Field(
        None,
        description="Solo si se envió monitorUserId; solo picks operados ese día.",
    )
    today: Bt2AdminMonitorTodayOut
    rows: List[Bt2AdminMonitorRowOut] = Field(default_factory=list)
    summary_human_es: str = Field("", alias="summaryHumanEs")
    sm_sync: Bt2AdminMonitorSmSyncOut = Field(..., alias="smSync")
    rows_total: Optional[int] = Field(
        None,
        alias="rowsTotal",
        description="Total de filas que cumplen filtros (paginación servidor).",
    )
    rows_offset: int = Field(0, alias="rowsOffset")
    rows_limit: int = Field(1500, alias="rowsLimit")


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
