# Sprint 06 — Decisiones

## D-06-001 — Calendario: Sprint 06 = motor + datos; Sprint 07 = parlays + diagnóstico + D-04-001

**Contexto:** El equipo repitió la etiqueta “Sprint 5/6” en conversaciones; en repo ya vale **D-05-001** (S5 = cierre V2, S6 = motor, S7 = parlays/diagnóstico).

**Decisión:** **Sprint 06** implementa y documenta: **DSR+CDM**, **cron fetch_upcoming**, **enum/normalización mercados**, **US-DX/OpenAPI** asociado, **analytics picks/bóveda** (MVP acotado en **D-06-004**). **Sprint 07** acoge parlays, recalibración diagnóstico longitudinal y **D-04-001** salvo cambio explícito de PM.

---

## D-06-002 — DSR y backtesting: fases y anti-fuga de información

**Contexto:** Los picks deben incorporar **criterio del modelo** sobre edge/selección; un diseño ingenuo expone **resultados históricos** al razonador y contamina backtest.

**Decisión (marco):**

1. **Fase A — Offline / diseño:** definir qué features puede ver DSR en entrenamiento o evaluación y qué queda **bloqueado hasta kickoff** (lista cerrada por BA BE + DS).
2. **Fase B — Producción diaria:** el input a DSR para el día **D** solo incluye datos permitidos por el contrato **US-DX-002** (sin “resultado del partido” ni estadísticas post-match para eventos aún no jugados).
3. **Trazabilidad:** versionar `ds_input` / hash o `pipeline_version` en BD o artefacto para auditoría.

4. **Enmienda PO (v1.1 — backtest):** en corridas de **backtesting**, los datos de entrada al pipeline **no** deben incluir información con **menos de 24 h de antelación** respecto al **día simulado** que se evalúa (regla mínima anti-fuga acordada con PO). BE documenta el **ancla de “día”** (p. ej. inicio en **TZ usuario** vs **UTC**) para que la regla sea reproducible.

**Trade-off:** Más ingeniería upfront; menos riesgo de “edge fantasma” en informes al PO.

**Trazabilidad:** **US-BE-025**, **US-DX-002**, **T-154+** en [`TASKS.md`](./TASKS.md).

---

## D-06-003 — Mercados CDM: enum canónico en picks (evolución D-04-002)

**Contexto:** Hoy coexisten `'1X2'`, `'Match Winner'`, `'Full Time Result'`, etc.; **settle** y queries son frágiles (**D-04-002** Sprint 04).

**Decisión:** Introducir **valor canónico** persistido (enum o tabla de referencia) en **`bt2_picks`** / snapshot que alimenta vault, mapeado desde Sportmonks en **ingesta o en capa ACL**; `_determine_outcome` (o sucesor) consume **solo** canónicos. El FE recibe el canónico + `*_human_es` si hace falta copy.

**Consecuencia:** Migración o backfill controlado; coordinación con **Sprint 05** **US-BE-023** si ya tocó `market` (sin duplicar narrativas: una sola fuente tras merge de ramas).

**Enmienda PO (v1.1 — corte duro y aclaración “settle”):**

- **Picks nuevos / bóveda publicada en S6:** **sin modo dual** de strings legacy: se persiste y expone **mercado canónico** (salvo lista explícita de excepción temporal documentada en migración).
- **Origen de la sugerencia del día:** PO exige **corte duro** respecto a armar el día con **regla estadística legacy**; las **sugerencias** que el usuario ve en flujo S6 provienen del **pipeline DSR** acordado.
- **Liquidación (`POST .../settle`):** sigue siendo **determinística** según **resultado del evento** y mercado canónico; **no** es “sugerencia del modelo”. Evitar confusiones de lenguaje entre **origen del pick** (DSR) y **resolución del pick** (reglas deportivas).

**Trazabilidad:** **US-BE-027**, **US-DX-002**, **US-FE-054** *(o US-FE-052 si se unifica)*.

---

## D-06-004 — Analytics picks/bóveda: MVP vs ampliación

**Contexto:** El producto pide analytics; sin acotar se diluye el sprint.

**Decisión (ratificada — arranque S6, 2026-04-08):**

