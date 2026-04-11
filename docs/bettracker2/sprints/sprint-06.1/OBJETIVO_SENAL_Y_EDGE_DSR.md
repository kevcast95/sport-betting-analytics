# Objetivo: señal DSR, edge medible y menos ruido (backlog Sprint 06.1)

> **Origen:** resumen para alinear PO/BA/BE con el alcance S6.1.  
> **Ejecución prevista:** **Sprint 06.1** — ver [`PLAN.md`](./PLAN.md).  
> **Trazabilidad S6:** **D-06-020** en [`../sprint-06/DECISIONES.md`](../sprint-06/DECISIONES.md).  
> **Recalibración:** **D-06-021** … **D-06-026** en [`DECISIONES.md`](./DECISIONES.md) (incl. **D-06-023:** definición completa en **US.md** / **TASKS.md** antes de ejecutar; **D-06-026:** criterios operativos de pool, post-DSR, KPI v0 y vacío duro).  
> **Refinement posterior:** [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md) + **D-06-027** … **D-06-030** (criterio de mercado DSR, enriquecimiento `ds_input` desde Postgres, coherencia salida, alineación prompt).

---

## 0. Línea base tras hallazgo (2026-04-09)

Las conversaciones previas con BE sobre S6.1 ( **menos picks, más etiquetas de confianza alta** , como en v1) **asumían** que BT2 alimentaba a DeepSeek con un **`ds_input` equivalente al de v1**. Eso **no es cierto** hoy: v1 envía `event_context` + `processed` + `diagnostics` (ver [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) §4); BT2 envía un **subconjunto mínimo** (nombres + cuotas) — §8 del mismo doc.

**Implicación:** pedir “más confianza alta como v1” **sin** enriquecer el insumo **o** sin reglas servidor que acoten la salida es **mezclar intención de producto con capacidad real** del pipeline actual. S6.1 debe **reconciliar** ambas cosas en [`DECISIONES.md`](./DECISIONES.md) **D-06-021** y en [`US.md`](./US.md).

**Meta PO “>80% picks alta calidad; premium aún más exigentes”:** se mantiene como **dirección**, pero solo es **operacional** cuando exista definición medible + instrumentación (admin/analytics); ver **D-06-021**.

---

## 1. Objetivo declarado

Priorizar **menos picks con mejor señal**, usando **métricas y reglas medibles** en backend y datos, **no solo** la narrativa o las etiquetas del modelo — y, en paralelo, **acercar el insumo DSR al contrato v1** desde CDM persistido (anti-fuga **D-06-002**).

---

## 2. Problema a evitar

Tratar **“Baja / Media / Alta”** (u homólogas) que devuelve el LLM como si fueran:

- **probabilidad de acierto**, o  
- **calidad del feed / ingesta SportMonks**.

Son cosas **distintas**: el modelo puede ser conservador o inconsistente; SportMonks puede estar bien ingestado y aun así el modelo etiquetar “Media”. El producto y analytics deben **no mezclar** esas semánticas en un solo KPI sin definición explícita.

**Reconciliación con v1:** en v1, la **confianza** del JSON también es **atribuible al modelo** sobre un **contexto rico**; por eso la etiqueta era **más interpretable** en producto. En BT2, la misma etiqueta sobre **solo cuotas** no hereda esa semántica — hasta que el insumo converja o el servidor **componga** una señal de calidad explícita (score / bandas).

---

## 3. Líneas de trabajo

### 3.0 Paridad de `ds_input` con v1 (nuevo eje, D-06-021)

Mapear campos v1 → fuentes BT2 (tablas CDM, agregados propios, flags de completitud). Entregar lista cerrada con PO (qué entra al LLM en prod vs qué queda solo para reglas/backtest).

### 3.1 Elegibilidad al pool (datos) — **D-06-024** / **D-06-025** / **D-06-026**

Criterios ratificados en **D-06-024** … **D-06-026**. **No** exigir 1X2 y O/U 2.5 a la vez como condición de entrada al pool (criterio descartado; ver **D-06-024** tabla pool).

- **Cuota mínima** **1.30** y **ligas prioritarias** del producto (**T-177**; lista en configuración operativa).
- **Sin par de mercados obligatorio fijo:** el universo es **lo que haya en CDM** normalizado (1X2, doble oportunidad, O/U goles/corners/tarjetas, BTTS, …); el modelo elige el mercado de **mayor valor relativo** entre los disponibles.
- Un evento entra al lote si tiene al menos **un** mercado canónico **completo** que cumpla la cuota mín (definición compartida pool/builder).

Objetivo: menos ruido **sin** corsé de mercado único; homogeneidad por **calidad de datos**, no por checklist fija.

