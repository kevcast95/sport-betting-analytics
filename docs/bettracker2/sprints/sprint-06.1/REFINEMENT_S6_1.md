# Sprint 6.1 — Refinement (fuente de verdad)

**Estado:** referencia para alinear DECISIONES, US, TASKS y cambios de prompt/builder.  
**Relación con `feedback.md`:** ese archivo conserva el hilo BA↔PO (preguntas, respuestas en bruto y contexto). **Este documento** sintetiza y fija lo acordado en lenguaje de producto e ingeniería.

**Referencias externas:** contrato e insumos en [`DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) (especialmente §4 `ds_input`, §8 BT2 mínimo).

---

## 1. Posicionamiento: BT2 respecto a v1

- **Rigor de pipeline:** BT2 debe mantener el **mismo orden y severidad de pasos** que v1 (candidatos → `ds_input` → modelo → salida estructurada → post-proceso servidor).
- **Calidad del insumo:** `ds_input` debe ser **óptimo y estrictamente superior a v1 en riqueza útil**, no solo “distinto”. La ventaja de BT2 es **datos certificados** (API/CDM + base propia), no reemplazar calidad narrativa por una cuota más limpia.
- **Promesa de producto:** BT2 es una **versión mejorada** de v1, no su sombra. Si el modelo recibe menos contexto decisorio que en v1, la promesa se rompe aunque el JSON de salida se parezca.

---

## 2. Criterio de elección de mercado (producto)

- Entre los **mercados disponibles** para el partido (p. ej. 1X2, BTTS, over/under), el modelo debe orientarse a la opción que, **según estadística histórica y parámetros presentes en el input** (contrato `ds_input` en `DSR_V1_FLUJO.md`), tenga **la mejor lectura de probabilidad de acierto coherente con la cuota** — no a “el mercado que más dinero pueda dar” como regla suelta.
- **Ejemplo ilustrativo:** si el 1X2 marca claramente un favorito por implícitas, pero el input (p. ej. alineaciones, bajas) **desaconseja** esa lectura, la sugerencia puede apoyar otra selección **fundada en esos datos** (como en v1: favorito con bajas importantes → lectura hacia el rival/local según contexto).
- **No es una regla de underdog:** el objetivo no es “elegir la cuota más alta del 1X2”, sino **validar con datos** si la línea del mercado tiene sentido; si los datos no alcanzan para el 1X2, el análisis puede considerar otros mercados (p. ej. O/U) apoyándose en **historial de equipos** disponible en base de datos.

---

## 3. Coherencia de salida (obligatoria)

- **Selección vs. razonamiento:** la opción mostrada (`selection` / mercado efectivo) debe ser **consistente** con el texto de `razon`. Una contradicción (p. ej. victoria local en la ficha y empate en el razonamiento) degrada la confianza del usuario; es **fallo de calidad** a corregir vía modelo + **Post-DSR** (reglas servidor), no confundirlo con “eligió underdog”.
- **Referencia de calidad v1:** en v1, el pick puede mostrar mercado, código en boletín, cuota, confianza, edge y un **“por qué” alineado** con el historial directo u otros datos — ese estándar narrativo sigue siendo la referencia para BT2.

---

## 4. Diagnóstico de síntomas (causas probables)

| Síntoma | Causa más plausible |
|--------|----------------------|
| Pick 1X2 con menor probabilidad implícita que otra línea | No es error automático si el producto busca lectura fundada en datos; hoy el **prompt BT2** habla de “valor/datos”, que no coincide del todo con la premisa del §2 hasta alinearlo. |
| `razon` contradice `selection` | Salida inconsistente del LLM; falta o insuficiencia de **Post-DSR** que degrade u omita. |
| Justificación genérica o “floja” | **`ds_input` aún menos rico que v1** en bloques decisorios → el modelo rellena sin anclaje; atacar con **builder + datos** y reglas. |
| Cuota en UI distinta a captura de una casa | Posible **fuente distinta** (p. ej. consensus agregado vs. una book); comparar la misma línea que consume el modelo. |

---

## 5. Requisito de datos: histórico y cuotas en DB

**Requisito PO (cerrado en intención):** al construir candidatos y el **`ds_input`**, la aplicación debe **consultar en la base propia** todo lo **histórico** relevante para el duelo (equipos, enfrentamientos, forma, etc.) y, **si existen**, **cuotas históricas** u otras series almacenadas. Objetivo: **no subutilizar** datos ya pagados y persistidos.

---

## 6. Validación técnica — construcción actual de `ds_input`

### 6.1 v1 (`jobs/select_candidates.py`)

Por cada evento seleccionado, cada ítem de `ds_input[]` se arma desde **`event_features.features_json`**:

| Bloque | Contenido |
|--------|-----------|
| `event_context` | Completo (torneo, equipos, horario, estado, etc.). |
| `processed` | Dict completo: `lineups`, `h2h`, `statistics`, `team_streaks`, `team_season_stats`, `odds_all`, `odds_featured`, etc. |
| `diagnostics` | Flags reales del scrape (`*_ok`, `fetch_errors`). |
| `selection_tier` | Tier A/B según calidad de datos. |

*(Referencia aproximada: líneas 549–563 de `select_candidates.py`.)*

### 6.2 BT2 hoy (`apps/api/bt2_dsr_ds_input_builder.py`, usado desde `bt2_router._generate_daily_picks_snapshot`)

| Bloque | Comportamiento actual |
|--------|------------------------|
| Evento | `bt2_events`, `bt2_leagues`, equipos. |
| Cuotas | `bt2_odds_snapshot` → `consensus` (y opcionalmente por casa). |
| `processed.odds_featured` | Poblado. |
| `processed.lineups`, `h2h`, `statistics`, `team_streaks`, `team_season_stats` | **Placeholders:** `available: false` (p. ej. líneas 75–79 del builder). |
| `diagnostics` | Incluye cobertura de mercado; flags `*_ok: false` para bloques anteriores. |

**Conclusión:** la fuente CDM/API puede ser más fiable que el scraper v1, pero **el builder BT2 aún no vuelca** H2H, estadísticas, alineaciones ni series al JSON que ve el modelo. El gap es **implementación y alcance del builder**, no “los datos no existen” en abstracto.

### 6.3 Alineación prompt ↔ producto

- En `apps/api/bt2_dsr_deepseek.py`, el system prompt actual pide **“mejor relación valor/datos”**, interpretable como **edge / valor esperado** en jerga de apuestas.
- La premisa de producto del §2 prioriza **lectura con mayor soporte en datos e histórico** (y coherencia cuota–narrativa), **no** maximizar payout como eje único.
- **Acción:** unificar criterio en **DECISIONES + texto de prompt** tras usar este doc como referencia.

### 6.4 Dependencia de datos para el caso “favorito con bajas”

Reproducir el comportamiento deseado (lineups/bajas que mueven la lectura frente al favorito) **exige** que `ds_input` lleve **lineups / estado de plantel (o equivalente)** con `available: true` y contenido útil. Solo ajustar el prompt **sin** enriquecer el builder **no** alcanza.

---

## 7. Backlog derivado (cerrado en repo)

Las premisas de §2–§6 están bajadas a:

- **DECISIONES.md** — sección **REFINEMENT_S6_1:** **D-06-027** … **D-06-030**.
- **US.md** — sección **REFINEMENT_S6_1:** **US-BE-037** … **US-BE-039**, **US-FE-056**.
- **TASKS.md** — sección **REFINEMENT_S6_1:** **T-189** … **T-194**.
- **PLAN.md**, **HANDOFF_EJECUCION_S6_1.md**, **EJECUCION.md** — misma sección para orden de ejecución y evidencia.

Cualquier cambio de alcance posterior sigue **D-06-023** (US / DECISIÓN antes de merge).
