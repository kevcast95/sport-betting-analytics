"""
US-BE-034 / T-181–T-182 — Post-DSR: reconciliar salida modelo vs input; pick canónico o None (omitir).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# D-06-024 — desvío cuota modelo vs input
_DEVIATION_PCT = 0.15
# D-06-024 — odds declaradas por modelo > 15 → cap confianza
_MODEL_ODDS_CONF_CAP = 15.0


def narrative_contradicts_ft_1x2(
    selection_canonical: str,
    narrative_es: str,
    *,
    home_team: str = "",
    away_team: str = "",
) -> bool:
    """
    D-06-029 — heurística conservadora: contradicción material entre selección 1X2 y texto (español).
    Solo FT_1X2; otros mercados no se evalúan aquí (evita regresiones T-181).
    """
    t = (narrative_es or "").lower()
    if len(t) < 8:
        return False

    # Framing “equipo X con cuota/valor…” al inicio del texto: si el pick es el otro lado, es
    # contradicción material (p. ej. pick local + “Visitante con cuota con buen valor…”).
    if selection_canonical == "home":
        if re.match(
            r"^\s*(el\s+)?visitante\s+con\s+(cuota|valor|buen\s+valor|buenos?\s+valor|mejores?\s+cuotas?|l[ií]nea)",
            t,
        ):
            return True
    elif selection_canonical == "away":
        if re.match(
            r"^\s*(el\s+)?local\s+con\s+(cuota|valor|buen\s+valor|buenos?\s+valor|mejores?\s+cuotas?|l[ií]nea)",
            t,
        ):
            return True

    def _draw_claimed() -> bool:
        if not re.search(
            r"\bempate\b|\bempatan\b|\ba\s+x\b|\ben\s+x\b|repart\w*\s+los\s+puntos",
            t,
        ):
            return False
        neg = (
            "no empate",
            "sin empate",
            "no habrá empate",
            "no habra empate",
            "evitar el empate",
            "no será empate",
            "no sera empate",
            "descarta el empate",
            "sin sorpresa de empate",
        )
        return not any(n in t for n in neg)

    away_win = bool(
        re.search(
            r"victoria\s+(para\s+)?(el\s+)?visitante|gana\s+(el\s+)?visitante|"
            r"triunfo\s+(del\s+)?visitante|se\s+impone\s+(el\s+)?visitante|"
            r"favorito\s+visitante\s+.*\b(gana|vence)\b",
            t,
        )
    )
    home_win = bool(
        re.search(
            r"victoria\s+(para\s+)?(el\s+)?local|gana\s+(el\s+)?local|"
            r"triunfo\s+(del\s+)?local|se\s+impone\s+(el\s+)?local|"
            r"favorito\s+local\s+.*\b(gana|vence)\b",
            t,
        )
    )

    if selection_canonical == "home":
        if away_win:
            return True
        if _draw_claimed():
            return True
        return False

    if selection_canonical == "away":
        if home_win:
            return True
        if _draw_claimed():
            return True
        return False

    if selection_canonical == "draw":
        if home_win or away_win:
            return True
        hn = (home_team or "").strip().lower()
        an = (away_team or "").strip().lower()
        if len(hn) >= 3 and hn in t and re.search(rf"{re.escape(hn)}.{{0,40}}\b(gana|vence|arrasa)\b", t):
            return True
        if len(an) >= 3 and an in t and re.search(rf"{re.escape(an)}.{{0,40}}\b(gana|vence|arrasa)\b", t):
            return True
        return False

    return False


def _input_odds(
    consensus: dict[str, dict[str, float]],
    market_canonical: str,
    selection_canonical: str,
) -> Optional[float]:
    sub = consensus.get(market_canonical) or {}
    v = sub.get(selection_canonical)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 1.0 else None


def _coverage_allows(
    market_coverage: dict[str, bool],
    market_canonical: str,
    selection_canonical: str,
) -> bool:
    if not market_coverage.get(market_canonical):
        return False
    return True


def postprocess_dsr_pick(
    *,
    narrative_es: str,
    confidence_label: str,
    market_canonical: str,
    selection_canonical: str,
    model_declared_odds: Optional[float],
    consensus: dict[str, dict[str, float]],
    market_coverage: dict[str, bool],
    event_id: int,
    home_team: str = "",
    away_team: str = "",
) -> Optional[Tuple[str, str, str, str]]:
    """
    Retorna tupla persistible (narr, conf, mmc, msc) o None si se omite el pick (D-06-026 §2).
    """
    if not market_canonical or market_canonical == "UNKNOWN":
        logger.info("bt2_post_dsr_omit reason=bad_market event_id=%s", event_id)
        return None
    if not selection_canonical or selection_canonical == "unknown_side":
        logger.info("bt2_post_dsr_omit reason=bad_selection event_id=%s", event_id)
        return None
    if not _coverage_allows(market_coverage, market_canonical, selection_canonical):
        logger.info(
            "bt2_post_dsr_omit reason=no_input_coverage event_id=%s mc=%s sc=%s",
            event_id,
            market_canonical,
            selection_canonical,
        )
        return None

    if market_canonical == "FT_1X2" and narrative_contradicts_ft_1x2(
        selection_canonical,
        narrative_es,
        home_team=home_team,
        away_team=away_team,
    ):
        logger.info(
            "bt2_post_dsr_omit reason=incoherent_razon event_id=%s mc=%s sc=%s",
            event_id,
            market_canonical,
            selection_canonical,
        )
        return None

    inp = _input_odds(consensus, market_canonical, selection_canonical)
    if inp is None:
        logger.info(
            "bt2_post_dsr_omit reason=no_input_odds event_id=%s mc=%s sc=%s",
            event_id,
            market_canonical,
            selection_canonical,
        )
        return None

    conf = (confidence_label or "low").strip().lower()
    if conf not in ("high", "medium", "low"):
        conf = "low"

    mod = model_declared_odds
    if mod is not None and mod > _MODEL_ODDS_CONF_CAP and conf == "high":
        conf = "medium"
        logger.info(
            "bt2_post_dsr_cap_conf event_id=%s model_odds=%s -> medium",
            event_id,
            mod,
        )

    if mod is not None and mod > 1.0 and inp > 0:
        dev = abs(mod - inp) / inp
        if dev > _DEVIATION_PCT:
            logger.info(
                "bt2_post_dsr_odds_mismatch event_id=%s input=%s model=%s dev=%.3f",
                event_id,
                inp,
                mod,
                dev,
            )

    narr = (narrative_es or "").strip() or "Señal modelo."
    return narr[:4000], conf, market_canonical, selection_canonical


def hash_for_ds_input_item(item: dict[str, Any]) -> str:
    from apps.api.bt2_dsr_contract import assert_no_forbidden_ds_keys, hash_dsr_input_payload

    assert_no_forbidden_ds_keys(item)
    return hash_dsr_input_payload(item)
