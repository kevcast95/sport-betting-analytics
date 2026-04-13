# Sprint 06.1 — DECISIONES

> **Relación:** complementa **D-06-020** (Sprint 06) sin sustituirla — el detalle de señal/edge sigue gobernado por el puente acordado allí.  
> **Objetivo operativo del sprint:** [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md).

---

## D-06-021 — Paridad v1 vs BT2 en `ds_input` y recalibración de la premisa S6.1 (2026-04-09)

**Contexto:** En conversación previa BE/PO para S6.1 se acordó priorizar **menos picks con etiquetas de confianza altas** (alineado a la experiencia v1, donde DSR etiqueta confianza en un flujo con **contexto rico**). Se **asumió implícitamente** que V2 BT2 aportaba al modelo un insumo equivalente al de v1.

**Hecho verificado (código + doc):**

- En **v1**, cada elemento de `ds_input[]` incluye `event_context`, `processed` (lineups, h2h, estadísticas, odds estructurados, etc.) y `diagnostics`, según [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) §4.
- En **BT2** hoy, `deepseek_suggest_batch` construye un **`ds_input` mínimo** (equipos, torneo, cuotas) — explícito en la misma guía §8 y en `apps/api/bt2_dsr_deepseek.py`.

**Conclusión:** La premisa “v1 y v2 están sincronizados en lo que ve DSR” **no era cierta**. La discusión S6.1 sobre **calidad vs cantidad** y **confianza alta** debe **rebasarse** sobre el **objetivo de paridad de insumo** (o sobre reglas servidor que compensen su ausencia), no solo sobre prompt o techo de picks.

**Decisión de producto (PO):**

1. **Objetivo de entrega S6.1:** acercar BT2 al **contrato de entrada v1** (misma forma y riqueza relativa del `ds_input` por evento), **construido desde CDM/Postgres**, respetando **D-06-002** (anti-fuga) — lista cerrada de campos por BA/BE con PO.
2. **Bóveda como territorio DSR (intención):** la señal mostrada debe corresponder a la **misma capa de decisión** que el input del modelo; mientras el pool SQL y el `ds_input` estén desalineados, la UX puede sentirse “dos cerebros”. S6.1 debe **reducir** esa brecha (pool + builder + validación). La **regla operativa de precedencia** y el fallback transparente quedan en **D-06-022** + matiz **D-06-024** / **D-06-025**.
3. **Fallback (reglas / SQL):** último recurso; cuando aplique reglas duras para selección entre outcomes del mismo mercado, **priorizar mayor probabilidad implícita** (cuota más baja entre opciones válidas), coherente con `suggest_from_candidate_row` en v2 y con la expectativa de PO.

**Confianza (`dsr_confidence_label` en BT2):**

- Hoy, en camino **DeepSeek**, la etiqueta deriva del JSON del modelo (`confianza` → `high` / `medium` / `low` en servidor).
- **No** equivale a probabilidad de acierto ni a calidad de ingesta — sigue vigente la separación de semánticas de **D-06-020**.
- Objetivo PO “**menos picks con confianza alta**” en el sentido v1 **requiere** insumo rico y/o **reglas o scores en servidor** que acoten o re-clasifiquen (definición en US + umbrales medibles).

**Meta aspiracional “>80% picks del día alta calidad; premium aún más exigentes”:**

- Se trata como **hipótesis de diseño** hasta definir: (a) qué cuenta como “alta calidad” (composición explícita: score dato + etiqueta + fuente), (b) **ventana de medición** (admin/analytics), (c) responsable de revisar umbral.
- **No** es compromiso de implementación hasta constar en **TASKS** con criterio de aceptación medible.

**Trazabilidad:** [`PLAN.md`](./PLAN.md), [`US.md`](./US.md), [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md).

---

## D-06-022 — Precedencia bóveda: manda el output de DSR; fallback SQL solo si no es fallo de ingesta (PO, 2026-04-09)

**Contexto:** Se discutieron “Opción A / B” solo como formas de **construir el universo de candidatos** hacia DSR (pool SQL con contrato tipo Tier A/B vs flujo más cercano a `select_candidates` v1). El PO precisa la **regla de oro** de qué ve el usuario en la bóveda.

**Decisión de producto (PO):**

