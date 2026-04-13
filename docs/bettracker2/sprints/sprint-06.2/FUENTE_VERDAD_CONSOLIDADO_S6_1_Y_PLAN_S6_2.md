# Fuente de verdad única — DSR / BT2 / bóveda (cierre S6.1 + plan S6.2)

**Versión:** 2026-04-11 (cierre: obligaciones operativas S6.2 normativas en **§1.13**; §6 = estado del consolidado, sin huecos de descripción).  
**Uso:** al ejecutar **S6.2**, las definiciones ejecutables están en **§1–§3** y **§1.13** (y **§6**). La radiografía operativa (US / TASKS / decisiones / handoff) vive en **`US.md`**, **`TASKS.md`**, **`DECISIONES.md`**, **`HANDOFF_EJECUCION_S6_2.md`** e [`INVENTARIO_TECNICO_S6_2.md`](./INVENTARIO_TECNICO_S6_2.md). Cualquier otro documento del repo es **archivo histórico** salvo enlace explícito desde estos; si algo contradice este texto, **actualizar este archivo** y **§1.13** si aplica.

**S6.1:** cerrado a nivel plan el **2026-04-10** (evidencia de pruebas escenarios en `docs/bettracker2/sprints/sprint-06.1/EJECUCION.md` — no gobierna reglas de producto).

---

## 1. Definiciones ejecutables (núcleo)

### 1.1 Pipeline

Orden obligatorio: **pool de candidatos** → **`ds_input`** → **DSR (batch LLM)** → **JSON estructurado** → **Post-DSR** → **persistencia del pick canónico** → **respuesta bóveda**.  
El usuario **nunca** ve el JSON crudo del modelo; ve el registro **después** de Post-DSR.

### 1.2 Insumo v1 vs objetivo BT2

En **v1**, cada elemento de `ds_input[]` lleva, como mínimo conceptual: **`event_context`**, **`processed`** (cuotas estructuradas, y cuando existen datos: lineups, h2h, estadísticas, etc.) y **`diagnostics`**.  
**Objetivo BT2:** el mismo **tipo de bloques** y **riqueza relativa**, poblados desde **Postgres / CDM** (`bt2_*`), no desde scrap SofaScore en producción.

**Anti-fuga:** en producción, **ninguna clave** que no esté en la **whitelist de fase 1** puede ir en el payload hacia el LLM. La lista concreta de claves vive en el repo como **`docs/bettracker2/dx/bt2_ds_input_v1_parity_fase1.md`** (el equipo la versiona en git; **este consolidado no enumera cada campo** para no duplicar cientos de líneas). Mecanismo: validador + **US-DX-003**.

**Regla de honestidad:** si no hay filas consultables para un bloque, **`available: false`** y **`diagnostics`** con causa real; **prohibido** marcar disponible con datos inventados.

### 1.3 Precedencia de lo que ve el usuario en bóveda

1. **Primero:** salida **DSR** ya pasada por Post-DSR (picks publicables o vacío con contrato de “sin pick” si aplica).  
2. **Fallback SQL / implícita:** solo si **no** hubo fallo operativo de ingesta del día **y** el conjunto DSR publicable quedó vacío **y** el **pool SQL de fallback** (mismos filtros que el pool valor: día operativo, ligas activas, cuota mínima, etc.) tiene **≥ 1** fila elegible.  
   - Selección en fallback: **mayor probabilidad implícita** = **cuota decimal más baja** entre outcomes válidos del mercado de referencia.  
   - Obligatorio: **`dsr_source` u homólogo** distinto de salida API del razonador; copy que **no** diga que es “el modelo” en el mismo tono que DSR; **disclaimer** de criterio alternativo y datos limitados cuando aplique política de cobertura baja.  
3. **Vacío duro:** el pool SQL de fallback devuelve **0** filas elegibles. **Cero** picks; mensaje operativo (no vender como señal).  
4. **Ingesta rota / CDM inútil por error de operación** (job caído, sin futuros cuando debería haberlos): **no** rellenar con fallback estadístico como si fuera día normal; vacío + **operación** (cron, revisión).

