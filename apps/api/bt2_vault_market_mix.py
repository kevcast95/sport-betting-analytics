"""
D-06-031 (UX) — mezcla de mercados en la cartelera visible del slate.

Tras resolver DSR/fallback por evento, reordena las filas persistidas (`slate_rank`)
para que las primeras posiciones (típ. 5 visibles) favorezcan **familias de mercado
distintas** cuando los datos ya trajeron picks en varios tipos.

No sustituye análisis estadístico ni garantiza edge: solo reduce la sensación de
“siempre 1X2” cuando el pool ya contiene O/U, BTTS, doble oportunidad, etc.
"""

from __future__ import annotations


def market_diversity_family(model_market_canonical: str) -> str:
    """
    Agrupa mercados canónicos en familias para contar variedad en el slate.
    """
    u = (model_market_canonical or "").strip().upper()
    if u == "FT_1X2" or u == "UNKNOWN":
        return u or "UNKNOWN"
    if u.startswith("OU_GOALS"):
        return "OU_GOALS"
    if u == "BTTS" or u.startswith("BTTS"):
        return "BTTS"
    if "DOUBLE_CHANCE" in u:
        return "DOUBLE_CHANCE"
    if "CORNER" in u:
        return "OU_CORNERS"
    if "CARD" in u:
        return "OU_CARDS"
    return u or "OTHER"


def order_indices_for_top_slate_diversity(
    model_market_canonicals: list[str],
    *,
    top_k: int,
) -> list[int]:
    """
    Devuelve una permutación de ``range(n)``: las primeras ``min(top_k, n)`` posiciones
    eligen greedy eventos cuya familia de mercado aún no apareció, rompiendo empates
    por índice ascendente (orden de calidad previo del pool).
    El resto conserva el orden original relativo.
    """
    n = len(model_market_canonicals)
    if n <= 1:
        return list(range(n))
    families = [market_diversity_family(m) for m in model_market_canonicals]
    used: set[str] = set()
    rem: set[int] = set(range(n))
    out: list[int] = []
    k = min(max(0, top_k), n)
    for _ in range(k):
        j = max(
            rem,
            key=lambda idx: (
                0 if families[idx] in used else 1,
                -idx,
            ),
        )
        rem.remove(j)
        out.append(j)
        used.add(families[j])
    out.extend(sorted(rem))
    return out