- **MVP S6:** agregados servidor **leíbles en V2** (conteos, outcomes snapshot, serie temporal por `operating_day_key` según **D-06-010** default técnico) expuestos en **endpoint(s)** acordados en **US-BE-028** + **vista FE** **US-FE-053** (en la práctica **vista admin precisión DSR** **D-06-015** / ref [`refs/us_fe_055_admin_dsr_accuracy.html`](./refs/us_fe_055_admin_dsr_accuracy.html)).
- **Fuera MVP S6:** dashboards BI completos, export CSV, segmentaciones avanzadas — backlog o S7.

**Trazabilidad:** **US-BE-028**, **US-FE-053**, **T-163**, **T-166**; cierre formal de criterios de arranque en **D-06-017**.

---

## D-06-005 — Cron `fetch_upcoming`: responsabilidad y runbook

**Contexto:** En Sprint 04 el script es **ejecución manual**; producción requiere horario y observabilidad.

**Decisión:** El **job** corre en el entorno acordado (cron host, k8s CronJob, o GitHub Actions con secretos) con **runbook** **US-OPS-001**: hora UTC, reintentos 429, alerta si 0 fixtures en ventana esperada, logs estructurados.

**Trazabilidad:** **US-BE-026**, **US-OPS-001**, **T-159**, **T-160**.

**Runbook repo:** [`../../runbooks/bt2_fetch_upcoming_cron.md`](../../runbooks/bt2_fetch_upcoming_cron.md) — job `scripts/bt2_cdm/job_fetch_upcoming.py`.

---

## D-06-006 — operatorProfile y métricas conductuales en DX

**Contexto:** Si el diagnóstico u operador expone `operatorProfile` en métricas para UI, hace falta **catálogo estable** (alias camelCase, valores cerrados).

**Decisión:** Ampliar **US-DX-002** con tabla `operatorProfile` / valores permitidos y su **`label_es`**; ningún valor nuevo en JSON de API sin fila en catálogo.

**Trazabilidad:** **US-DX-002**, **US-FE-052** si el FE muestra perfil en analytics.

---

## D-06-007 — Alcance PO (cuestionario v1, 2026-04-08)

**Fuente:** [`pregts_definiciones.md`](./pregts_definiciones.md) **v1**.

**Resultado de negocio #1:** el **modelo (DeepSeek Reasoner / API)** debe **justificar la selección** y dejar explícito el **tipo de mercado** (1X2, doble oportunidad, draw, BTTS, over/under, etc.). **Referencia técnica:** revisar contratos entrada/salida DeepSeek de **v1** solo como consulta de diseño.

**DSR:** conjunto de **candidatos** entra al reasoner; salida = **opciones claras** sobre el mercado más defendible por evento (detalle en **US-BE-025** / **T-154**).

**Persistencia:** los picks (y metadatos necesarios) deben **persistir** para **evaluar eficiencia del modelo** (no basta solo con logs).

**Narrativa bóveda:** **híbrida** — BE entrega **contenido estructurado** del modelo; FE puede componer con plantillas. Referencia UX: flujos tipo v1 `runs/.../picks` (solo inspiración; V2 sigue rutas `/v2/*`).

**Prioridad de recorte si hubiera presión:** PO indica *ninguna* en el cuestionario; se registra como **ambición declarada** — el equipo puede proponer **fases** en **TASKS** si el cronograma real lo exige.

**Riesgo principal (PO):** **compliance** (marco en **D-06-014**; cerrar con legal si aplica).

**Criterios de “S6 terminado” (mínimos propuestos + PO):** (1) job ingesta **7 días consecutivos** OK en entorno acordado; (2) **0** picks en prod con mercado **no mapeado** al canónico (salvo lista explícita de excepción); (3) **checklist PO** firmado; (4) evidencia de **pick generado y persistido por DSR** en flujo end-to-end demo; (5) vista/analytics que permita **ver picks atribuibles a DSR** (MVP **D-06-004**).

**Trazabilidad:** **US-BE-025**, **US-FE-052**, **T-157–T-168**.

---

## D-06-008 — Composición diaria bóveda vía DSR (15 picks / franjas / tiers)

**Contexto:** PO define cupo de **presentación** alineado a franjas ya usadas en producto.

**Decisión (PO v1):** el modelo debe soportar la **propuesta del día** con **15 picks**: **5 por franja horaria** (3 franjas); entre ellos **2 premium de alto valor** y **3 libres** de **alta calidad estadística**, de modo que exista **incentivo real** al desbloqueo premium.

