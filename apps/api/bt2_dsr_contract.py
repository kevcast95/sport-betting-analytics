"""
US-DX-002 / D-06-002 — contrato entrada DSR producción (anti-fuga).

T-172 — modelos whitelist `ds_input` fase 1 (extra=forbid) + validación de envelope lote LLM.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PIPELINE_VERSION_DEFAULT: str = "s6-rules-v0"
# Versión pública API (`GET /bt2/meta`) y hito DX S6.2 cubo A + diagnostics ampliados.
CONTRACT_VERSION_PUBLIC: str = "bt2-dx-001-s6.2r2"
CONTRACT_VERSION_S6_1: str = "bt2-dx-001-s6.1r1"  # histórico / comparativas

# Claves prohibidas en objetos anidados (substring case-insensitive)
_FORBIDDEN_SUBSTRINGS = (
    "result_home",
    "result_away",
    "final_score",
    "fulltime_score",
    "match_winner",
    "winner_team",
    "goals_home",
    "goals_away",
    "score_ht",
    "penalty_shootout",
)


class DsrProductionCandidateOdds(BaseModel):
    """Subconjunto seguro de odds para un candidato (sin PII)."""

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(..., ge=1)
    odds_1x2: dict[str, float] = Field(default_factory=dict)
    odds_ou_25: dict[str, float] = Field(default_factory=dict)


class DsrProductionBatchIn(BaseModel):
    """Lote legado tests / herramientas — sin datos post-partido."""

    model_config = ConfigDict(extra="forbid")

    operating_day_key: str = Field(..., min_length=10, max_length=10)
    pipeline_version: str = Field(default=PIPELINE_VERSION_DEFAULT, max_length=40)
    candidates: list[DsrProductionCandidateOdds] = Field(default_factory=list)

    @field_validator("candidates")
    @classmethod
    def _non_empty(cls, v: list[DsrProductionCandidateOdds]) -> list[DsrProductionCandidateOdds]:
        if not v:
            raise ValueError("candidates no puede estar vacío para invocación DSR")
        return v


# ── T-172 — whitelist `ds_input[]` (DX bt2_ds_input_v1_parity_fase1.md §3) ─────


class DsScheduleDisplay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utc_iso: str = Field(..., min_length=4)
    local_iso: Optional[str] = None
    timezone_reference: Optional[str] = Field(default="UTC", max_length=32)


class DsEventContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    league_name: str
    country: Optional[str] = None
    league_tier: Optional[str] = Field(default=None, max_length=8)
    home_team: str
    away_team: str
    start_timestamp_unix: Optional[int] = None
    match_state: str = Field(..., max_length=32)


class DsByBookmakerRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bookmaker: str = Field(..., max_length=120)
    market_canonical: str = Field(..., max_length=64)
    selection_canonical: str = Field(..., max_length=64)
    decimal: float = Field(..., gt=1.0)
    fetched_at: str = Field(..., max_length=64)


class DsOddsIngestMeta(BaseModel):
    """T-190 — ventana de ingesta en snapshot (sin serie completa de cuotas; gap documentado en DX)."""

    model_config = ConfigDict(extra="forbid")

    first_fetched_at_iso: str = Field(..., max_length=64)
    last_fetched_at_iso: str = Field(..., max_length=64)
    distinct_fetch_batches: int = Field(..., ge=0, le=10_000)


class DsOddsFeatured(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consensus: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_bookmaker: Optional[list[DsByBookmakerRow]] = None
    ingest_meta: Optional[DsOddsIngestMeta] = None


def _empty_or_unavailable_block(d: Any) -> bool:
    if d == {}:
        return True
    if isinstance(d, dict) and len(d) == 1 and d.get("available") is False:
        return True
    return False


class DsProcessedF1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    odds_featured: DsOddsFeatured
    lineups: dict[str, Any]
    h2h: dict[str, Any]
    statistics: dict[str, Any]
    team_streaks: dict[str, Any]
    team_season_stats: dict[str, Any]
    # SportMonks fixture includes (opcionales; base = {available: false})
    fixture_conditions: dict[str, Any]
    match_officials: dict[str, Any]
    squad_availability: dict[str, Any]
    tactical_shape: dict[str, Any]
    prediction_signals: dict[str, Any]
    broadcast_notes: dict[str, Any]
    fixture_advanced_sm: dict[str, Any]

    @field_validator(
        "lineups",
        "h2h",
        "statistics",
        "team_streaks",
        "team_season_stats",
        "fixture_conditions",
        "match_officials",
        "squad_availability",
        "tactical_shape",
        "prediction_signals",
        "broadcast_notes",
        "fixture_advanced_sm",
    )
    @classmethod
    def _processed_context_blocks(cls, v: dict[str, Any]) -> dict[str, Any]:
        # D-06-028: permitir {available:true,...} con claves seguras (T-172 + assert_no_forbidden_ds_keys al validar ítem).
        if _empty_or_unavailable_block(v):
            return v
        if isinstance(v, dict) and v.get("available") is True:
            assert_no_forbidden_ds_keys(v)
            return v
        raise ValueError("bloque processed: {}, {available:false} o {available:true} sin claves prohibidas (D-06-002)")


class DsDiagnosticsF1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_coverage: dict[str, bool]
    markets_available: Optional[list[str]] = None
    lineups_ok: bool
    h2h_ok: bool
    statistics_ok: bool
    fetch_errors: list[str]
    # T-203 / D-06-038 — gap explícito cuando no hay fila raw (ingesta/429/worker).
    raw_fixture_missing: bool = False
    team_season_stats_reason: Optional[str] = None


class DsInputItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(..., ge=1)
    sport: Literal["football"]
    selection_tier: Literal["A", "B"]
    schedule_display: DsScheduleDisplay
    event_context: DsEventContext
    processed: DsProcessedF1
    diagnostics: DsDiagnosticsF1


class DsrLlmBatchEnvelope(BaseModel):
    """Envelope enviado al prompt usuario (whitelist §2)."""

    model_config = ConfigDict(extra="forbid")

    operating_day_key: str = Field(..., min_length=10, max_length=10)
    pipeline_version: str = Field(default=PIPELINE_VERSION_DEFAULT, max_length=48)
    sport: Literal["football"] = "football"
    ds_input: list[DsInputItem]

    @field_validator("ds_input")
    @classmethod
    def _non_empty_ds(cls, v: list[DsInputItem]) -> list[DsInputItem]:
        if not v:
            raise ValueError("ds_input no puede estar vacío para invocación DSR")
        return v


def validate_ds_input_item_dict(item: dict[str, Any]) -> DsInputItem:
    assert_no_forbidden_ds_keys(item)
    return DsInputItem.model_validate(item)


def validate_ds_batch_envelope(batch: dict[str, Any]) -> DsrLlmBatchEnvelope:
    assert_no_forbidden_ds_keys(batch)
    return DsrLlmBatchEnvelope.model_validate(batch)


def assert_no_forbidden_ds_keys(obj: Any, path: str = "$") -> None:
    """Recorre JSON-like y lanza ValueError si aparece semántica prohibida."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            for bad in _FORBIDDEN_SUBSTRINGS:
                if bad in kl:
                    raise ValueError(f"Clave prohibida en input DSR ({path}.{k}) — D-06-002")
            assert_no_forbidden_ds_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            assert_no_forbidden_ds_keys(item, f"{path}[{i}]")


def hash_dsr_input_payload(payload: dict[str, Any]) -> str:
    """Huella estable para auditoría (sin PII)."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
