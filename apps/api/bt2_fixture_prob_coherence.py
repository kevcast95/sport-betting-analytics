"""
§1.3 — Coherencia probabilística MVP sobre `consensus` (misma forma que AggregatedOdds).

Solo lectura numérica reproducible; no sustituye DSR. Flags no bloquean picks por defecto.
"""

from __future__ import annotations

from typing import Any, Optional

from apps.api.bt2_dsr_contract import DsProbCoherenceDiagnostics, ProbCoherenceFlag
from apps.api.bt2_dsr_odds_aggregation import ft_1x2_book_spread_ratio

# Umbrales por defecto (documentados en spec; ajustables si producto lo pide)
_DEFAULT_MAX_RAW_OVERROUND_1X2: float = 1.12
_DEFAULT_MAX_FT_1X2_SPREAD: float = 1.12
_DEFAULT_MAX_RAW_OVERROUND_OU25: float = 1.15


def proportional_devig_three_way(
    odds_home: float,
    odds_draw: float,
    odds_away: float,
) -> tuple[float, float, float]:
    ih = 1.0 / odds_home
    id_ = 1.0 / odds_draw
    ia = 1.0 / odds_away
    s = ih + id_ + ia
    if s <= 0:
        return (0.0, 0.0, 0.0)
    return (ih / s, id_ / s, ia / s)


def evaluate_fixture_prob_coherence(
    consensus: dict[str, dict[str, float]],
    *,
    max_raw_overround_1x2: float = _DEFAULT_MAX_RAW_OVERROUND_1X2,
    max_ft_1x2_spread: float = _DEFAULT_MAX_FT_1X2_SPREAD,
    max_raw_overround_ou25: float = _DEFAULT_MAX_RAW_OVERROUND_OU25,
) -> DsProbCoherenceDiagnostics:
    """
    Calcula métricas compactas a partir del mapa consensus (post medianas).

    Returns:
        Modelo validable que el builder serializa en `diagnostics.prob_coherence`.
    """
    notes: list[str] = []
    ft_sub = consensus.get("FT_1X2") or {}
    oh = ft_sub.get("home")
    od = ft_sub.get("draw")
    oa = ft_sub.get("away")

    if not (
        oh is not None
        and od is not None
        and oa is not None
        and oh > 1.0
        and od > 1.0
        and oa > 1.0
    ):
        return DsProbCoherenceDiagnostics(
            flag="coherence_na",
            notes=["missing_or_invalid_ft_1x2_consensus"],
        )

    ih, id_, ia = 1.0 / float(oh), 1.0 / float(od), 1.0 / float(oa)
    raw_1x2 = ih + id_ + ia
    spread = ft_1x2_book_spread_ratio(consensus)

    ou_sub = consensus.get("OU_GOALS_2_5") or {}
    oo = ou_sub.get("over_2_5")
    uu = ou_sub.get("under_2_5")
    ou_raw: Optional[float] = None
    if oo is not None and uu is not None and float(oo) > 1.0 and float(uu) > 1.0:
        ou_raw = 1.0 / float(oo) + 1.0 / float(uu)

    if raw_1x2 > max_raw_overround_1x2:
        notes.append("ft_1x2_implied_sum_raw_above_threshold")
    if spread is not None and spread > max_ft_1x2_spread:
        notes.append("ft_1x2_book_spread_ratio_above_threshold")
    if ou_raw is not None and ou_raw > max_raw_overround_ou25:
        notes.append("ou_25_implied_sum_raw_above_threshold")

    flag: ProbCoherenceFlag = "coherence_ok" if not notes else "coherence_warning"

    return DsProbCoherenceDiagnostics(
        flag=flag,
        ft_1x2_implied_sum_raw=round(raw_1x2, 6),
        ft_1x2_book_spread_ratio=round(spread, 6) if spread is not None else None,
        ou_25_implied_sum_raw=round(ou_raw, 6) if ou_raw is not None else None,
        notes=notes,
    )


def prob_coherence_dict_for_ds_input(consensus: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Dict JSON-serializable listo para `diagnostics["prob_coherence"]`."""
    return evaluate_fixture_prob_coherence(consensus).model_dump()