**Matiz:** si hay datos CDM utilizables pero el modelo no da señal, **sí** se permite fallback con transparencia (disclaimer), frente al caso “no hay candidatos reales”.

### 1.4 Pool (antes del LLM)

| Regla | Valor |
|--------|--------|
| Cuota mínima | **1.30** (decimal). Por debajo: no promover sin nueva decisión explícita. |
| Mercados obligatorios en pareja | **Ninguno** (no exigir 1X2 + O/U 2.5 u otro par fijo para entrar al pool). |
| Universo | Mercados **normalizados en CDM** que el mapeo canónico reconozca: 1X2, doble oportunidad (si hay líneas y coherencia), O/U goles, O/U corners, O/U tarjetas, BTTS, etc. |
| Condición de entrada | Al menos **un** mercado canónico **completo** con línea **≥ 1.30**. |
| Ligas | Conjunto prioritario del producto + `bt2_leagues.is_active`. |
| Tamaño del lote | Lo fija **ingeniería** (tokens, coste, latencia), no un tope de producto arbitrario. |

**Premium vs standard (intención cerrada):**  
- **Standard:** sensación media-alta / alta; **dirección** de producto **>70% aciertos** en ventana medida — **no** es SLA de build hasta existir numerador/denominador con **settlement** y ventana acordada.  
- **Premium:** sensación de “casi seguro” aunque la cuota sea ~1.30; reglas **más estrictas** que standard (completitud, consenso, frescura — detalle cuantitativo en implementación).  
- **Premium nunca menos estricto que standard.**

### 1.5 Post-DSR (reglas numéricas y lógicas)

- Se persiste **un pick canónico** por evento elegible; **no** el JSON del modelo tal cual.  
- **Cuota persistida:** la del **input** (consensus / CDM). Si el modelo declara cuota con **desvío > ±15%** respecto al input para ese mercado/selección → se guarda la del **input** y se deja **log / métrica** de discrepancia.  
- Si mercado o selección del modelo **no existen** en el lote enviado → **omitir** pick DSR ese evento (**sin** sustituto automático desde Post-DSR en fase vigente).  
- Si el modelo declara odds **> 15.0** para la selección → **`dsr_confidence_label`** como máximo **medium** (cap).  
- Si hay **incoherencia material** entre la selección canónica y el texto de **`razon`** → **omitir** pick; **no** reescribir `razon` en servidor por defecto.

### 1.6 Intención del modelo al elegir mercado

Entre mercados **presentes en el input**, la lectura debe privilegiar **soporte en datos e historia** contenidos en `ds_input`, **coherente con la cuota** — **no** maximizar payout ni “cuota alta” como regla suelta.  
(Lo que en documentación histórica se llama “valor relativo” se interpreta así, no como edge ciego.)

### 1.7 Etiquetas y KPIs (no mezclar)

- **`dsr_confidence_label`:** interpretación **solo** como etiqueta **atribuida al modelo** sobre el insumo recibido; **no** es “probabilidad de acierto” ni “calidad de ingesta SportMonks”.  
- **Metas PO** (>70% standard, >80% alta calidad): **dirección** hasta definición medible + instrumentación; el endpoint admin de agregados cuenta **etiquetas y fuente**, no afirma % de acierto hasta settlement.

### 1.8 Cobertura baja y degradación

- Si DSR queda vacío o insuficiente **pero** hay candidatos SQL → fallback con **mensaje** de modelo insuficiente + **disclaimer** de sesgo por datos limitados + lineage.  
- **Heurística opcional:** si eventos futuros en ventana día operativo **< 5**, flag tipo **`limited_coverage`** para copy — **no** bloquea fallback si hay filas SQL válidas.  
- **Vacío duro** sigue siendo **0** filas en el pool de fallback con los filtros del snapshot.

### 1.9 Ingesta SportMonks (hechos y reglas)

**Dos caminos de persistencia distintos:**