1. **La bóveda es territorio del output de DSR** — punto. Lo que DSR entrega como lectura / selección por evento (incluido `picks=[]` con `motivo_sin_pick` donde aplique el contrato) es la **capa primaria** de lo que debe reflejarse como señal del protocolo.
2. **Si DSR devuelve cero picks en el día** (o un conjunto vacío equivalente a “no hay señal” a nivel producto) **y la causa no es un fallo operativo de ingesta del día** (CDM sin futuros, job caído, datos ausentes por error de pipeline — el caso “0 por mala ejecución de ingesta”), **entonces** aplica el **fallback**: armar picks desde el **pool SQL** con el criterio de **mayor probabilidad implícita** (cuota más baja entre outcomes válidos del mercado de referencia), persistirlos y **mostrarlos en bóveda** con **trazabilidad explícita** de que no son salida DeepSeek (`dsr_source`, lineage existente o campo dedicado acordado en **US-DX-003** / **T-173**).
3. **Si el cero es por ingesta fallida del día**, **no** se debe enmascarar con el fallback estadístico como si fuera señal normal: el producto debe quedar en **estado vacío / aviso operativo** y la corrección es **operación** (cron, auditoría — ver nota admin CDM), alineado a [`../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`](../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md).

**Matiz (PO, 2026-04-08):** cuando **sí** hay filas utilizables en CDM pero el modelo no entrega señal suficiente, el fallback con **lineage** y **disclaimer** de datos limitados **sí** aplica — ver **D-06-024** § cobertura y **D-06-025** §4. El punto 3 anterior se interpreta como **vacío duro** (sin candidatos SQL reales), no como “pocos eventos de valor”.

**Relación con A/B:** A y B definen **cómo se eligen candidatos antes del LLM**; **no** sustituyen esta precedencia. BE implementa una u otra (o híbrido) siempre **subordinado** a **D-06-022**.

**Trazabilidad:** [`US.md`](./US.md) — **US-BE-036** (orquestación snapshot); [`TASKS.md`](./TASKS.md); [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md).

---

## D-06-023 — Modo de trabajo S6.1: sin “validación por pasos”; gaps → US/refinement antes de código (PO/BA, 2026-04-09)

**Contexto:** El equipo quiere que, cuando los devs **arranquen ejecución**, el sprint sea **cerrable de un solo bloque** cubriendo **todos** los puntos acordados — no un hilo de “vamos validando paso a paso” que deje **definición sin documentar** o refactors core a mitad de sprint sin contrato.

**Decisión:**

1. **Antes del primer merge de S6.1:** todo hallazgo que sea **bache**, **cambio de core** o **dependencia transversal** debe quedar como **US nueva**, **refinement** explícito de una US madre, o **DECISIÓN** — no como comentario oral o ticket fuera del repo.
2. **No** se asume un modelo de “validar el sprint por fases” donde la definición se completa **durante** la implementación; la definición vive en [`US.md`](./US.md) + [`TASKS.md`](./TASKS.md) + [`DECISIONES.md`](./DECISIONES.md) hasta **kickoff**.
3. **Checklist de cobertura:** [`TASKS.md`](./TASKS.md) debe reflejar **todos** los entregables (incl. orquestación **D-06-022**, paridad **D-06-021**, FE semántica, DX, tests). El **Definition of Done** del sprint = cierre de esas tareas + criterios de US, no acuerdos solo verbales o fuera del repo.

**Trazabilidad:** [`PLAN.md`](./PLAN.md) § modo de trabajo, [`TASKS.md`](./TASKS.md).

---

## D-06-024 — Umbrales operativos S6.1 (pool valor, premium, post-DSR, cobertura) (PO, enmendado 2026-04-08)

**Contexto:** Primera redacción (2026-04-09) fijaba mercados obligatorios 1X2+O/U 2.5 y límites de lote. **Enmienda PO** (intención de producto): el mercado elegido debe ser **respuesta al valor del evento**, no un corsé; aprovechar API/CDM; fallback con transparencia cuando el modelo no basta. **Razonamiento y matiz de bóveda:** **D-06-025**.

