"""
US-DX-002 / D-06-002 — contrato entrada DSR producción (anti-fuga).

Validación mínima: rechazar claves que sugieran resultado conocido o post-partido.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

PIPELINE_VERSION_DEFAULT: str = "s6-rules-v0"

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
    """Lote de entrada producción diaria — sin datos post-partido."""

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