| Origen | Script / flujo | `include` actual en código (referencia repo) | Escribe en |
|--------|----------------|---------------------------------------------|------------|
| Atraco histórico | `scripts/bt2_atraco/sportmonks_worker.py` | `participants;odds;statistics;events;league;scores` | `raw_sportmonks_fixtures` (**INSERT … ON CONFLICT DO NOTHING** → no actualiza payload si `fixture_id` ya existe) |
| Día a día | `scripts/bt2_cdm/fetch_upcoming.py` | `participants;odds;scores;league` | `bt2_events`, `bt2_odds_snapshot`, equipos, ligas — **no** escribe `raw` |

**Lineups:** el JSON guardado en `raw` **no** contenía `lineups` en raíz porque **ningún** job listado pedía `lineups` / `formations` / `sidelined` en `include`. La API SportMonks **sí** puede devolver listas estructuradas si se añaden esos includes en la petición (verificado con fixture de prueba).  
**Hasta** US de ingesta + persistencia (**UPSERT** o tablas derivadas) + ampliación whitelist: **`processed.lineups`** se publica como **`available: false`** con **diagnostics** explícito; **no** fabricar alineaciones.

**Estadísticas / corners:** con `statistics` en el include entran agregados de equipo; **type_id 34** corresponde a **corners** en el catálogo SportMonks. Conviene **cache local** `type_id → nombre`; no depender de anidar `statistics.type` en cada request en producción.

**Pendientes de datos (para US S6.2):**  
1) Volcar **1–2** JSON completos (programado vs terminado) para diseñar mapper `statistics[]` → shape tipo `process_statistics` y exclusiones pre-partido (anti-fuga).  
2) **429** eventos con `bt2_events` pero sin fila en `raw_sportmonks_fixtures` → **backfill** o **`diagnostics.raw_fixture_missing`** en builder; no fingir raw.

### 1.10 Operación: por qué “0 picks”

Sin **cron estable** de `fetch_upcoming` / job equivalente con claves válidas, es **esperable** **0** eventos futuros en CDM y por tanto **0** picks: es fallo de **operación**, no de DSR.

**Vista admin (obligación S6.2):** pantalla solo **admin** (misma clave que otras rutas admin BT2), que para un **`operating_day_key`** muestre conteos y, para lista paginada, **un motivo único** en español por evento, por ejemplo: `sin_ingesta`, `liga_inactiva`, `estado_partido`, `fuera_ventana_dia`, `sin_cuota_minima`, `en_pool_sql`, `en_snapshot`. La lógica debe **calcar** la query real del snapshot en servidor, para no “mentir” frente a producción. Detalle de pantalla y API: nota `docs/bettracker2/notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md` y **§1.13**.  
**Refresh snapshot (obligación S6.2):** endpoint **POST** (o contrato equivalente) para refrescar snapshot **día / usuario** tras ingesta tardía, sin depender solo de cerrar/abrir sesión — ver **§1.13** para numeración US.

### 1.11 UI bóveda — preview y detalle (**Vektor**)

**Nombre en copy usuario** para el bloque de análisis: **Vektor** (no mostrar “DSR”, “razonador API”, “modelo canónico” al usuario final). **Cumplimiento y storytelling:** revisión **legal / compliance** mínima sobre el nombre **Vektor** y los claims del bloque “por qué” (sin prometer rentabilidad ni certeza); en producto, **entrada de glosario** (“Vektor — interpretación del protocolo sobre el insumo del día”) y alineación de **`GlossaryModal`** / copy — obligaciones fechadas en **`DECISIONES.md` S6.2** según **§1.13**.

**Orden fijo:**  
1) **Partido** (A vs B) — primera lectura.  
2) **Competición**.  
3) **Fecha y hora** — una sola línea coherente (tz usuario).  
4) **Mercado** en lenguaje apuesta (ej. Resultado final 1X2).  
5) **Lectura** (quién gana el pronóstico, clara).  
6) **Cuota sugerida** — **siempre visible** en bloque propio; **nunca** solo debajo del botón de acción.  
7) **Chips:** estándar / premium / programado / **partido empezado** (u equivalente).  
8) **Vektor — por qué:** en preview **máximo ~2 líneas** truncadas; en detalle **párrafo completo**.  
9) **Confianza:** una línea tipo “Confianza del modelo: Alta” — sin “simbólica”, sin % CDM, sin versión pipeline en superficie.  
10) **Acciones:** Detalle / Tomar; si evento iniciado, CTA deshabilitada **sin** párrafo largo ni referencias a IDs de decisión interna.

