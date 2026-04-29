# DSR Output Contract v2 (shadow_dsr_replay)

## Objetivo

Contrato mínimo, estricto y canónico para `deepseek-v4-pro` en `dsr_api_only`, sin fallback de selección y sin parseo permisivo.

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
      "confidence_label": "low" | "medium" | "high",
      "rationale_short_es": "...",
      "no_pick_reason": ""
    }
  ]
}
```

## Reglas duras

- Exactamente un registro por cada `event_id` de `ds_input`.
- Sin texto fuera del JSON.
- Sin markdown ni prose adicional.
- Mercado objetivo del experimento: `FT_1X2`.
- Si no hay pick, usar `market_canonical=UNKNOWN` y `selection_canonical=unknown_side` con `no_pick_reason`.
- No inventar picks ni completar con fallback local.
- No usar estructura anidada `picks[]`; cada evento debe traer campos canónicos en el objeto raíz del evento.

## Normalización mínima aceptada (parser)

El parser acepta aliases razonables y los normaliza:

- `market_canonical` \| `market` \| `marketCode`
- `selection_canonical` \| `selection` \| `side` \| `pick`
- `confidence_label` \| `confianza` \| `confidence`
- `rationale_short_es` \| `razon` \| `reason`

Sin inventar selección cuando faltan campos canónicos.
Sin rescate de JSON desde texto libre o `reasoning_content`.
