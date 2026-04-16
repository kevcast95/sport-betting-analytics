# Sprint 06.4 — Plan

**Estado:** arranque documental — alcance **Fase 2 del programa** (frente **F3** en el roadmap PO): frescura defendible sin disparar coste.

**Rama Git de trabajo:** `sprint-06.4` (desde `main` actualizado).

**Cierre / contexto del sprint anterior:** documentación y entregas de **S6.3** permanecen **cerradas**; este sprint **no** reabre decisiones ni tareas de S6.3. Referencia histórica: [`../sprint-06.3/PLAN.md`](../sprint-06.3/PLAN.md).

**Verdad madre del programa (norte, fases, frentes F1–F6):** [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md) — ver también [`DECISIONES.md`](./DECISIONES.md) **D-06-062**.

**Artefactos base de S6.4:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md), [`HANDOFF_BE_EJECUCION_S6_4.md`](./HANDOFF_BE_EJECUCION_S6_4.md), [`EJECUCION.md`](./EJECUCION.md).

**Contrato de US:** [`../../01_CONTRATO_US.md`](../../01_CONTRATO_US.md).

---

## 1. Objetivo

Definir e implementar (en la medida acordada en kickoff) una **política operativa de frescura** que separe claramente:

- **Ingesta CDM / SportMonks** (alta frecuencia posible, coste mayormente de API SM y jobs), y  
- **Invocaciones al DSR** (coste LLM + orquestación),

de modo que el sistema mejore **datos cercanos al partido** (p. ej. lineups, O/U disponibles en fuente) **sin** multiplicar llamadas DSR innecesarias, y deje **trazabilidad** para defender coste y cadencia ante operación y producto.

---

## 2. Alcance (dentro de S6.4)

| Bloque | Qué se espera |
|--------|----------------|
| **Política escrita** | Acta o documento normativo en repo: qué entidades refresca la ingesta SM/CDM, con qué frecuencia por tipo de dato o ventana temporal, qué permanece persistido solo en CDM/SM vs qué alimenta snapshot / `ds_input`. |
| **Reglas DSR** | Criterio explícito: **cuándo** conviene re-ejecutar DSR o regenerar insumo costoso vs **cuándo** basta refrescar CDM y lecturas posteriores sin nuevo DSR. |
| **Coste y operación** | Presupuesto o límites defendibles (por día, por evento, por usuario si aplica), métricas mínimas y runbooks; criterios de alerta o revisión manual. |
| **Medición / discovery (prioritario)** | **US-BE-061** + **US-BE-062**; parámetros de ejecución congelados en [`DECISIONES.md`](./DECISIONES.md) **D-06-068**; tablas **T-287** / **T-288**. Ver **US-BE-060** en [`US.md`](./US.md). |

---

## 3. Fuera de alcance (explícito)

- **F4 / F5:** variedad y mix de mercados en la señal, Post-DSR, conducta usuario (DP, preview, premium), franjas de visualización — **sin** backlog de implementación aquí.
- **Reapertura F2 o S6.3:** umbrales de elegibilidad F2, acta T-244, jobs de evaluación oficial salvo **dependencia técnica** puntual ya existente (solo integración, no rediseño normativo).
- **Nuevo modelo** o rediseño profundo de prompts DSR como objetivo principal del sprint.
- **Fallback productivo** a SofaScore o sustitución de SM como verdad BT2/CDM.

---

## 4. Dependencias

- **Técnicas:** pipelines CDM existentes (`scripts/bt2_cdm/`, workers SM), tablas `raw_*` / `bt2_*`, construcción de snapshot / `ds_input` tal como estén en `main` al inicio de S6.4.
- **Normativas:** decisiones y cierre Fase 1 / F2 documentados en S6.3 **se respetan**; S6.4 añade capa **D** (snapshot / tiempo) sin contradecir F1/F2.

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Confundir “más ingesta SM” con “más picks / más DSR” | Documentar y codificar separación; métricas distintas por canal (SM vs DSR). |
| Política demasiado vaga para implementar | Entregable mínimo: tabla **evento × tipo de refresh × frecuencia × disparador DSR sí/no** en acta o anexo enlazado desde `DECISIONES.md`. |
| Coste SM sube sin control | Cupos, ventanas, includes mínimos acordados; revisión en `EJECUCION.md` con números. |
| Scope creep hacia F4 | Checklist de cierre del sprint y revisión de PR contra `PLAN.md` §3. |

---

## 6. Criterio de cierre del sprint

1. Existe **política aprobada** (PO/TL) reflejada en `DECISIONES.md` y referenciada en `TASKS.md` / código o runbooks según corresponda.  
2. Queda **evidencia** en [`EJECUCION.md`](./EJECUCION.md): corridas, métricas de frescura/coste, y — si aplica — evidencia de **US-BE-061 / US-BE-062** (tablas **T-287** / **T-288** + queries).  
3. `HANDOFF_BE_EJECUCION_S6_4.md` describe el orden real seguido y cualquier diferencia respecto al plan inicial.  
4. Ningún entregable obligatorio mezcla **F3** con **F4/F5** ni reabre **F2/S6.3** sin decisión explícita fuera de este alcance.

---

*2026-04-15 — creado: base documental sprint 06.4 (Fase 2 / F3).*
