# Handoff — Ejecución Backend / datos Sprint 06.4 (Fase 2 / F3)

> Orden sugerido, bloques y reglas duras para **no mezclar frentes**.  
> Backlog: [`TASKS.md`](./TASKS.md). US: [`US.md`](./US.md). Decisiones: [`DECISIONES.md`](./DECISIONES.md).  
> **Verdad madre del programa:** [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md).

---

## 0. Congelar política antes de cambiar comportamiento productivo

**Tareas:** **T-267**, **T-268**.

**Objetivo:** Acta **US-BE-058** con matriz *dato × frecuencia × capa × DSR sí/no* y delimitación explícita **F4/F5 fuera**.

**Regla dura:** Sin acta aceptada por PO/TL, **no** mergear lógica que cambie cupos o disparadores DSR en producción (**T-270** depende de esto).

**Checklist de salida §0:** [ ] acta en repo; [ ] enlaces desde `DECISIONES.md` / `PLAN.md`; [ ] D-06-062 a **D-06-068** revisadas.

---

## 1. Inventario y brecha (solo lectura + doc)

**Tareas:** **T-269**.

**Objetivo:** Mapa honesto de **dónde** se llama DSR hoy vs **dónde** solo corre CDM/SM.

**Entregable:** Sección **§ brecha** en este archivo o en anexo enlazado desde `TASKS.md` / `EJECUCION.md`.

---

## 1b. Medición intradía SM (insumo política; sin DSR prod)

**Tareas:** **T-280**, **T-287**, **T-281**, **T-282** (**US-BE-061**). **Normas:** **D-06-067**, **D-06-068**.

**Objetivo:** Ejecutar medición SM según **D-06-068** (universo, cadencia, disponible, familias) en **T-287** para evidencia hacia **US-BE-058**.

**Orden sugerido:** T-280 → **T-287** → T-281 → T-282.

**Runbook T-280 (universo, cadencia, TZ, normalización §6, esquema T-287):** [`../../runbooks/bt2_f3_sm_intraday_observation_d06_068.md`](../../runbooks/bt2_f3_sm_intraday_observation_d06_068.md).

**Paralelismo:** Puede ejecutarse **en paralelo** con §1 (T-269) si el diseño no escribe política DSR ni activa fallback; coordinar **rate limits** SM con cualquier otra ingesta del mismo entorno.

**Regla dura:** Persistencia **T-287**; **no** sustituye acta **US-BE-058**. Observabilidad, no producto alternativo de datos.

---

## 2. Implementación mínima desacoplada

**Tareas:** **T-270**, **T-271**.

**Objetivo:** Configuración o guardas que materialicen **D-06-064** (SM/CDM vs DSR).

**Reglas para no mezclar frentes:**

| Frente | Permitido en PRs F3 | Prohibido sin nuevo sprint / decisión |
|--------|---------------------|--------------------------------------|
| **F3** | Jobs de ingesta, throttling DSR, métricas de refresco, snapshot en función de política, **jobs de medición SM** (US-BE-061), **scripts benchmark** SM vs SofaScore (US-BE-062) | — |
| **F4** | — | Post-DSR por mix de mercados, nueva lógica de “variedad” en slate; usar resultado del benchmark para **cambiar** mix de señal sin acta aparte |
| **F5** | — | DP, preview, límites visibles usuario |
| **F2 / S6.3** | Lectura de elegibilidad/mercados **solo** como input pasivo | Cambiar umbrales, acta T-244, reglas de evaluación oficial |

**Entregable:** PR(s) en `EJECUCION.md` con evidencia en **tablas/queries** donde aplique (F3 medición), no solo logs.

---

## 3. Operación y evidencia

**Tareas:** **T-272**, **T-273**, **T-274**, **T-275**.

**Objetivo:** Runbook + una corrida de validación que demuestre los dos modos (CDM solo vs DSR autorizado).

**Orden sugerido:** T-272 → T-273 → T-274 → T-275.

---

## 4. Benchmark SM vs SofaScore (solo discovery)

**Tareas:** **T-283**, **T-288**, **T-284**, **T-285**, **T-286** (**US-BE-062**). **Normas:** **D-06-066**, **D-06-068** §6.

**Objetivo:** Benchmark SofaScore vs **T-287**, mismo universo y cadencia **D-06-068**, matching **§6**.

**Orden sugerido:** T-283 → **T-288** → T-284 → T-285 → **T-286**.

**Reglas duras:**

- **SofaScore = solo benchmark/discovery** (**D-06-066**); sin fallback productivo (**T-286**). Tablas **T-287** / **T-288** fuera de rutas productivas.
- Lado **SM** del comparativo: leer **T-287** (US-BE-061). Lado **SofaScore:** solo **T-288**; **T-284** no re-poll SM.

---

## 5. Cierre

**Tareas:** **T-278**, **T-279**.

Actualizar este handoff con **desviaciones** respecto al orden ideal y deuda **solo** si sigue siendo F3.

---

## § brecha (rellenar en T-269)

| Área | Ubicación aproximada | Hoy dispara DSR | Notas |
|------|----------------------|-----------------|-------|
| *(pendiente)* | | | |

---

*2026-04-15 — handoff S6.4; medición §4 única (061+062); **D-06-065**.*