**Prohibido en UI usuario:** códigos internos tipo `FT_1X2 · home`, “confianza simbólica”, “Origen: API”, “Completitud CDM 12/100”, “Versión pipeline …”.

**Coherencia dura (QA):** el titular de mercado + la cuota mostrada + el texto Vektor deben describir **la misma** selección; si no, es **bug de producto/datos**, no copy.

**Fallback:** si `dsr_source` indica fallback SQL, el texto **no** debe sonar a “salida del razonador por API”.

**Wire preview (referencia de layout, no diseño visual):**

```
FC Barcelona  vs  Espanyol
La Liga
[fecha/hora una vez]

Resultado final (1X2)
Victoria local — Barcelona

Cuota sugerida  1,31

[Estándar] [Programado]

Vektor — por qué
Barcelona en racha … (máx. ~2 líneas…)

Confianza del modelo: Alta

[ Detalle ]  [ Tomar pick ]
```

**Wire detalle (referencia):** mismo bloque “partido” arriba; columna o card de **especificación** con mercado, lectura, **cuota**, riesgo/retorno si el flujo lo exige; columna **registro en protocolo** con copy mínimo y CTA; debajo **Vektor** ancho completo; opcional disclaimer corto “sobre el protocolo”.

### 1.12 Deuda técnica de datos — qué es lo mismo y qué no (SportMonks / CDM / `ds_input`)

**Objetivo único de negocio:** que `ds_input` se acerque a v1 con **datos reales en Postgres**, no placeholders.

Hay **tres cubos**; el que comentaste con includes (**lineups**, **corners**, etc.) es sobre todo el **cubo A**. Los puntos §6 sobre stats de temporada y serie de cuotas son **B** y **C** — mismo programa de trabajo “mejor insumo”, **distinta** ingesta y tablas.

| Cubo | Qué es | Relación con “includes que no están en la DB” | Cierre típico |
|------|--------|-----------------------------------------------|----------------|
| **A — Enriquecimiento por fixture (API fixture)** | Datos que vienen del **mismo** recurso fixture de SportMonks ampliando `include` y persistiendo: p. ej. **`lineups`**, **`formations`**, **`sidelined`**, **`statistics`** (ahí dentro **corners** vía **type_id 34** en filas de equipo), opcional **`lineups.details`**. Hoy: **no** se pedían esos includes en los jobs que llenan `raw` / o el diario **no** escribe `raw`; el `raw` viejo no se refresca por **DO NOTHING**. | **Sí:** es exactamente la deuda de “pedir más al API + guardar + mapear al builder + whitelist”. | US S6.2: ampliar `include`, **UPSERT** `raw` o tablas derivadas, política refresh, **mapper** `statistics[]` → `processed.*`, volcar JSON de referencia (programado vs terminado), backfill **429** sin raw, ampliar whitelist si nuevos nodos van al LLM. |
| **B — Agregados de temporada por equipo (`team_season_stats` o equivalente en contrato)** | Estadísticas **agregadas de temporada** por club (no son el array `statistics` del **partido** del fixture). Pueden requerir **otros endpoints** SM, otras tablas CDM o jobs batch; **no** se resuelven solo con “un include más en el GET del fixture del día”. | **Indirecta:** mismo objetivo (mejor `processed.*`); **no** es el mismo ticket que “meter `lineups` en el include”. | Hasta existir **tabla/fuente** y job: **`available: false`** + `diagnostics` con causa; US de ingesta **dedicada** cuando el schema exista. |
| **C — Serie temporal de cuotas** | Historial de cómo **cambia** la cuota de un mercado/selección en el tiempo (movimiento de línea). | **No** es lineups ni `statistics` del fixture; es **otra dimensión** de dato (muchas observaciones en el tiempo). | Sin schema (p. ej. `odds_history` o snapshots densos): **no** prometer en builder; US **dedicada** + índices por `event_id`/tiempo; **prohibido** full-scan en prod. |

