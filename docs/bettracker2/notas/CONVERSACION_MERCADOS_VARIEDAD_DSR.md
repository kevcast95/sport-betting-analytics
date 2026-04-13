# Conversación — Variedad de mercados, calidad y reglas de desempate

**Fecha de registro:** 2026-04-09  
**Contexto:** picks de bóveda mayormente 1X2; percepción de pobreza; diferencia entre sesgo del modelo y “mejor mercado” real.

## Objetivo de producto

- Alto nivel de análisis y valor estadístico defendible.
- Evitar que el usuario sienta: “el modelo siempre me dice 1X2, así que chiste”.
- **Variedad de muestra** y **calidad** no son lo mismo: la primera mejora percepción y exploración; la segunda exige calibración, histórico por tipo de mercado y reglas medibles (edge, cobertura, etc.).

## Qué quedó implementado (código existente)

1. **`bt2_vault_market_mix` + `order_indices_for_top_slate_diversity`**  
   Tras DSR/fallback, se reordena el `slate_rank` para que el **top visible** mezcle **familias** de mercado (1X2, O/U goles, BTTS, doble oportunidad, …) **solo entre filas que ya traen** ese `model_market_canonical`. No se inventan mercados.

2. **Prompt DSR (`bt2_dsr_deepseek.py`)**  
   Instrucción de no quedarse en 1X2 por costumbre cuando otros mercados del `consensus` tienen soporte similar; esquema de ejemplo con O/U y BTTS antes que 1X2 para bajar anclaje.

3. **Tests**  
   `bt2_vault_market_mix_test.py`.

**Límite:** si el modelo/fallback devuelve solo `FT_1X2` en todos los eventos, la mezcla **no puede** mostrar variedad de mercado en pantalla.

## Ideas acordadas (diseño / siguiente iteración)

### Evaluar otros mercados en el mismo evento

Para cada partido, considerar mercados que **existen y están cubiertos** en el input (`consensus` + bloques `processed` útiles). Si 1X2 no cumple criterios, **pasar** a O/U, BTTS, doble oportunidad, etc., **solo** si hay datos y cuotas válidas en **ese** evento. No es menú fijo por slot global.

### Desempate por diversidad cuando el soporte es similar

Si **dos mercados** tienen soporte **igual o similar** y el slate **ya acumula muchos 1X2**, regla posible: **preferir el no-1X2** como desempate, **siempre** que el otro mercado siga siendo elegible (validación + post-proceso).

- Definir operativamente “similar soporte” y “muchos 1X2” (porcentaje del pool, tope en top K, etc.).
- Aplicar preferentemente al **top visible** o subconjunto acotado para no distorsionar todo el día si el valor real es casi todo 1X2.

### Forzar variedad vs mercados prefijados

- **Forzar** cuotas por familia sin soporte **sí** mezcla mercados pero **puede** sacrificar calidad.
- **Mercados prefijados** por posición = producto editorial predecible; **no** equivale a “el modelo eligió lo mejor”, sustituye libertad por reglas de negocio.

### Punto intermedio recomendado

Reglas **condicionadas**: solo admitir salidas no-1X2 si el `consensus` y `processed` dan **soporte explícito** y superan umbrales; evita forzar mercados vacíos y reduce coste vs cuotas rígidas por familia.

---

*Documento de continuidad para backlog / US futuras; no sustituye DECISIONES de sprint.*
