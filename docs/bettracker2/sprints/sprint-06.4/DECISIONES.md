# Sprint 06.4 — DECISIONES

> **Jerarquía normativa del programa:** el documento madre / norte general sigue siendo **[`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md)** — ordena fases, frentes **F1–F6** y la relación entre capas (ingesta, `ds_input`, señal DSR, snapshot/tiempo, UX, medición). Los `PLAN.md` / `TASKS.md` / `US.md` de cada sprint **operativizan** porciones de ese norte; **no** lo sustituyen.  
> **Backlog del sprint:** [`PLAN.md`](./PLAN.md), [`TASKS.md`](./TASKS.md), [`US.md`](./US.md).  
> **Sprint anterior:** S6.3 — **no** reabrir aquí decisiones de cierre Fase 1 / F2 salvo referencia técnica puntual.  
> **Convención alcance:** cambio material en código o contrato operativo → nueva **US** y/o nueva **D-06-0xx** antes de merge.

* * *

## D-06-062 — Sprint 06.4 implementa la Fase 2 del roadmap: frente F3 (frescura vs coste) (2026-04-15)

**Contexto:** En `ROADMAP_PO_NORTE_Y_FASES.md`, **Fase 2** describe “Frescura sin quiebrar el banco” y el frente **F3** cubre la capa **D** (snapshot / tiempo): política de refresco, ingesta SM frecuente vs llamadas DSR, impacto en coste y calidad percibida.

**Decisión:**

1. El alcance **normativo y de ingeniería** de **S6.4** es **exclusivamente** ese frente: **Fase 2 = F3** en la nomenclatura del roadmap (frescura operativa y coste defendible).  
2. **F4** (variedad de mercados / sesgo 1X2) y **F5** (conducta, DP, preview) quedan **fuera** de obligaciones de cierre de S6.4.  
3. El problema central a resolver en S6.4 es **frescura de datos y coste de cómputo/API**, **no** la diversidad de mercados en la señal.

**Trazabilidad:** [`PLAN.md`](./PLAN.md), US-BE-058 … US-BE-062, US-OPS-003; tareas T-267 en adelante.

* * *

## D-06-063 — Verdad madre del programa permanece en sprint-06.3 (2026-04-15)

**Contexto:** El trabajo de documentación y entrega vive en la carpeta `sprint-06.4`, pero el **norte estratégico** del programa BT2 ya está consolidado en el roadmap PO.

**Decisión:**

1. Cualquier sprint (incluido **06.4**) debe alinearse a **[`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md)** para fases, frentes y orden de palancas.  
2. Si hay tensión entre un documento de **S6.4** y el roadmap PO, gana el **roadmap** salvo **enmienda explícita** firmada en `DECISIONES.md` del roadmap o aquí con referencia cruzada.

**Trazabilidad:** [`PLAN.md`](./PLAN.md) § cabecera; kickoff S6.4.

* * *

## D-06-064 — Separación obligatoria: refresco CDM/SM vs invocación DSR (2026-04-15)

**Contexto:** Mezclar ambos canales impide razonar coste y SLA de datos cercanos al partido.

**Decisión (borrador operativo hasta kickoff numérico):**

1. La **política de frescura** debe documentar al menos: **qué** se actualiza por ingesta SM/CDM; **cada cuánto** o bajo qué disparadores; **qué** queda como verdad en tablas CDM/SM sin pasar por DSR.  
2. Las **llamadas DSR** deben tener criterio explícito de **cuándo sí** (p. ej. nuevo snapshot para slate, cambio material en insumo, ventana pre-partido acotada) y **cuándo no** (p. ej. solo actualización de odds o lineups en raw ya contemplada en pipeline).  
3. Métricas de coste deben poder **desagregar** SM vs DSR en reporte u observabilidad mínima acordada en `TASKS.md`.

**Trazabilidad:** US-BE-058, US-BE-059, US-OPS-003.

* * *

## D-06-065 — Medición “tiempo hasta lineups / O-U”: una sola vía en S6.4 (2026-04-15)

**Contexto:** El roadmap menciona medición opcional de frescura (lineups / O-U). En S6.4 no debe haber dos US competidoras para el mismo fin.

**Decisión:**

