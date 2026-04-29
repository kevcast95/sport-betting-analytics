# DSR Abstention Policy v5 (final microiteration)

## Objetivo

Reducir abstención excesiva de `deepseek-v4-pro` manteniendo robustez operativa y sin fallback.

## Política explícita

- Mercado del experimento: `FT_1X2`.
- Si `FT_1X2` está disponible, la acción por defecto es **emitir pick** (`home|draw|away`).
- `UNKNOWN/unknown_side` solo se permite en **abstención legítima**.

## Definiciones obligatorias

### Abstención legítima

Se permite `UNKNOWN` solo cuando el propio lote muestra una de estas condiciones:

- cobertura/consistencia de mercado insuficiente para sostener preferencia razonable;
- contradicción severa entre señales del lote que impide dirección defendible;
- datos críticos ausentes de forma que invalida una preferencia mínima.

En esos casos, `no_pick_reason` debe ser concreto y verificable contra el lote.

### Abstención excesiva

No se permite `UNKNOWN` por:

- duda normal;
- señal imperfecta pero direccional;
- ausencia de edge alto/perfecto.

Si no hay causal dura de abstención legítima, el modelo debe elegir `home`, `draw` o `away`.

## Guardrails

- Sin inventar edge ni datos externos.
- Sin parser mágico.
- Sin fallback de selección.
- JSON estricto y mínimo por evento.