**Notas de ingeniería:**

1. Coherencia con **D-05.2-002** (franjas TZ usuario) y cupo operativo **3 std + 2 prem** — este ítem es **composición del snapshot / narrativa DSR**; unificar con vault en **US-BE-025**.
2. **Pipeline:** **prefiltro + candidatos generados en backend** (`build_candidates` o sucesor) = **único** insumo enviado a DSR; la salida debe ser **selección dentro de ese conjunto** (validación de esquema; **no** mercados/selections fuera del set — mitiga alucinaciones).
3. **Objetivo 15:** si DSR declara **sin valor** en parte del pool, **no forzar** 15: menos ítems + **D-06-009**. **Calidad:** mantener pool **M ≫ 15** antes de DSR; **candidato** a entrar al pool = reglas CDM + **umbral estadístico** (documentar por deporte — gap **D-06-011** §2); **no rellenar slots** por debajo del umbral.
4. Si el CDM no alcanza candidatos suficientes, **degradación documentada** + UI vacía honesta (**D-06-009**).

**Trazabilidad:** **US-BE-025**, **US-BE-030** (evolución respecto a 05.2 si unifica pipeline), **US-FE-052**, **T-158**, **T-165**.

---

## D-06-009 — Ingesta fallida o 0 fixtures (experiencia usuario)

**Decisión:** si el job falla o no hay fixtures/picks generables en la ventana, la app debe mostrar un **estado vacío explícito** (estilo **404** o mensaje claro: *no hay picks ahora, revisá más tarde*), no una lista rota ni error genérico sin copy.

**Entorno job (primer “serio”):** **máquina única** (cron local/host acordado) hasta migración a orquestador.

**Trazabilidad:** **US-BE-026**, **US-FE-052** o pantalla bóveda, **T-159**, **T-165**.

---

## D-06-010 — Mercados canónicos, DX y analytics (precisiones PO v1)

**Mercados:** **multi-deporte desde el día 1**, priorizando **fútbol**; el **mapa fuente → canónico** lo define **BE** (con catálogo en **US-DX-002**).

**Migración / backfill:** interés en **backtesting ciego** — detalle de **backfill** de picks históricos vs solo-forward queda en tarea **US-BE-027** / migración (no bloquea definición de enum).

**Analytics MVP:** audiencia **operador + PO**; métrica mínima explícita: **visibilidad de picks generados por DSR**; **sin export CSV** en S6. **Series temporales:** si no se decide aún, **default técnico** propuesto: agregados por **`operating_day_key`** (últimos **N** días configurable en endpoint) — PO puede ratificar o acotar a “hoy + ayer” en **D-06-004**.

**`contractVersion`:** **bump por entrega** (hitos: DSR, mercados, analytics, etc.), no un solo salto al final del sprint.

**“API vieja” (compatibilidad):** en este repo se distingue **BT2 V2** (`/bt2/*`, `contractVersion`) de **legacy V1** (otras rutas). El FE V2 puede asumir **contrato actual** salvo **feature flag** acordado por hito; no se exige paralelismo indefinido con V1.

**Trazabilidad:** **US-DX-002**, **US-BE-027**, **US-BE-028**, **US-FE-053**, **US-FE-054**, **T-153–T-156**, **T-161–T-167**.

---

## D-06-011 — Estado refinamiento (post v1.1 cuestionario)

**Cerrado con PO (v1.1):** regla **24 h** en backtest (**D-06-002** §4); input DSR **cerrado** al pool backend (**D-06-008**); **TZ usuario** para día/franja (**D-06-012**); **corte duro** mercado + origen bóveda vía DSR (**D-06-003** enmienda); propuesta runbook (**D-06-013**); marco compliance (**D-06-014**).

**Abierto (asignar en v1.2 o ingeniería):**

1. **Firma formal** del dueño del protocolo **Fase B** (lista de campos permitidos en **producción diaria**) — puede ser **BE lead + PO** una vez exista el documento técnico anexo.
2. **Umbrales numéricos** “evento es candidato” por deporte/liga (**D-06-013**).
3. **Canal/on-call real** y severidad (sustituir placeholder de **D-06-013**).
4. **Parecer legal** sobre proveedor del modelo y datos de usuarios (**D-06-014**).

**Trazabilidad:** [`pregts_definiciones.md`](./pregts_definiciones.md) **v1.1**; **PLAN.md** §6.

