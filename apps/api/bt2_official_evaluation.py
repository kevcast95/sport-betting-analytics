"""Estados y códigos de evaluación oficial v1 (ACTA T-244 / D-06-050).

Literales idénticos en DB, jobs y API; sin alias ni valores paralelos.
"""

from __future__ import annotations

import enum
from typing import Final

# ── Estados de evaluación (enum v1, strings exactos) ─────────────────────────

OFFICIAL_EVALUATION_STATUSES_V1: Final[tuple[str, ...]] = (
    "pending_result",
    "evaluated_hit",
    "evaluated_miss",
    "void",
    "no_evaluable",
)


class Bt2OfficialEvaluationStatus(str, enum.Enum):
    """Literales ACTA T-244 §3 — mismos valores que la columna `evaluation_status`."""

    pending_result = "pending_result"
    evaluated_hit = "evaluated_hit"
    evaluated_miss = "evaluated_miss"
    void = "void"
    no_evaluable = "no_evaluable"


def assert_official_evaluation_status(value: str) -> None:
    if value not in OFFICIAL_EVALUATION_STATUSES_V1:
        raise ValueError(
            f"evaluation_status inválido {value!r}; "
            f"v1 permitidos: {OFFICIAL_EVALUATION_STATUSES_V1}"
        )


# ── Motivos de descarte / no evaluable (catálogo ACTA T-244 §4) ────────────────

NO_EVALUABLE_REASON_CODES_V1: Final[frozenset[str]] = frozenset(
    {
        "MISSING_FIXTURE_CORE",
        "MISSING_VALID_ODDS",
        "INSUFFICIENT_MARKET_FAMILIES",
        "MISSING_DS_INPUT_CRITICAL",
        "OUTSIDE_SUPPORTED_MARKET_V1",
        "MISSING_TRUTH_SOURCE",
        "EVENT_NOT_SETTLED",
        "MARKET_MAPPING_UNRESOLVED",
        "VOID_OFFICIAL_EVENT",
    }
)


def assert_no_evaluable_reason_code(value: str) -> None:
    if value not in NO_EVALUABLE_REASON_CODES_V1:
        raise ValueError(
            f"no_evaluable_reason inválido {value!r}; "
            f"v1 permitidos: {sorted(NO_EVALUABLE_REASON_CODES_V1)}"
        )
