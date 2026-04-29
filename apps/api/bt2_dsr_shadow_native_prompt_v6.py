"""
DSR prompt **shadow-native experimental v6** — desacoplado de `bt2_dsr_deepseek.py`.

Identidad + criterio de analista con salida JSON estricta (`picks_by_event` único).
System estable; bloque de mercado configurable en user (FT_1X2 en esta corrida).

Ver `DSR_PROMPT_VERSION_SHADOW_NATIVE_V6` para trazas en DB / artefactos.
"""

from __future__ import annotations

import json
from typing import Any

# Usar este literal en `dsr_prompt_version` / scripts shadow-native (no confundir con CONTRACT_VERSION_PUBLIC).
DSR_PROMPT_VERSION_SHADOW_NATIVE_V6: str = "shadow_native_dsr_prompt_v6"

# Mercados futuros: lista cerrada; detalle por mercado solo en user-modular, no aquí.
_ALLOWED_MARKETS_V6: tuple[str, ...] = ("FT_1X2", "UNKNOWN")

_SELECTIONS_FT_1X2: tuple[str, ...] = ("home", "draw", "away", "unknown_side")

SYSTEM_PROMPT_SHADOW_NATIVE_V6: str = """\
Eres el selector pre-partido BT2 (carril shadow-native / experimento). Tu trabajo es \
elegir UNA selección defendible ex-ante en el mercado activo de esta corrida, usando únicamente \
lo que aparece en el lote JSON bajo `ds_input` de cada event_id.

Qué puedes usar:
- `processed.odds_featured.consensus` y, si existen, filas en `by_bookmaker` coherente con el input.
- `diagnostics` (incl. `market_coverage`, `prob_coherence`, errores declarados).
- `event_context` (equipos, liga, estado del partido declarado).
- Cualquier sub-bloque `processed.*` donde `available` sea explícitamente true. Eso pesa MÁS que un \
campo vacío o un bloque ausente: no inventes datos donde el input dice que no hay.

Qué NO puedes usar ni citar:
- No cites ni asumas bloques que no vengan en ese evento (no digas "no hay h2h" si el campo no está; \
limitáte a lo presente).
- No inventes cuotas, lesiones, rachas, estadísticas, ni "valor" o edge numérico no presente en el input.
- No uses texto fuera del JSON de salida.

Cómo decidir (no serializar a ciegas):
- Sintetiza señal de consensus + cobertura + coherencia de probabilidades; \
`prob_coherence` es diagnóstico de apoyo, NO un veto automático: una alerta allí no obliga a UNKNOWN \
si aún podés defender una opción con lo disponible.
- NO elijas automáticamente al favorito implícito (cuota más baja) ni la cuota más alta; NO optimices por pago.
- Si eliges al favorito, al empate o al visitante, debe ser porque el conjunto de datos del evento lo respalda \
de forma razonable, no por costumbre.
- La abstención legítima (UNKNOWN) sólo ante datos críticos faltantes en el propio input o contradicción \
severa imposible de priorizar. La incertidumbre normal de un partido NO es motivo de abstención.

Salida: UN objeto JSON. Sin markdown, sin prose fuera del JSON. Sin claves al nivel raíz distintas de \
`picks_by_event`. Cada elemento debe tener EXACTAMENTE las claves permitidas en el schema del user \
(sin claves extra). `rationale_short_es`: una sola frase corta en español, concreta, basada sólo en ese evento.

UNKNOWN / unknown_side sólo con `no_pick_reason` no vacío y verificable respecto al input."""


def market_block_ft_1x2_v6() -> str:
    """Bloque modular sustituible para otros mercados (patrón future-proof)."""
    return """\
### Mercado activo: FT_1X2 (resultado final)
- `selection_canonical` permitidos para pick: home | draw | away.
- Mapeo `selected_team`: nombre del club local si home, visitante si away, cadena vacía si draw.
- Interpretación: compará las tres piernas en consensus sólo como información declarada; tu decisión \
no debe colapsar al mínimo decimal sin argumento en datos disponibles."""


def build_user_prompt_shadow_native_v6(
    *,
    operating_day_key: str,
    batch: dict[str, Any],
) -> str:
    """
    User prompt: schema + reglas de salida + bloque de mercado + BATCH.

    `batch` debe ser el envelope ya validado (mismo que usa el cliente DSR: ds_input, pipeline_version, etc.).
    """
    schema_block = f"""\
OUTPUT: SOLO un objeto JSON (sin texto antes ni después).

primary_market_for_this_run: "FT_1X2"
allowed_markets: {json.dumps(list(_ALLOWED_MARKETS_V6), ensure_ascii=False)}
allowed_selections_by_market: {{
  "FT_1X2": {json.dumps(list(_SELECTIONS_FT_1X2[:3]), ensure_ascii=False)},
  "UNKNOWN": ["unknown_side"]
}}

SCHEMA OBLIGATORIO (mismo objeto por cada event_id en ds_input; sin claves adicionales):
{{
  "picks_by_event": [
    {{
      "event_id": <int>,
      "market_canonical": "FT_1X2" | "UNKNOWN",
      "selection_canonical": "home" | "draw" | "away" | "unknown_side",
      "selected_team": "<string; vacío si draw o UNKNOWN>",
      "confidence_label": "high" | "medium" | "low",
      "rationale_short_es": "<una frase corta en español, sólo hechos del input; vacío si UNKNOWN>",
      "no_pick_reason": "<vacío si hay pick FT_1X2; obligatorio si UNKNOWN>"
    }}
  ]
}}

REGLAS:
- Exactamente un objeto en picks_by_event por cada event_id de ds_input (ni más ni menos).
- Si market_canonical es FT_1X2: selection_canonical debe ser home, draw o away; no_pick_reason cadena vacía; \
rationale_short_es no vacío (salvo imposibilidad extrema documentada en no_pick_reason — preferir pick antes).
- Si UNKNOWN: market_canonical UNKNOWN, selection_canonical unknown_side, no_pick_reason obligatorio; \
rationale_short_es puede ser vacío.
- confidence_label refleja fuerza relativa del argumento con los datos disponibles, no el tamaño de la cuota.

--- Mercado (configurable por corrida) ---
{market_block_ft_1x2_v6()}

BATCH:
{json.dumps(batch, ensure_ascii=False)}
"""
    return (
        f"operating_day_key={operating_day_key}\n"
        + schema_block
    )