**Contrato `ds_input`:** **[`../../dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md)** (T-171), alineado a esta sección y a D-06-025.

### Pool de candidatos a DSR (US-BE-033 / T-177)

| Parámetro | Valor | Notas |
|-----------|--------|--------|
| Cuota mínima (decimal) | **1.30** | Umbral de valor; por debajo no se promueve selección al usuario hasta que una **nueva política** quede documentada en **DECISIONES**. |
| Mercados | **Ningún par obligatorio fijo** | El modelo elige, **entre mercados presentes en CDM** para ese evento, el que mejor expresa valor (ilustración: 1X2 reñido frente a corners O/U con mejor relación valor/cuota). Incluir en el universo objetivo: **1X2**, **doble oportunidad** (cuando haya líneas + coherencia con 1X2), **O/U goles**, **O/U corners**, **O/U tarjetas**, **BTTS**, según ingestión y mapeo canónico. |
| Ligas | **Las ligas prioritarias del producto** (conjunto acotado en configuración operativa; implementación **T-177**) | Alcance editorial, no tope técnico de datos. `is_active` en CDM sigue siendo control operativo de qué competiciones entran. |
| Tamaño de lote / filas por evento | **Sin fijo de producto** | Prioridad: **calidad diaria** y pipeline tipo v1 (corrida diaria, candidatos → DSR). BE dimensiona lotes y recortes por **presupuesto técnico** (tokens, latencia, coste API), documentado en runbook, no como regla PO artificial. |

### Barra **premium** vs standard (US-BE-033 / T-178)

| Tier | Intención PO (cualitativa) | Implementación |
|------|----------------------------|----------------|
| **Standard** | Picks con sensación **media-alta / alta** confianza; meta de producto **superior al 70%** de acierto **medido en ventana** (analytics), para que la bóveda diaria y los DP tengan credibilidad. | Score servidor + etiquetas + datos que alimentan DSR (T-178, métricas en admin). |
| **Premium** | Narrativa **máxima probabilidad de ganar** ese día aunque la cuota sea **≈ 1.30**; el usuario gasta DP por **disciplina y sensación de “casi seguro”**, no por retorno esperado máximo. Otras rachas (otro tier sin DP) pueden verse mejores; el producto acepta esa honestidad. | Reglas **más estrictas** que standard (completitud de mercados relevantes, consenso entre libros, frescura, señales de banca implícita) — detalle cuantitativo en **T-178** con datos reales. |

### Post-proceso salida DSR (US-BE-034 / T-181–T-182) — qué es (resumen)

Ver **D-06-025** § “Qué es post-DSR”. **Lo que se persiste en BT2 no es el JSON crudo del modelo**, sino el **registro de pick ya pasado por Post-DSR** (artefacto canónico listo para bóveda y settlement).

| Aspecto | Política fase 1 (vigente hasta nueva entrada en **DECISIONES**) |
|---------|-----------------------------------------------------|
| **Objeto persistido** | Post-DSR **construye o ajusta** el pick que se guarda: compara input vs output del modelo, aplica reglas parametrizadas, y **solo entonces** INSERT/UPSERT. El usuario ve **esa** versión reconciliada. |
| Coherencia **numérica** (cuota salida modelo vs input) | **Fuente de verdad de la cuota = el input** (`consensus` / CDM). Si DSR declara una cuota desalineada (**desvío > ±15%**, **D-06-024**), el valor **persistido** es el del input para ese mercado/selección canónica (ajustes adicionales solo si **T-181** los documenta), con **log + métrica** de discrepancia. |
| Mercado/selección inválidos respecto al input | Si el core del modelo apunta a un mercado o selección **sin cobertura** en el lote enviado → **no pick** para ese evento en **fase 1** (**D-06-026**). Sin sustituto automático desde Post-DSR hasta decisión explícita nueva. |
| Cuotas extremas **declaradas** por el modelo | Cap de `dsr_confidence_label`: odds declaradas por el modelo **> 15.0** → máximo `medium` (**D-06-024**); la cuota **guardada** sigue anclada al input cuando exista línea válida. |

**Matiz implementación — qué es “modificar” vs “pick nuevo / sustituto”:**

- En la mayoría de casos el artefacto persistido es el **mismo** mercado y **misma** selección que eligió DSR, con **parámetros corregidos** (sobre todo **cuota** y metadatos de confianza tomados o acotados según reglas), no una segunda opinión del servidor sobre el partido.
- Si mercado/selección del modelo **no existen** en el input del lote → **omitir pick** (fase 1, **D-06-026**). **Sustituto mínimo** desde input queda **fuera** de alcance S6.1 hasta nueva decisión en **DECISIONES**.
- El detalle fino **sustituto vs vacío** y los tests de regresión son responsabilidad de **T-181**, acotado por **D-06-026** (fase 1: solo omitir si inválido).

### Cobertura baja, “ingesta rota” y fallback (US-BE-036 / T-179; matiz **D-06-022**)

| Señal | Definición operativa | UX / persistencia |
|--------|----------------------|-------------------|
| **`dsr_signal_degraded`** (nombre de contrato sugerido) | DSR devolvió vacío o cobertura insuficiente **pero** existen filas en CDM para armar candidatos SQL. | Mostrar picks **fallback** (implícita / reglas) con **lineage** claro **y** copy: *no hay suficientes partidos o eventos de valor para el modelo estadístico; estas son opciones reales con criterio alternativo* + **disclaimer**: *la selección está sesgada por los datos limitados del día*. |
| **Vacío duro** | No hay ningún evento/cuota utilizable en el universo configurado (CDM realmente vacío para el día). | Sin picks; mensaje operativo claro (sin disfrazar como señal DSR). |

**D-06-022.3** queda **matizado:** ya no se persigue “pantalla vacía” solo porque el conteo de eventos sea bajo si **aún** se pueden proponer opciones reales desde SQL; la transparencia es obligatoria.

**Trazabilidad:** [`TASKS.md`](./TASKS.md) T-171–T-182; [`../../dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md); **D-06-025**.

