"""
Cuatro dimensiones de señal por pick (producto) + integración de prob_coherence como sanidad, no motor autónomo.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from apps.api.bt2_fixture_prob_coherence import evaluate_fixture_prob_coherence
from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds

EvidenceQuality = Literal["low", "medium", "high"]
PredictiveTier = Literal["low", "medium", "high"]
ActionTier = Literal["free", "premium"]
AccessTierDB = Literal["standard", "premium"]

MAX_PREMIUM_SLOTS = 2
MIN_PREMIUM_STRENGTH = 0.42


def league_eligible_for_snapshot(league_tier: Optional[str]) -> bool:
    """Solo ligas S y A entran en la bóveda accionable."""
    t = (league_tier or "").strip().upper()
    return t in ("S", "A")


def prob_coherence_flag_for_agg(agg: AggregatedOdds) -> str:
    d = evaluate_fixture_prob_coherence(agg.consensus)
    return str(d.flag or "coherence_na")


def _coherence_multipliers(flag: str) -> tuple[float, float]:
    """
    (evidence_score_0_1_adj, p_hat_multiplier)
    prob_coherence: refuerzo/penalización leve, nunca decide mercado.
    """
    f = (flag or "").strip().lower()
    if f == "coherence_ok":
        return 0.08, 1.03
    if f in ("coherence_warning",):
        return -0.1, 0.92
    return 0.0, 0.98


def evidence_quality_from(
    data_completeness: int,
    prob_coherence_flag: str,
) -> EvidenceQuality:
    c = max(0, min(100, int(data_completeness)))
    ev = 0.0
    if c >= 72:
        ev = 0.75
    elif c >= 45:
        ev = 0.5
    else:
        ev = 0.25
    ev += _coherence_multipliers(prob_coherence_flag)[0]
    ev = max(0.0, min(1.0, ev))
    if ev >= 0.62:
        return "high"
    if ev >= 0.38:
        return "medium"
    return "low"


def estimate_hit_probability(
    consensus: dict[str, dict[str, float]],
    market_canonical: str,
    selection_canonical: str,
    prob_coherence_flag: str,
) -> float:
    sub = consensus.get((market_canonical or "").strip().upper()) or {}
    sc = (selection_canonical or "").strip().lower()
    raw = sub.get(sc)
    try:
        od = float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        od = 0.0
    if od > 1.0:
        p = 1.0 / od
    else:
        p = 0.5
    p *= _coherence_multipliers(prob_coherence_flag)[1]
    return max(0.05, min(0.92, p))


def strength_score(
    house_margin: float,
    data_completeness: int,
    prob_coherence_flag: str,
) -> float:
    """Score 0..1 para rankear candidatos a premium y predictive_tier."""
    hm = max(0.0, min(0.3, float(house_margin)))
    hm_part = (1.0 - min(hm / 0.2, 1.0)) * 0.35
    c = max(0, min(100, int(data_completeness))) / 100.0
    comp_part = c * 0.4
    f = (prob_coherence_flag or "").strip().lower()
    if f == "coherence_ok":
        coh = 1.0
    elif f == "coherence_warning":
        coh = 0.78
    else:
        coh = 0.88
    coh_part = coh * 0.25
    return max(0.0, min(1.0, hm_part + comp_part + coh_part))


def assign_predictive_tier(ranks_sorted: list[tuple[str, float]]) -> dict[str, PredictiveTier]:
    """
    ranks_sorted: (event_id_str, score) ya ordenado desc.
    Terciles por posición.
    """
    n = len(ranks_sorted)
    if n == 0:
        return {}
    out: dict[str, PredictiveTier] = {}
    for i, (eid, _) in enumerate(ranks_sorted):
        frac = i / max(n - 1, 1)
        if frac <= 1 / 3:
            out[eid] = "high"
        elif frac <= 2 / 3:
            out[eid] = "medium"
        else:
            out[eid] = "low"
    return out


def assign_standard_premium_access(
    *,
    ordered_row_payloads: list[dict[str, Any]],
    tier_by_event: dict[int, str],
    hm_by_event: dict[int, float],
    score_by_event: dict[int, float],
) -> dict[int, AccessTierDB]:
    """
    premium = hasta 2 eventos Tier S con mayor strength_score y score >= MIN_PREMIUM_STRENGTH.
    Tier A → siempre standard. Tier S fuera del top threshold → standard (free track).
    No se fuerza premium débil.
    """
    premium_eids: set[int] = set()
    s_ranked: list[tuple[int, float]] = []
    for p in ordered_row_payloads:
        eid = int(p["event_id"])
        lt = (tier_by_event.get(eid) or "").upper()
        if lt != "S":
            continue
        sc = float(score_by_event.get(eid, 0.0))
        s_ranked.append((eid, sc))
    s_ranked.sort(key=lambda x: -x[1])
    for eid, sc in s_ranked:
        if len(premium_eids) >= MAX_PREMIUM_SLOTS:
            break
        if sc >= MIN_PREMIUM_STRENGTH:
            premium_eids.add(eid)
    access: dict[int, AccessTierDB] = {}
    for p in ordered_row_payloads:
        eid = int(p["event_id"])
        access[eid] = "premium" if eid in premium_eids else "standard"
    return access


def compute_row_signal_fields(
    *,
    agg: AggregatedOdds,
    data_completeness: int,
    market_canonical: str,
    selection_canonical: str,
) -> tuple[float, EvidenceQuality, str]:
    """prob_coherence_flag + campos derivados para persistir."""
    fl = prob_coherence_flag_for_agg(agg)
    p_hat = estimate_hit_probability(
        agg.consensus, market_canonical, selection_canonical, fl
    )
    ev = evidence_quality_from(data_completeness, fl)
    return p_hat, ev, fl
