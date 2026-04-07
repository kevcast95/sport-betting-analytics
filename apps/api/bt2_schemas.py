"""
Contratos JSON (US-DX-001) para BetTracker 2.0 — stub Sprint 01.
Serialización con alias camelCase para alinear con el cliente TypeScript.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Bt2MetaOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    contract_version: str = Field(
        default="bt2-dx-001-stub-1",
        serialization_alias="contractVersion",
        description="Versión del contrato stub; bump al cambiar shape.",
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
    external_search_url: str = Field("", serialization_alias="externalSearchUrl")


class Bt2VaultPicksPageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    picks: List[Bt2VaultPickOut]
    generated_at_utc: str = Field(
        ...,
        serialization_alias="generatedAtUtc",
        description="Marca temporal de generación.",
    )
    message: Optional[str] = Field(None, serialization_alias="message")


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