### 3.2 Volumen (producto / ops)

**Cuota mínima** y filtros de liga: **D-06-024**. **Techo de lote** por tokens/coste: decisión **técnica** (runbook BE), no tope PO arbitrario (**D-06-025**).

### 3.3 Edge y umbrales en BE

Especificar si se desea **edge implícito** calculado en servidor (con las odds del input) y **cortes**:

- descartar candidato,  
- degradar a reglas, o  
- marcar **flag** para UI.

Eso acerca “calidad” a algo **auditable** y **repetible** en backtest.

### 3.4 Prompt DSR

Refinar el mensaje de **“menos picks, más edge”** **después** de 3.0–3.2: el prompt **no** sustituye reglas de negocio ni compensa un `ds_input` que contradiga la intención v1.

### 3.5 Semántica en producto

Si hace falta, **separar conceptos** en requisitos explícitos:

| Concepto | Idea |
|----------|------|
| Completitud de líneas | ¿Tenemos **algún** mercado canónico **completo** y útil en CDM (no un par fijo 1X2+O/U)? |
| Confianza modelo | Etiqueta **subjetiva** del LLM (no confundir con P(acierto)); en v1 vivía sobre **bundle rico** — en BT2 hay que **re-etiquetar en UX** si el insumo aún es mínimo. |
| Score dato / edge numérico | Métrica **definida en servidor** (auditable); candidata a alimentar “alta calidad” agregada y **barra premium** más alta que estándar. |

Así UX y analytics **no mezclan** etiquetas sin contrato.

---

## 4. Entregable típico BA con PO

1. **Lista de criterios medibles** (SQL / métricas / checks en job o API).  
2. **Umbrales iniciales** y **criterio de revisión** (cuándo el PO reabre el umbral).  
3. **Impacto esperado** en volumen diario de picks y en **backtesting** (qué tabla de odds se usa como “verdad” en el tiempo — ver nota de reconciliación CDM).

---

## 5. Anexo — enlaces y referencias

### 5.1 Documentos relacionados

- [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) — contrato v1 de `ds_input` y nota BT2 §8.  
- [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md) — atraco vs `fetch_upcoming`, `bt2_odds_snapshot`, implicaciones para backtest.  
- Sprint 06 — contrato DSR / lotes: **D-06-018**, **D-06-019** en [`../sprint-06/DECISIONES.md`](../sprint-06/DECISIONES.md).  
- [`DECISIONES.md`](./DECISIONES.md) — **D-06-021** … **D-06-026** (pool valor, post-DSR persistido, fallback transparente, vacío duro §6, KPI v0).  
- [`../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`](../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md) — auditoría CDM (**T-188**, fuera de alcance S6.1 hasta decisión explícita de PO).

### 5.2 US / tareas (fuente de verdad: [`US.md`](./US.md) + [`TASKS.md`](./TASKS.md))

| ID | Título resumido |
|---------------|-----------------|
| US-DX-003 | Contrato `ds_input` ampliado |
| US-BE-032 | Builder `ds_input` desde CDM |
| US-BE-033 | Pool, umbrales, premium más estricto |
| US-BE-034 | Post-DSR / coherencia vs implícitas |
| US-BE-036 | Orquestación snapshot (D-06-022) |
| US-FE-055 | Copy semántica UI |
| US-BE-035 | Admin medición v0 (conteos; **obligatorio** S6.1 vía **T-183**; KPI “% acierto” → US posterior) |

Desglose: [`TASKS.md`](./TASKS.md) **T-171–T-187**; orden: [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md) (**D-06-023**). Evidencia cierre: [`EJECUCION.md`](./EJECUCION.md).

### 5.3 Umbrales (fuente de verdad **DECISIONES** S6.1)

| Parámetro | Valor / estado | Notas |
|-----------|----------------|--------|
| Cuota mínima | **1.30** | **D-06-024** |
| Mercados obligatorios | **Ningún par fijo** | **D-06-024** / **D-06-026** |
| Post-DSR persistido | Cuota desde input si desvío; omitir si mercado inválido | **D-06-024** / **D-06-026** |
| Cobertura baja (flag UX) | Opcional: &lt; 5 futuros → `limited_coverage`; no bloquea fallback | **D-06-026** §4 |
| Vacío duro (sin fallback estadístico) | **0** filas elegibles en pool SQL de fallback (filtros **T-177**) | **D-06-026** §6 |
| KPI >70% / >80% | Dirección PO; MVP admin = conteos; % acierto → US posterior | **D-06-026** §5 |

---

*Última actualización: 2026-04-09 — Alineación con **DECISIONES** **D-06-021**…**D-06-026**; §5.2 US-BE-035; §5.3 vacío duro §6.*