**Regla para no mezclar US:** un PR “SportMonks includes fixture” **no** cierra solo **B** ni **C**; un PR “tabla temporada” **no** sustituye **A** si faltan lineups en el payload persistido.

### 1.13 Obligaciones normativas Sprint 6.2 (cierre de lo antes listado como “huecos”)

Lo siguiente **no** es backlog opcional de redacción: es **contrato** para US, `DECISIONES.md` y código S6.2 salvo nueva decisión explícita que **versione** este archivo.

1. **Regenerar (FSM)** — En la **US de producto** del bloque §3.A: tabla o diagrama mínimo con estados visibles para el usuario, evento **Regenerar**, transiciones permitidas y **una sola** definición de **reset** (p. ej. volver al estado previo a la última regeneración exitosa **o** “estado inicial del día operativo” — elegir **una** y documentarla). La **UI no** expone IDs internos de máquina de estados; el **backend** documenta la FSM (comentario en código o **ADR** corto enlazado desde `TASKS.md` S6.2).

2. **Prompt batch (PO/BA)** — **Sesión de lectura** sobre el artefacto versionado del prompt (alineado a `US-BE-038` / parity fase 1). Resultado en **`DECISIONES.md` S6.2**: “aprobado tal cual” o lista de cambios con fecha. Si no hay cambios respecto a la última versión aprobada: anotar explícitamente *sin cambios vs vX* para no bloquear despliegue.

3. **Vista auditoría CDM + refresh snapshot** — En **`US.md` de la carpeta `sprint-06.2`**, **dos US backend** dedicadas (numeración sin colisión con 06.1; p. ej. `US-BE-04x` / `US-BE-04y` a fijar al redactar): (a) pantalla admin según §1.10 y `docs/bettracker2/notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`; (b) **POST refresh snapshot** (contrato día/usuario o el que se cierre en esa US). Cada ruta/endpoint debe citar el **motivo único** en español ya definido en §1.10.

4. **TASKS vs código (jerarquía de verdad)** — **`docs/bettracker2/sprints/sprint-06.1/TASKS.md`** es **histórico de ejecución** del cierre 06.1. La especificación viva del producto es **§1–§3 y §1.13 de este archivo** más el **código en la rama acordada** (`main` o release). Las casillas nuevas de trabajo viven en **`TASKS.md` S6.2**. *Opcional sin cambiar esta jerarquía:* si auditoría interna lo exige, pasada **TASKS 06.1 vs código** con etiquetas `[hecho]` / `[difiere — ver código]` y enlace a PR o archivo.

5. **Cubo C — serie temporal de cuotas** — **US dedicada** + schema explícito (p. ej. `bt2_odds_history` **o** política de snapshots con granularidad y retención). **Índices** por `event_id` + tiempo (y claves de mercado/selección según modelo canónico). El **builder** solo lee **rangos acotados**; **prohibido** full-scan en producción. Hasta existir tabla y job: **no** enviar ese bloque al LLM **o** `available: false` + `diagnostics`.

6. **Cubo B — `team_season_stats` (u homólogo)** — **`available: false`** + **`diagnostics`** con causa real hasta existir **fuente consultable** (tabla CDM y/o job contra endpoint/agregación de **temporada/equipo**, no sustituible por includes solo del fixture del día). **US separada** del cubo A; en diseño, documentar **qué endpoint o agregación** alimenta el bloque (distinto de `statistics[]` del partido).

7. **Marca Vektor** — Revisión **legal / compliance** y límites de claims según §1.11; **glosario** y **`GlossaryModal`** alineados a esa definición; dejar constancia en **`DECISIONES.md` S6.2** cuando PO/legal cierren texto.

---

## 2. US Sprint 6.1 — qué pedía cada una (una línea)