---

## D-06-012 — Día operativo y TZ (PO v1.1)

**Decisión:** el **`operating_day_key`** y las **franjas horarias** visibles al operador se interpretan en la **zona horaria del usuario** (**`userTimeZone`** u homólogo en contrato BT2).

**Ingesta:** el **job** en servidor puede ejecutarse en **UTC** u horario fijo operativo; el pipeline debe **etiquetar** picks/candidatos al día operativo correcto para cada usuario (o documentar si el MVP es **una sola región** con TZ por defecto).

**Trazabilidad:** **US-BE-025**, **US-BE-026**, **T-154**, **T-159**.

---

## D-06-013 — Runbook cron / alertas (propuesta hasta asignación PO)

**Decisión (propuesta equipo — ratificar nombre/canal):**

| Ítem | Valor sugerido |
|------|----------------|
| **Dueño funcional** | **BE lead** (o dos personas en rotación semanal). |
| **Alerta** | Email + canal Slack **#bt2-ops** (o el que exista en la org). |
| **Severidad** | **P2** si el job falla un día (sin picks nuevos); **P1** si hay caída de DB/API crítica. |
| **Runbook mínimo** | Comando de **retry**, ruta de **logs**, “qué revisar si 0 fixtures”, enlace en **US-OPS-001** / **T-160**. |

**Trazabilidad:** **US-OPS-001**, **T-160**.

---

## D-06-014 — Compliance (qué significa y qué preguntar)

**Contexto:** “Compliance” en productos con **IA de terceros** y **datos de usuarios** suele cubrir, según jurisdicción y modelo de negocio:

- **Proveedor del modelo (DeepSeek):** ¿hay **DPA** / términos que permiten usar datos de fixtures + prompts? ¿Se envía **PII** (nombre, email) en prompts? *(Objetivo: **no**.)*
- **Retención:** cuánto tiempo se guardan **prompts**, **respuestas** y **logs**; derecho de borrado si aplica **GDPR** u homólogos.
- **Apuestas / juego:** si el producto opera en jurisdicciones reguladas, pueden existir requisitos de **auditoría** de cómo se generó una sugerencia (trazabilidad **D-06-002** / persistencia picks).

**Decisión:** el alcance **S6** incluye **checklist interno** (sin PII en prompts, retención mínima documentada, revisión de términos DeepSeek) y **ticket a legal** si el producto tiene usuarios en **UE/UK** u otras zonas con ley de datos estricta.

**Trazabilidad:** PO + legal; **US-BE-025** (logging sin datos sensibles).

---

## D-06-015 — Alcance mínimo ejecutable S6 (recorte PO: “empezar por lo medible”)

**Contexto:** El sprint estaba **sobre-dimensionado** (enum global en toda la UI, cron prod, DX ancho, operatorProfile, etc.). PO prioriza **una sola ola** que demuestre valor: **DSR integrado**, picks **trackeables**, **medibles** al cerrar, y **vista admin** con agregados persistidos.

**Decisión — núcleo obligatorio S6:**

1. **Integración DSR:** llamadas por **lotes** de **candidatos** generados en backend (sin **ningún dato de usuario** en el prompt). Contrato de prompt/versionado en **módulo Python dedicado** (patrón a revisar en **v1** / jobs existentes).
2. **Persistencia trazable:** guardar por pick/snapshot lo necesario para saber **qué predijo el modelo** (mercado + selección concretos: 1X2 local, over 2.5, BTTS sí, etc.) + `pipeline_version` / hash de input **sin PII**.
3. **Medición al settle — “se cumplió como predijo el modelo”:** al liquidar cada evento, determinar si el **desenlace real del mercado** coincide con lo que **DSR sugirió** para ese pick. Ejemplos de criterio (según tipo de mercado persistido): *1X2* → ganó la selección indicada (p. ej. **home**); *totales* → se cumplió **over/under** según la línea y el resultado (p. ej. **over 2.5** con ≥3 goles); *BTTS*, *doble oportunidad*, etc. con regla explícita en **OpenAPI / doc BE** por `market` (sin ambigüedad). Casos **void** / **push** / **no aplicable** quedan en enum aparte (**p. ej.** `modelPredictionResult`: `hit` \| `miss` \| `void` \| `n_a`).
4. **Denominador de la métrica diaria:** la **meta** es **15** picks DSR por día; si el modelo (o el pipeline) devuelve **N < 15** ese día, las tasas y conteos del admin usan **N = picks efectivamente publicados ese día** (aciertos / N), no 15 forzado.
5. **Vista admin (MVP):** pantalla **restringida** en S6: por ahora **solo admin** (flag de entorno, lista blanca, o equivalente). **TODO explícito producto:** sustituir por **rol de usuario** en modelo de permisos (p. ej. `is_admin` / `role=analyst`) en **S6.1** o cuando exista tabla de roles. Debe mostrar, por **día operativo / snapshot:** **N** picks DSR del día, **cuántos `hit`** tras liquidar, **ratio** (y desglose por pick para auditar).
6. **Bóveda operador:** puede ser **mínima** en S6 si hace falta priorizar admin: que los picks **salgan del pipeline DSR** y se vea **algún** detalle modelo; pulir narrativa **US-FE-052** puede quedar en **S6.1** si el tiempo aprieta.