1. **US-BE-060 no tiene backlog ejecutable en S6.4**; su intención queda **cubierta** por **US-BE-061** (intradía SM, día operativo) y **US-BE-062** (benchmark 5 ligas vs SofaScore).  
2. **Prioridad de medición/discovery:** **US-BE-061** + **US-BE-062** con persistencia tabular (**D-06-067**, **D-06-066** §4) y parámetros **D-06-068**. Eso **no** reabre US-BE-060.  
3. Lo **opcional** = **posponer** una **corrida** de **061**/**062** o un **día**; no sustituir el **universo** de **061** por submuestreo arbitrario (**D-06-068**).  
4. No anticipa **F4**.

**Trazabilidad:** US-BE-061, US-BE-062; **T-280–T-282**, **T-283–T-288**.

* * *

## D-06-066 — SofaScore en S6.4: solo benchmark / discovery; prohibido fallback productivo (2026-04-15)

**Contexto:** Se requiere comparar frescura y disponibilidad SM vs SofaScore para informar F3. El repo ya tiene procesadores/scraper SofaScore (`processors/lineups_processor.py`, `core/scraped_odds_anchor.py`, `processors/odds_all_processor.py`, `processors/odds_feature_processor.py`).

**Decisión:**

1. Cualquier uso de SofaScore dentro de **S6.4** bajo **US-BE-062** es **exclusivamente** medición, benchmark o discovery.  
2. Queda **explícitamente no aprobado** en este sprint: fallback productivo a SofaScore, sustitución de SM como fuente normativa BT2/CDM, feature flags que activen consumo SofaScore en pipeline productivo, o decisión de cambio de proveedor.  
3. Una eventual integración productiva requeriría **sprint y decisión normativa nueva**, fuera del alcance F3 documental de S6.4.  
4. Persistencia de hechos benchmark: **T-288**, misma norma que **D-06-067** §3 (consultable en SQL; no “solo logs”).

**Trazabilidad:** US-BE-062; **T-283–T-288**; checklist **T-286**.

* * *

## D-06-067 — Medición intradía SM como insumo a política F3 (2026-04-15)

**Contexto:** La política de refresh (US-BE-058) necesita datos sobre **cuándo** SM expone lineups y mercados relevantes intradía.

**Decisión:**

1. Se autoriza **job/cron de observación** SM sobre el universo **D-06-068** §1, con cadencia **§2**, que **registre** disponibilidad sin implicar por sí solo cambio de política DSR hasta que PO/TL incorporen hallazgos al acta.  
2. La medición debe respetar **rate limits** y coste SM; no sustituye evaluación oficial ni F2.  
3. Los registros deben quedar en **persistencia estructurada consultable** (p. ej. Postgres, tabla append-only de observaciones/eventos) para poder calcular al cierre del día **primera** lineup, **primera** disponibilidad de mercados relevantes y **frecuencia** de cambio por fixture; **no** basta como única fuente analítica el volcado solo a logs sin esquema equivalente.

**Trazabilidad:** US-BE-061; **T-280, T-287, T-281, T-282**; **D-06-068**.

* * *

## D-06-068 — Congelación operativa US-BE-061 / US-BE-062 (ejecución medición; no es política F3 final) (2026-04-15)

**Contexto:** Sin universo, cadencia y definiciones de “disponible” y matching fijados, **T-287**/**T-288** no generan evidencia comparable para **US-BE-058**.

**Decisión (congelada para implementación 061/062):**

1. **Universo:** todos los partidos del **día operativo** en las **5 ligas objetivo** (misma nómina F2 / S6.3).  
2. **Cadencia de observación** respecto al `kickoff_at` de cada fixture (misma TZ documentada en **T-280**):  
   - de **T−24h** a **T−6h**: cada **60** min;  
   - de **T−6h** a **T−90m**: cada **15** min;  
   - de **T−90m** a **kickoff**: cada **5** min;  
   - de **kickoff** a **T+15m**: cada **5** min.  
3. **Familias / señales observadas** (primera ejecución): **lineups**, **FT_1X2**, **OU_GOALS_2_5**, **BTTS**.  
4. **Lineup disponible:** `true` solo si hay lineup **usable para local y visitante**; un solo lado ⇒ `false`.  
5. **Mercado disponible (por familia):** `true` si en esa observación existe **cotización usable** para esa familia.  
6. **Matching SM ↔ SofaScore:** primario por **liga** + **kickoff** + **nombres normalizados** local/visitante; si hay ambigüedad, marcar **`needs_review`**; **no** bloquear la corrida por esos casos.

**Trazabilidad:** US-BE-061, US-BE-062; **T-280**, **T-283**; **D-06-066** (SofaScore solo discovery).

* * *

*2026-04-15 — decisiones S6.4 (incl. **D-06-068** congelación 061/062).*
