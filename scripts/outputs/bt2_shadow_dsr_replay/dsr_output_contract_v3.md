# DSR Output Contract v3 (shadow_dsr_replay)

## Objetivo

Reducir fragilidad operativa de salida para `deepseek-v4-pro` minimizando el JSON a los campos estrictamente necesarios para BT2.

## Estructura obligatoria

El modelo debe devolver **solo** un objeto JSON con:

```json
{
  "picks_by_event": [
    {
      "event_id": 123,
      "market_canonical": "FT_1X2" | "UNKNOWN",
      "selection_canonical": "home" | "draw" | "away" | "unknown_side",
      "selected_team": "...",
      "no_pick_reason": ""
    }
  ]
}
```

## Reglas duras

- Exactamente 1 objeto por cada `event_id` en `ds_input`.
- Sin texto fuera del JSON.
- Sin markdown ni prose.
- Mercado permitido: `FT_1X2` (o `UNKNOWN` si no hay pick).
- Si no hay pick: `market_canonical=UNKNOWN`, `selection_canonical=unknown_side`, `no_pick_reason` no vacío.
- Sin inventar picks.
- Sin fallback de selección.

## Normalización mínima aceptada (parser)

- `market_canonical` | `market` | `marketCode`
- `selection_canonical` | `selection` | `side` | `pick`
- `selected_team` | `team`
- `no_pick_reason` | `motivo_sin_pick` | `no_pick`

Sin parseo mágico de texto libre.