---

## D-06-025 — Enmienda PO: valor por mercado, premium, post-DSR explicado, fallback transparente (2026-04-08)

### 1. Filosofía del pool (respuesta al valor, no corsé)

- La premisa **no** es “forzar un pick porque faltaba un mercado en una checklist”, sino **identificar el mercado del partido donde la lectura probabilística + cuota tiene más sentido** (ilustración: clásico reñido en 1X2 con implícitas altas vs **corners O/U** @1.35 con mejor filo).
- **Doble oportunidad:** entra al análisis cuando hay **líneas en CDM** y **respaldo** (coherencia con 1X2 / datos agregados); el modelo decide si aporta valor.
- **O/U** puede ser **goles, corners o tarjetas** (y otras líneas que la API normalice); **BTTS** igual.
- Objetivo operativo alineado a **v1:** corrida diaria (ventana fijada en operación; referencia histórica v1: inicio de día UTC), **procesar localmente** las ligas configuradas, filtros, **pasar candidatos a DSR** y garantizar **señal diaria con calidad**, aprovechando el coste de API pagada (sin topes de producto que desperdicien datos).

### 2. Premium vs standard (intención emocional y de métricas)

- **Standard:** confianza percibida **media-alta / alta** y **meta >70%** aciertos en ventana — la bóveda alimenta la rutina y los DP.
- **Premium:** priorizar sensación de **“casi seguro”** ese día (incluso @1.3); reconocer que **no** es garantía matemática ni monopolio de mejores rachas; refuerza **disciplina y recompensa simbólica** con riesgo residual explícito en copy legal/producto cuando corresponda.

### 3. Qué es “post-DSR” (para no técnicos)

- **Post-DSR** = la fase **servidor** que corre **después** del JSON del modelo y **define qué se persiste**. No guardamos el texto del LLM tal cual; guardamos el **pick canónico** que sale de reconciliar **input + salida DSR**.
- **Cadena de calidad (acuerdo PO):** (1) **filtros claros** de candidatos → (2) **input sólido** (datos del lote / `consensus`) → (3) **core DSR** (mercado y lectura de valor relativo) → (4) **Post-DSR** detecta discrepancias input/output, **ajusta parámetros** (incluido alinear **cuota** al input) o, si las reglas lo exigen, **no persiste** el pick (fase 1 S6.1: sin sustituto de mercado/selección — **D-06-026** §2) → (5) **persistencia** de lo limpio para que el usuario vea picks coherentes con CDM.
- **Núcleo del trabajo de DSR (intención):** elegir el **mercado con mayor valor relativo** (contexto estadístico + cuota en el input). Esa **elección** es del modelo **mientras sea compatible** con el input; si no lo es, Post-DSR aplica la política parametrizada (no alucinar mercados inexistentes en el lote).
- **Fuente de verdad de la cuota persistida:** siempre el **input**; el número que el modelo escriba sirve para **comparar y auditar**, no para guardar a ciegas.
- **Alucinaciones:** se asumen; por eso Post-DSR está **parametrizado** (umbrales, caps de confianza, logs, reglas de omisión y ajuste de parámetros; fase 1 sin sustituto de pick — **D-06-026** §2).
- **No** es un “segundo modelo” que re-opine el partido: es **validación y normalización reglada** hacia un registro único y limpio. Las reglas viven en DECISIONES + código revisable (T-181–T-182).
- **Matiz “pick reconciliado”:** lo normal es **misma lectura DSR** + **parámetros alineados al input**; “pick nuevo” en sentido fuerte solo cuando la salida sea **incompatible** con el lote (ver tabla **D-06-024** § post-DSR, párrafo *Matiz implementación*).

