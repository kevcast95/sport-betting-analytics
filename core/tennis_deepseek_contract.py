"""
Contrato de salida DeepSeek para picks de tenis (JSON único, OpenAI-compatible).

Mercados v1: priorizar ganador del partido (Match winner) anclado a `processed.tennis_odds`.
No usar mercados de fútbol (1X2 con empate, BTTS, etc.).
"""

from __future__ import annotations

# Mercados permitidos para el modelo (subset estable; ampliar con cuidado).
TENNIS_MARKETS_V1 = (
    "Match winner",
    "Winner",
    "First set winner",
    "Total games Over/Under",
)

TENNIS_SYSTEM_PROMPT = (
    "Eres un analista de apuestas de tenis (ATP/WTA). "
    "El texto legible en la salida (especialmente el campo `razon`) debe estar en español; "
    "los nombres de mercado en JSON pueden seguir el contrato en inglés (Match winner, etc.). "
    "Debes devolver SOLO JSON válido (sin markdown). "
    "No inventes cuotas: el campo `processed.tennis_odds` y `processed.odds_all` son la fuente; "
    "si falta una cuota para un mercado, no emitas pick para ese mercado o deja picks vacíos. "
    "En tenis no hay empate en ganador de partido: selection solo '1' (jugador local/home) o '2' (visitante/away). "
    "Usa `event_context` (superficie, ronda, filtros), `processed.tennis_odds`, "
    "`processed.tennis_rankings`, `processed.tennis_statistics` (stats del partido), "
    "`processed.tennis_team_statistics_seasons` (temporadas disponibles por jugador) y "
    "`processed.tennis_registry` (muestra de categorías y torneos priorizados por país) para la explicación."
)


def build_tennis_user_prompt_instructions(*, date_str: str) -> str:
    return (
        f"Fecha de referencia: {date_str}.\n"
        "Tarea: con el lote `batch` (campo ds_input), propón picks de TENIS por evento.\n\n"
        "Reglas de salida (JSON):\n"
        "- Devuelve SOLO un objeto con esta forma:\n"
        "{\n"
        '  "picks_by_event": [\n'
        "    {\n"
        '      "event_id": 123,\n'
        '      "picks": [\n'
        "        {\n"
        '          "market": "Match winner"|"First set winner"|"Total games Over/Under",\n'
        '          "selection": "1"|"2"  (1=home/local, 2=away; nunca "X"),\n'
        '          "odds": number,\n'
        '          "edge_pct": number,\n'
        '          "confianza": "Baja"|"Media"|"Media-Alta"|"Alta",\n'
        '          "razon": string\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        '- Para "Match winner" / "Winner": selection solo "1" o "2".\n'
        "- Máximo 2 picks por evento. Si no hay cuotas en los datos, picks=[].\n"
        "- EDGE: p_imp_pct = round(100/odds,2); elige p_real_pct (0-100); edge_pct = round(p_real_pct - p_imp_pct, 2).\n"
        "- Confianza: misma escala que fútbol (>=5 Alta, >=3 Media-Alta, >=1.5 Media, si no Baja).\n"
        "- `razon`: una sola frase en español, usando superficie/ronda/ranking si están en event_context o processed.tennis_rankings.\n\n"
        "Datos del lote (JSON):\n"
    )


def infer_sport_from_batch(batch: dict) -> str:
    sp = batch.get("sport")
    if isinstance(sp, str) and sp.strip():
        return sp.strip().lower()
    ds = batch.get("ds_input") or []
    if ds and isinstance(ds[0], dict):
        m = ds[0].get("sport")
        if isinstance(m, str) and m.strip():
            return m.strip().lower()
    return "football"