**Decisión — explícitamente diferido (S6.1 / S7 salvo spike):**

- **US-BE-027** / **US-FE-054** (mercado canónico en **todas** las pantallas) — en el núcleo basta **consistencia interna** DSR + settle para el subconjunto tocado.
- **T-153–T-155** masivos (catálogo DX + operatorProfile) — reducir a **lo mínimo** para el contrato DSR + admin + bump `contractVersion`.
- **T-159–T-160** (cron prod + runbook pesado) — seguir con **manual / máquina única** hasta validar métricas; cron duro cuando el núcleo demueste valor.
- **US-FE-053** genérico — sustituir en la práctica por la **vista admin de acierto DSR** descrita arriba (puede reutilizar **US-BE-028** como endpoint agregado).

**Trazabilidad:** **US-BE-025**, **US-BE-028** (o nueva US-BE-029 “DSR accuracy admin” si se parte el backlog), **US-FE-052** o vista admin dedicada; **T-157**, **T-158**, **T-163** (recortadas), **T-165** opcional vs vista admin primero.

---

## D-06-016 — Estructura funcional vs cambios S6; backtesting a ciegas

### A) ¿Cambia la estructura funcional actual?

**Para el operador (flujo principal V2):** el **viaje** sigue siendo coherente con hoy: **bóveda → tomar pick → liquidar** (y lo ya definido en sesión, ledger, etc.). **No** se redefine el producto como otro tipo de app.

**Lo que sí cambia (más allá de “DSR como generador”):**

- **Origen del snapshot:** los picks del día pasan a armarse por el **pipeline DSR** (lotes de candidatos desde backend), no por la regla estadística legacy para publicar el día.
- **Datos nuevos:** persistir **qué predijo el modelo** por pick y, tras liquidar, el **hit/miss** (u homólogo) — es **extensión de modelo de datos** y lógica en **settle**.
- **Nueva superficie:** **vista admin** (métricas DSR) — hoy no existía como requisito de S6 recortado.

En resumen: **la estructura funcional del operador se mantiene**; los cambios son **pipeline de generación**, **persistencia de trazabilidad**, **cálculo al cierre** y **pantalla admin**.

### B) ¿Backtesting a ciegas en este sprint?

**En el núcleo S6 (D-06-015 — Ola 1):** el entregable es **integración en camino producto** + **medición en picks reales liquidados** + **admin**. Ahí **no** está contemplado como alcance obligatorio un **runner de backtesting ciego** (reproducir días históricos con dataset congelado, batch masivo, informes offline).

**Lo que sí queda en doc:** la **regla anti-fuga mínima** (**D-06-002** §4 — datos de entrada al pipeline de backtest ≥ **24 h** antes del día simulado) para cuando se implemente ese runner.

**Recomendación:** **backtesting a ciegas como producto/herramienta** → **S6.2 / Sprint 07** (o spike en paralelo si hay capacidad), **después** de que el pipeline DSR y el **hit/miss** en prod estén estables — reutiliza el mismo contrato de mercado y la misma función de “¿acertó el modelo?”.

