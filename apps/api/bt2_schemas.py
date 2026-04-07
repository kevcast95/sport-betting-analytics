"""
Contratos JSON (US-DX-001) para BetTracker 2.0 — stub Sprint 01.
Serialización con alias camelCase para alinear con el cliente TypeScript.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    market_class: str = Field(serialization_alias="marketClass")
    market_label_es: str = Field(serialization_alias="marketLabelEs")
    event_label: str = Field(serialization_alias="eventLabel")
    titulo: str
    suggested_decimal_odds: float = Field(serialization_alias="suggestedDecimalOdds")
    edge_bps: int = Field(serialization_alias="edgeBps")
    selection_summary_es: str = Field(serialization_alias="selectionSummaryEs")
    traduccion_humana: str = Field(serialization_alias="traduccionHumana")
    curva_equidad: List[float] = Field(serialization_alias="curvaEquidad")
    access_tier: Literal["open", "premium"] = Field(serialization_alias="accessTier")
    unlock_cost_dp: int = Field(serialization_alias="unlockCostDp")
    operating_day_key: str = Field(serialization_alias="operatingDayKey")


class Bt2VaultPicksPageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    picks: List[Bt2VaultPickOut]
    generated_at_utc: str = Field(
        ...,
        serialization_alias="generatedAtUtc",
        description="Marca temporal del stub (estática en MVP).",
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