### 4. Fallback cuando el modelo no alcanza o los datos son escasos

- Si con los datos del día el **modelo estadístico** no produce señal suficiente pero **hay** opciones en CDM, el producto prefiere **mostrar alternativas reales** (fallback SQL / implícitas) con:
  - mensaje de que **no hubo suficiente valor para el criterio del modelo**;
  - **disclaimer** de que el criterio de ese bloque está **sesgado por datos limitados**;
  - **lineage** técnico (`dsr_source` / equivalente) para auditoría y FE.

---

## D-06-026 — Ratificación BA: criterios operativos de ejecución (pool/post-DSR/KPI/cobertura) (2026-04-08)

**Contexto:** Se unificó la interpretación entre **US.md** y **D-06-024** / **D-06-025** para evitar reglas contradictorias en kickoff. Esta entrada **fija** criterios ejecutables sin reabrir la filosofía de producto ya acordada.

1. **Pool vs US-BE-033:** la fuente de verdad de elegibilidad y premium es **D-06-024** + **D-06-025** + whitelist **US-DX-003**; **no** hay par obligatorio 1X2 + O/U 2.5 en producto.
2. **Post-DSR / T-181 — sustituto vs vacío (fase 1):** si mercado o selección del modelo **no** tienen cobertura en el input del lote → **omitir pick** para ese evento (no persistir fila DSR inválida). **Sustituto mínimo** desde SQL/implícita **no** entra en fase 1; requiere decisión explícita nueva.
3. **Post-DSR — matriz numérica:** se mantiene tabla **D-06-024** § post-DSR (cuota persistida desde input si desvío > ±15%; cap confianza si odds modelo > 15).
4. **Heurística “cobertura baja” (T-179):** opcional — si el conteo de eventos futuros (ligas activas, ventana día operativo) es **&lt; 5**, se puede exponer flag **`limited_coverage`** (o equivalente) para **copy / disclaimer**; **no** bloquea fallback SQL si hay filas utilizables (**D-06-024** § cobertura).
5. **KPI meta >70% standard (US-BE-035):** intención PO en **D-06-025** §2. **Medición v0 (MVP admin):** agregados por `operating_day_key` de `dsr_confidence_label`, `dsr_source` y **score** cuando BE lo exponga en el contrato admin — **sin** afirmar “% acierto” hasta definir numerador/denominador con **settlement** y ventana (referencia típica **30 días**, a fijar en **US de refinamiento**); hasta entonces la meta >70% es **dirección**, no SLA de build S6.1.
6. **Vacío duro / sin candidatos utilizables (bloquea fallback estadístico):** alineado a **D-06-022** pt. 3 y **D-06-025** §4. Si el **pool SQL** que alimentaría fallback (mismos filtros de elegibilidad que **T-177** / día operativo / ligas activas) devuelve **0** filas elegibles, **no** hay base para picks fallback: el producto queda en **vacío operativo** (sin enmascarar como señal DSR). Ampliaciones (job caído, freshness, umbrales distintos de “0 filas”) pueden documentarse en **T-179–T-180** y [`EJECUCION.md`](./EJECUCION.md) si BE las implementa en S6.1; **no** son obligatorias más allá de este criterio mínimo **0 filas pool**.

**Trazabilidad:** [`US.md`](./US.md) (US-BE-033 … 036), [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md), [`TASKS.md`](./TASKS.md), [`EJECUCION.md`](./EJECUCION.md).

---

## REFINEMENT_S6_1 — Decisiones posteriores a [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md) (PO/BA, 2026-04-09)

> **Fuente narrativa:** [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md) (§1–§7). Esta sección **fija** decisiones ejecutables; **no** sustituye **D-06-021** … **D-06-026** salvo donde se indica **matiz** explícito.

### D-06-027 — Criterio de elección de mercado DSR: lectura apoyada en datos e histórico (no “payout primero”)