**Trazabilidad:** **US-BE-025** (extensión futura); **jobs/** v1 como referencia de batches.

---

## D-06-017 — Arranque ejecución completa Sprint 06 (green light)

**Contexto:** `PLAN.md` §2 y [`TASKS.md`](./TASKS.md) (**T-153–T-168**) describen el sprint completo (DX, DSR, mercados canónicos, cron, analytics, FE bóveda + admin + labels, OPS). **D-06-015** había listado recortes para una “ola 1”; el equipo quiere **un solo arranque** de sprint, con paralelismo **FE ∥ BE** (y DX/OPS en sus carriles), **sin** interpretar el sprint como “solo núcleo primero y el resto indefinido”.

**Decisión (PO — 2026-04-08):**

1. **Ejecución plena del backlog S6** documentado en **`TASKS.md`**: todas las tareas **T-153–T-170** (incl. **T-169** — DeepSeek en vivo **D-06-018**; **T-170** — lotes v1-equivalentes **D-06-019**) están **en alcance del mismo período de sprint**; el **orden** lo marcan dependencias técnicas en [`EJECUCION.md`](./EJECUCION.md), no un recorte global de producto.
2. **D-06-015** conserva el **núcleo de valor** y los **criterios mínimos de “S6 terminado”** acordados en **D-06-007**; la subsección **«explícitamente diferido»** de **D-06-015** **no excluye** ya esas tareas del sprint — queda como **priorización sugerida** (qué demuestra valor antes) si hace falta desempate en el día a día.
3. **D-06-002 (fases DSR):** el **marco** (fases A/B, anti-fuga producción **§1–§3**, regla 24 h backtest **§4**) queda **ratificado para arranque**. El detalle cerrado de **lista de campos Fase B** puede completarse en **US-DX-002** / **T-154** durante el sprint (el ítem **1** aún abierto en **D-06-011** sigue como firma formal del anexo técnico cuando exista, **sin** bloquear el inicio de código).
4. **D-06-004:** ratificada en esta misma fecha — ver enmienda arriba en **D-06-004**.
5. **US-DX-002:** el **alcance** está en [`US.md`](./US.md) + **`TASKS.md` T-153–T-156**; la ejecución DX **arranca en paralelo** con BE desde el día 1. La regla **«merge masivo FE dependiente de contratos»** se interpreta por **hito** (`contractVersion`, shapes estables por endpoint), **no** como veto a abrir el sprint en FE y BE a la vez.
6. **US-OPS-001 / runbook:** **baseline operativa** = propuesta **D-06-013** (dueño, severidad, runbook mínimo) documentada en **T-160**; **canal/on-call** y placeholders del ítem **3** abierto en **D-06-011** se **sustituyen** cuando la org asigne nombres reales, sin bloquear redacción del runbook ni **T-159**.

**Trazabilidad:** [`PLAN.md`](./PLAN.md) §6, [`EJECUCION.md`](./EJECUCION.md), [`US.md`](./US.md).

---

## D-06-018 — Proveedor DSR: `rules_fallback` vs DeepSeek en vivo (BT2 API)

**Objetivo de producto (PO — inequívoco):** En **V2**, los picks del snapshot diario deben generarse con **DSR vía modelo** en condiciones normales de **staging/producción**: **replicar o adaptar v1** (`deepseek_batches_to_telegram_payload_parts` + forma **`picks_by_event` / `ds_input` por lote**), **dentro del pipeline BT2** (API, BD, anti-fuga **D-06-002**, sin depender de `out/batches/*.json`). **T-169** cubre **integración HTTP + persistencia** con DeepSeek; **la equivalencia de criterio de selección con v1 (lotes)** es **T-170** — **D-06-019**. **No** se acepta “1 llamada por evento” como **diseño final** sustituto de v1 sin **excepción explícita firmada por PO** (y entonces debe documentarse como deuda). Lo ya entregado en **T-157** (`rules_fallback`) es **contrato + persistencia + tests**, no el destino final del producto.

**Contexto técnico:** Hoy **`bt2_dsr_suggest.py`** no llama a DeepSeek: aplica **reglas locales** y persiste **`dsr_source = rules_fallback`**. Eso sigue siendo **válido** como **modo seguro**: CI, máquinas sin key, o **degradación** si la API falla — pero **no** sustituye al objetivo anterior en entornos donde el PO exige razonador.

### A) Léxico producto / código

| Valor `dsr_source` | Significado |
|--------------------|-------------|
| **`rules_fallback`** | Mercado/selección y narrativa generados **solo en servidor** con reglas determinísticas (sin llamada LLM en ese request). |
| **`dsr_api`** | Señal atribuible a **llamada DeepSeek** (u otro proveedor OpenAI-compatible) en el camino que genera el snapshot. |

**`rules_fallback` no es “bug”:** es **respaldo** (CI, dev sin key, error de red/API). **Meta en staging/prod con credenciales:** picks con **`dsr_source=dsr_api`** y narrativa/selección provenientes de **DeepSeek**, alineado a **D-06-007**.

### B) Referencia técnica v1 (jobs, no acoplar BT2 al filesystem)

- **Job:** [`jobs/deepseek_batches_to_telegram_payload_parts.py`](../../../../jobs/deepseek_batches_to_telegram_payload_parts.py) — llama **`POST {base_url}/chat/completions`** (API **OpenAI-compatible**), lee **`DEEPSEEK_API_KEY`** (nombre de env por defecto en CLI `--api-key-env`), **`base_url`** default `https://api.deepseek.com`, modelos típicos `deepseek-reasoner` / `deepseek-chat`; timeouts, reintentos y extracción de contenido (`choices[0].message.content`, manejo `reasoning_content`, fallback chat para forzar JSON — ver `_call_deepseek_chat`, `_extract_message_content`, `_force_json_from_reasoning`).
- **Runner / env:** [`jobs/independent_runner.py`](../../../../jobs/independent_runner.py) y [`openclaw/DEEPSEEK_LOCAL.md`](../../../../openclaw/DEEPSEEK_LOCAL.md) — variables **`DS_CHAT_MODEL`**, **`DS_ANALYSIS_MODEL`** / **`DS_MODEL`**, timeouts largos para reasoner.
- **Flujo v1:** lotes JSON en disco (`split_ds_batches` → batches) → DeepSeek → partes payload Telegram. **BT2 API** **no** debe depender de `out/batches/*.json`; debe construir **payload mínimo** desde filas CDM/candidatos ya en memoria o BD, alineado a **anti-fuga** (`bt2_dsr_contract.assert_no_forbidden_ds_keys`, hash del input enviado al LLM).

### C) Configuración propuesta (implementación **T-169**)

| Variable | Rol |
|----------|-----|
| **`BT2_DSR_PROVIDER`** | **`deepseek`** — objetivo en **staging/prod** con key (llamada al modelo antes de persistir snapshot; éxito → `dsr_api`). **`rules`** — solo reglas, útil en **dev local** sin gastar API o en **CI** sin secretos. *(Default en código: BE puede usar `rules` si no hay key, pero **despliegue con PO = DSR completo** debe fijar `deepseek` + `DEEPSEEK_API_KEY`.)* |
| **`DEEPSEEK_API_KEY`** | Credencial (misma convención que v1). **Obligatoria** donde `BT2_DSR_PROVIDER=deepseek`. |

**Variables opcionales (solo si querés cambiar lo que el código ya trae por defecto):** no hace falta tocarlas en `.env` salvo tuning u operación especial.

| Variable | Qué es (en criollo) | Si no la definís |
|----------|---------------------|-------------------|
| **`BT2_DSR_DEEPSEEK_BASE_URL`** | URL base del API estilo OpenAI (`…/chat/completions`). Solo cambia si usás **proxy** o otro host compatible. | Se usa **`https://api.deepseek.com`**. |
| **`BT2_DSR_DEEPSEEK_MODEL`** | Nombre del modelo en el JSON de la petición (ej. `deepseek-reasoner` más lento y “pesado”, `deepseek-chat` más rápido/barato — misma tensión que v1). | BE fija un default documentado en código/PR (p. ej. alineado a v1). |
| **`BT2_DSR_TIMEOUT_SEC`** | Segundos máximos **por petición HTTP** (en diseño **por lote v1-equivalente**, un timeout por lote — ver **D-06-019**). | Default razonable en código (inspirado en v1, p. ej. 120–420 según modelo y tamaño de lote). |
| **`BT2_DSR_MAX_RETRIES`** | Cuántas veces **reintentar** la misma llamada ante fallos **transitorios** (red, 5xx). | Default bajo (p. ej. 0–1) para no duplicar coste ni latencia. |

**Documentar en** [`.env.example`](../../../../.env.example) **comentarios** (sin secretos).

### D) Comportamiento ante error

- Si `BT2_DSR_PROVIDER=deepseek` y **falta key** o la API **falla** (timeout, 4xx/5xx): **degradar** a **`rules_fallback`**, registrar **warning** estructurado (sin PII), y persistir `dsr_source=rules_fallback` **o** fallar el job con error explícito según política de entorno — **default recomendado: degradar** para no dejar día sin snapshot en prod; PO puede cambiar a “fail closed” en staging.

### E) Contrato de salida hacia persistencia

- La respuesta del LLM debe mapearse a los campos ya existentes: **`model_market_canonical`**, **`model_selection_canonical`**, **`dsr_narrative_es`**, **`dsr_confidence_label`**, **`pipeline_version`** (p. ej. `s6-deepseek-v1` por lote vs `s6-rules-v0`), **`dsr_source=dsr_api`** cuando la selección vino de la API exitosamente.
- **OpenAPI / `PickOut`:** ya exponen `dsrSource`; actualizar descripción si hace falta (**T-155** / handoff).

### F) Alcance granularidad — **D-06-019** + **T-170**

El debate **1 llamada / evento** vs **lotes como v1** no se resuelve por criterio técnico aislado: **manda el PO**. Ver **D-06-019**.

### G) Fuera de alcance inmediato (backlog / S6.1)

- Cola async **dedicada** desacoplada de `session/open`, dashboard de coste por token/request.
- Tests de integración **contra API real** en CI (usar **mock HTTP** en CI; prueba manual con key en local/staging).

**Implementación repo:** **`apps/api/bt2_dsr_deepseek.py`** (`deepseek_suggest_batch`, `ds_input` / `picks_by_event`) + **`_generate_daily_picks_snapshot`** (`bt2_router.py`, lotes `BT2_DSR_BATCH_SIZE`) — **T-169** + **T-170** cerrados en BE.

**Trazabilidad:** **US-BE-025**, **T-169**, **T-170** en [`TASKS.md`](./TASKS.md); [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md); **D-06-002**, **D-06-014**.

---

## D-06-019 — Granularidad DSR en BT2: **lotes v1-equivalentes** (decisión PO)

**Contexto:** BE razonó correctamente que **1 llamada por evento** simplifica cableado y aísla fallos, mientras que **v1 por bloques** optimiza coste/latencia de red, permite **comparación cruzada** entre candidatos y encaja con el producto **“~15 picks del día”** y el contrato **`picks_by_event`** alineado al **`ds_input`** del lote. El PO había pedido **replicar/adaptar v1** en **más de una ocasión**; no debe quedar ambigüedad: el **criterio de selección sobre el conjunto** del día es **requisito de producto**, no opcional.

**Decisión (PO — vinculante para BE):**

1. **Diseño objetivo:** al generar el snapshot (`_generate_daily_picks_snapshot` o sucesor), el camino **`BT2_DSR_PROVIDER=deepseek`** debe construir **uno o más lotes** de candidatos (misma **idea semántica** que `split_ds_batches` + batches v1: el modelo ve **varios eventos** en el mismo prompt cuando el tamaño de lote lo permita), invocar DeepSeek con contrato de salida **compatible con `picks_by_event`** (adaptado a campos BT2), y **persistir una fila por evento** en `bt2_daily_picks` a partir de esa salida.
2. **Prohibido presentar como “cierre S6 producto”** un diseño que sea **solo** “1 HTTP por evento sin comparación cruzada en el mismo prompt”, **salvo** que el PO firme una **excepción explícita** y se registre en **DECISIONES** + deuda en **Sprint 07**.
3. **T-169** puede haber entregado **primera integración** (HTTP + persistencia); **T-170** cierra **equivalencia v1 por lotes**. Hasta **T-170** done, el PO puede considerar **US-BE-025** **incompleta en sentido producto** aunque T-169 esté mergeada.
4. **Degradación parcial:** si un **lote** falla, política permitida: reintentar lote, o degradar **solo los eventos de ese lote** a `rules_fallback`, o fallar cerrado — documentar en PR; no contradice D-06-018.
5. **Fuera de este decisorio:** número exacto de lotes por día, tamaño máximo de lote (BE propone, PO ratifica en revisión de PR si hace falta).

**Trazabilidad:** **T-170**, **US-BE-025**, **D-06-018** §B.

---

*Última incorporación: **D-06-019** (lotes v1-equivalentes); **D-06-018**; **D-06-017**; **D-06-015** + **D-06-016**; [`pregts_definiciones.md`](./pregts_definiciones.md) v1.2.*
