# Sprint 06.5 — Validate SFS

**Fuente de verdad de definición:** [`cursor_prompt_s6_5_validate_sfs.md`](./cursor_prompt_s6_5_validate_sfs.md) — cualquier desvío respecto a ese archivo es defecto de documentación hasta enmienda explícita allí.

**Programa (contexto, no redefine este sprint):** [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md).

---

## 1. Objetivo real

Responder con evidencia en Postgres BT2 (staging/experimental) si:

1. SofaScore sirve como **fuente experimental** de odds/markets para BT2.
2. BT2 puede operar **al menos una semana experimental adicional** con SFS y observar resultados reales sobre mercados, con coste/cupos **operables**.
3. Existe una **capa canónica agnóstica a proveedor** suficiente para integrar **The Odds API** después **sin rehacer el core** (solo adapter).
4. El problema dominante pasa a quedar acotado como **fuente + modelado canónico + cobertura real**, y deja de asumirse como único eje el **refresh complejo por completitud tardía** cerca del kickoff.

---

## 2. Por qué cambió la percepción del problema

- SportMonks **no garantiza** por sí solo toda la riqueza de markets aun con add-on.
- SofaScore **parece** más rico en varios casos.
- El legacy V1 pudo **subcapturar** riqueza por processors/persistencia; eso **no** convierte a V1 en dependencia del experimento (ver **DECISIONES** y prompt §Contexto).

---

## 3. Alcance / fuera de alcance

| Dentro | Fuera |
|--------|--------|
| Provider propio BT2-SFS (`apps/api/bt2/providers/sofascore/` o equivalente acordado con TL) | Fallback productivo SM→SFS |
| Endpoints obligatorios SFS: `odds/1/featured`, `odds/1/all` únicamente | Otros endpoints SFS como obligatorios de cierre |
| Cohorte base **BT2/Postgres** gobernada por SM/CDM | V1/SQLite como runtime o truth source |
| Ventana híbrida **6 días UTC cerrados + día actual UTC** (ver §4) | UI/FE, `US-FE-*`, vistas admin nuevas |
| Persistencia experimental + shadow `ds_input` | Cambio del truth source oficial productivo del acta T-244 |
| `GO` / `PIVOT` / `NO-GO` con umbrales cerrados | Cierre de F3 por decreto; solo **tres salidas posibles** documentadas para replan F3 |

---

## 4. Ventana y dos modos de trabajo

**Ventana:** **6 días UTC completos hacia atrás** desde el ancla de corrida, **más** el **día actual UTC**. Para el día actual: solo **job temporal controlado en staging**, con corte a las **00:00 UTC** del día siguiente.

**Modo A — Historical bootstrap 6d:** reconstruir y comparar los 6 días cerrados; V1 solo **seed auxiliar** de IDs si existen.

**Modo B — Daily experimental path:** cohorte SM del día en staging → equivalencia SFS → odds → persistir y comparar hasta cierre UTC definido.

---

## 5. Criterio de cierre del sprint

- Corridas documentadas (histórica + daily) en [`EJECUCION.md`](./EJECUCION.md) con `run_id`.
- KPI principal y `% match` calculados según [`DECISIONES.md`](./DECISIONES.md).
- Shadow `ds_input` con metadata obligatoria y **1** fixture E2E + **mini cohorte 20** eventos comparables.
- **Acta final** `GO` / `PIVOT` / `NO-GO` según reglas duras del prompt y **DECISIONES**.
- Frase de arquitectura Odds API en **DECISIONES** (seam listo, falta adapter).

---

## 6. Artefactos del sprint

| Archivo | Rol |
|---------|-----|
| [`cursor_prompt_s6_5_validate_sfs.md`](./cursor_prompt_s6_5_validate_sfs.md) | Definición madre |
| [`DECISIONES.md`](./DECISIONES.md) | Norma D-06-062+ |
| [`US.md`](./US.md) | Backlog por historia |
| [`TASKS.md`](./TASKS.md) | T-267+ ejecutables |
| [`EJECUCION.md`](./EJECUCION.md) | Parámetros cerrados, corridas, acta |

---

*Documento derivado exclusivamente del prompt maestro del sprint.*