**Contexto:** El prompt actual del batch (`bt2_dsr_deepseek.py`) habla de **“mejor relación valor/datos”**, interpretable como **edge / valor esperado**. El PO fijó en **REFINEMENT_S6_1** §2 que, entre mercados disponibles en el input, la lectura debe privilegiar **mayor soporte en estadística histórica y parámetros presentes en `ds_input`**, con **coherencia entre cuota e narrativa**, sin usar “más dinero posible” como regla suelta.

**Decisión:**

1. La **intención de producto** del núcleo DSR se alinea a **REFINEMENT_S6_1** §2 (incl. ejemplo favorito con bajas en lineups).
2. **Matiz sobre D-06-025 §3:** donde se dice “mayor valor relativo (contexto estadístico + cuota)”, **“valor relativo”** se entiende como **lectura de acierto fundamentada en el lote enviado**, no como mandato de perseguir cuotas altas sin anclaje en datos del input.
3. **Pool y elegibilidad** siguen gobernados por **D-06-024** / **D-06-025** / **D-06-026**; esta decisión **no** relaja cuota mínima ni reglas premium/standard.

**Trazabilidad:** **US-BE-038**, **T-191**; revisión conjunta con **US-BE-033** si el copy de reglas internas o filtros mencionan “valor” en sentido ambiguo.

---

### D-06-028 — `ds_input` desde Postgres: consultar histórico del duelo (y cuotas históricas si existen)

**Contexto:** Hoy el builder puede dejar `lineups`, `h2h`, `statistics`, `team_streaks`, `team_season_stats` como **placeholders** aunque la API/CDM y Postgres permitan enriquecer (**REFINEMENT_S6_1** §5–§6).

**Decisión:**

1. **Diseño e implementación** del builder (**refinement** de **US-BE-032**) deben **consultar** la base por datos **históricos relevantes** al enfrentamiento (equipos, H2H, forma, estadísticas agregadas, alineaciones o equivalentes **según existan** en schema, jobs o tablas derivadas).
2. Si existen **cuotas históricas** u otras series persistidas aplicables al contexto del evento, deben **incorporarse** al contrato **solo** vía whitelist **US-DX-003** / **T-171** y validador **T-172** (anti-fuga **D-06-002**).
3. **No** es aceptable dejar `available: false` por defecto en bloques decisorios cuando **ya haya filas consultables** en Postgres para ese evento/equipos; la ausencia debe reflejarse en **`diagnostics`** con causa real (ingesta vacía, TTL, etc.).

**Trazabilidad:** **US-BE-037**, **T-189–T-190**; **US-DX-003** si nuevos caminos en JSON hacia el LLM.

---

### D-06-029 — Coherencia obligatoria `selection` vs `razon` en salida DSR (Post-DSR)

**Contexto:** Salida del LLM puede declarar una selección y un razonamiento **contradictorios**; eso destruye confianza de usuario (**REFINEMENT_S6_1** §3).

**Decisión:**

1. **Post-DSR** (**refinement** de **US-BE-034**) debe incluir reglas o heurísticas que detecten **incoherencia material** entre mercado/selección canónica y el texto de `razon`.
2. **Fase refinement:** ante incoherencia detectada → **omitir** pick DSR para ese evento (alineado a filosofía **D-06-026** §2: no sustituto automático de mercado) **salvo** que una **nueva** entrada en **DECISIONES** autorice otro tratamiento (p. ej. solo degradar etiqueta).
3. **Reescritura** de `razon` por el servidor para “arreglar” la contradicción **no** es alcance por defecto; si se propone, va como decisión explícita nueva.

**Trazabilidad:** **US-BE-039**, **T-192**.

---

### D-06-030 — Prompt batch DeepSeek alineado a D-06-027

**Contexto:** El system prompt actual no refleja literalmente la premisa de **D-06-027**.

**Decisión:** Actualizar `_SYSTEM_BATCH` (y, si aplica, user prompt batch) en `apps/api/bt2_dsr_deepseek.py` para que las instrucciones sean **consistentes con D-06-027**, sin contradicción con **D-06-028** (el modelo no puede “inventar” histórico no enviado).

**Criterio de aceptación:** texto aprobado por PO/BA + tests mínimos de regresión (**T-191**).

**Trazabilidad:** **US-BE-038**, **T-191**.

---

*Entradas: **D-06-021** … **D-06-026** (2026-04-08 / 2026-04-09); **REFINEMENT_S6_1:** **D-06-027** … **D-06-030** (2026-04-09).*