| ID | Pedido |
|----|--------|
| US-DX-003 | Whitelist + validador anti-fuga + meta `contractVersion` + OpenAPI/ts para campos que ve el cliente |
| US-BE-032 | Builder `ds_input` desde CDM según whitelist |
| US-BE-033 | Pool: ligas, 1.30, mercados desde CDM, premium más estricto |
| US-BE-034 | Post-DSR y pick canónico persistido |
| US-BE-036 | Orquestación DSR → fallback → vacío duro + flags API |
| US-BE-035 | Admin: agregados por día (etiquetas, fuente, score si existe) |
| US-FE-055 | Copy que separa semánticas; vacío operativo vs sin señal |
| US-BE-037 | Builder: histórico duelo, stats, lineups si hay datos reales |
| US-BE-038 | Prompt batch alineado a §1.6 |
| US-BE-039 | Post-DSR: contradicción selección vs texto → omitir |
| US-FE-056 | Copy alineado a §1.6 |

---

## 3. Plan de acción Sprint 6.2 (orden lógico)

Las obligaciones que antes figuraban como “consultas” están **cerradas en §1.13**; este apartado es el **orden de trabajo**, no redefine reglas.

**A. Producto** — Decisión + US: snapshot **global** (~20/día), **5 tomables**/día, slate **5**, **Regenerar** con FSM según **§1.13.1**, franjas 06:00–11:59 / 12:00–17:59 / 18:00–23:59, madrugada fuera de alcance, job nocturno vs disparo por `session/open` por usuario, modelo de datos/API.  
**B. UX** — US-FE + criterios QA para §1.11 en `PickCard` y settlement; glosario Vektor **§1.13.7**.  
**C. Datos** — Cubo **A** §1.12: `include` ampliado, UPSERT `raw` o tablas derivadas, mapper `statistics`/lineups, 429 sin raw; cubos **B** y **C** según **§1.13.5–6**.  
**D. DX** — Ampliar whitelist si nuevos caminos al LLM.  
**E. Pipeline** — Refactor cuando A esté escrito: pool global + vista por usuario.  
**F. Admin** — **§1.13.3**: vista auditoría CDM + POST refresh snapshot; enlazar runbooks.  
**G. Documentación** — `DECISIONES.md` / `US.md` / `TASKS.md` en `sprint-06.2` (**§1.13.2, .3, .4**); prompt batch y legal Vektor con fecha en `DECISIONES.md`; **este archivo** se versiona con fecha al cambiar reglas.

---

## 4. Registro de IDs de decisión (solo etiqueta; el texto normativo es §1 y §1.13)

Los IDs **D-06-021** … **D-06-030** y **D-06-020** (puente S6) son las **etiquetas** bajo las cuales se aprobó lo resumido en §1; sirven para commits, comentarios de código y auditoría legal, **no** para volver a leer otros markdown como fuente de verdad. Las **obligaciones de cierre S6.2** no llevan ID D-06-* en este archivo: están en **§1.13** y en actas futuras de `DECISIONES.md` S6.2.

---

## 5. Archivo histórico (extracción)

El contenido normativo de este archivo se extrajo y unificó a partir de: plan y decisiones S6.1, objetivo señal, refinement, US/TASKS, ejecución, auditoría raw SportMonks, hallazgo SM, mapa v1, nota vista admin CDM, incremento 06.1/06.2, `DSR_V1_FLUJO`, whitelist DX. **No** es necesario abrirlos para definir nuevas US si **§1–§3** y **§1.13** están actualizados.

---

## 6. Estado del consolidado (¿hay huecos de descripción?)

**Especificación de producto y reglas en este archivo:** **cerrada** para el alcance acordado (incluye obligaciones S6.2 en **§1.13**). No quedan ítems en este markdown del tipo “definición pendiente” o “elegir entre dos modelos sin decisión”: la jerarquía **TASKS 06.1 vs spec** quedó fijada en **§1.13.4** (histórico + spec viva + código; opcional auditoría de casillas sin sustituir esa jerarquía).

**Lo que sigue siendo trabajo (no es laguna del doc):** redactar e implementar **US** S6.2, **migraciones**, **jobs**, **código**, y **actas fechadas** en `DECISIONES.md` (prompt §1.13.2, legal Vektor §1.13.7). Hasta que eso exista en repo/prod, el **producto** no está “hecho”; el **texto normativo** de este consolidado puede considerarse **completo** para arrancar S6.2.

---

*Al cambiar una regla de §1–§3 o §1.13, incrementar la fecha en la cabecera.*
