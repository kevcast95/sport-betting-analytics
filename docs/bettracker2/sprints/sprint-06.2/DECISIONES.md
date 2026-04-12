# Sprint 06.2 — DECISIONES

> **Jerarquía:** reglas normativas en [`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](./FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md) (§1–§3, §1.12, §1.13). Inventario ejecutable en [`INVENTARIO_TECNICO_S6_2.md`](./INVENTARIO_TECNICO_S6_2.md).  
> **Sprint anterior:** [`../sprint-06.1/DECISIONES.md`](../sprint-06.1/DECISIONES.md) **D-06-021** … **D-06-030** siguen vigentes salvo contradicción explícita aquí.  
> **Convención alcance:** **D-06-023** (cambio en código → nueva US / decisión antes de merge).

---

## D-06-031 — Jerarquía de verdad: TASKS 06.1 histórico (2026-04-11)

**Contexto:** §1.13.4 del consolidado S6.2.

**Decisión:**

1. **`docs/bettracker2/sprints/sprint-06.1/TASKS.md`** es **histórico de ejecución** del cierre 06.1; no se exige que cada casilla refleje línea a línea el código actual salvo auditoría opcional (**T-221**).
2. La especificación viva del producto para S6.2 es **`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`** + **`INVENTARIO_TECNICO_S6_2.md`** + **código en la rama de release acordada**.
3. El trabajo nuevo se rastrea en **`TASKS.md` de esta carpeta** (S6.2).

**Trazabilidad:** US implícita en gobernanza — **TASKS S6.2**; acta kickoff puede citar esta decisión.

---

## D-06-032 — Parámetros snapshot bóveda S6.2 (2026-04-11)

**Contexto:** §3.A consolidado; inventario §3.4 P1–P2.

**Decisión de producto (referencia normativa — números cerrados salvo enmienda explícita con fecha):**

1. **Universo / tope de candidatos del día:** **20** eventos en el cómputo que alimenta la bóveda para ese día operativo (consolidado “~20”; aquí se fija **20** como decisión. Si el código usa una constante con otro nombre, debe coincidir con **20** salvo **enmienda** de este apartado).
2. **Tomables:** **5** por **usuario** y **día operativo** (lo que settlement y persistencia cuenten como “pick tomado”; BE/FE alineados a esta cifra).
3. **Slate visible:** **5** picks en la vista principal del día.
4. **Franjas (TZ usuario):** actividad normal de generación/visualización acordada en **06:00–11:59**, **12:00–17:59**, **18:00–23:59**. **00:00–05:59:** fuera de alcance del flujo normal; UX según **US-FE-057** / **US-BE-044**, sin violar **D-06-022** (no disfrazar ingesta rota).
5. Cambiar **20**, **5** o franjas → **editar este bloque con fecha** (no solo comentario en PR).

**Trazabilidad:** **US-BE-044**, **T-209–T-211**.

---

## D-06-033 — Disparo del snapshot: job, sesión y refresh (2026-04-11)

**Contexto:** §3.A consolidado (“job nocturno vs `session/open`”).

**Política cerrada:** qué hace cada disparador. Los **horarios UTC**, **env** e **idempotencia** se documentan en **US-BE-044** / **US-BE-047** y en código; **aquí** solo se fija la regla de negocio para evitar ambigüedad futura.

1. **Job programado (cron / worker) — obligatorio:** al menos una ejecución programada que arme o actualice pool/snapshot con CDM fresco. El sistema **no** puede depender solo de que el usuario abra la app.
2. **POST refresh snapshot — obligatorio en S6.2** (**US-BE-047**): permite forzar recomputo tras ingesta tardía u operación; **no** sustituye el criterio de **D-06-022** (fallo de ingesta no se normaliza como día sano).
3. **Apertura de sesión (`session/open` u homólogo) — opcional como complemento:** si se implementa, solo para **obtener snapshot cuando aún no exista** uno válido para el `operating_day_key` del usuario y dentro de **D-06-032**. **No** reemplaza el job (1). No invalidar un snapshot ya válido solo por abrir la app, salvo **Regenerar** (**D-06-034**) o refresh (2).
4. Ante conflicto con **D-06-022** / **D-06-025**, prevalecen esas decisiones.

**Trazabilidad:** **US-BE-044**, **US-BE-047**, **T-209–T-211**, **T-215**.

---

## D-06-034 — Regenerar: máquina de estados (FSM) y reset (2026-04-11)

**Contexto:** §1.13.1 consolidado.

**¿Qué es FSM?** **FSM** (*finite state machine*) = **máquina de estados**. En este contexto **no** es jerga vacía: es la definición explícita de **en qué “situation” puede estar** el flujo de bóveda/snapshot para un usuario (ej.: aún no hay snapshot, snapshot listado, regeneración en curso, error operativo) y **qué transiciones están permitidas** al usar **Regenerar**. El servidor **valida** esas transiciones; el usuario ve solo **copy de producto**, no códigos internos.

**Decisión:**

1. **Regenerar** es obligatorio en S6.2: documentar la máquina en **US-BE-045** (tabla o diagrama) + **ADR** o enlace en **`TASKS.md`** (**T-213**).
2. **Una sola regla de reset** al regenerar (elegir **una** y reflejarla en acta antes del merge final de **US-BE-045**):
   - **(a)** Volver al estado **justo antes** de la última regeneración **exitosa** (deshacer un solo regenerar).
   - **(b)** Volver al **estado inicial del día operativo** para ese usuario (como si no se hubiera regenerado ese día).
3. La **UI no** muestra IDs internos de estados.

**Acta (obligatoria antes de cierre US-BE-045):**

- [a] Opción **(a)** o **(b)** — responsable: BA — fecha: 11-04-2026

**Trazabilidad:** **US-BE-045**, **T-212–T-213**.

---

## D-06-035 — Aprobación del texto del prompt batch (2026-04-11)

**Contexto:** §1.13.2 consolidado; continuidad **US-BE-038** / **D-06-027** … **D-06-030**.

**Decisión:**

1. **Sesión de lectura PO/BA** sobre el artefacto versionado del prompt (p. ej. `bt2_dsr_deepseek.py` / anexo en repo).
2. Resultado obligatorio en **esta sección (acta)** o anexo fechado enlazado desde aquí:
   - **Aprobado tal cual**, o
   - **Lista de cambios** con fecha y PR, o
   - **Sin cambios vs vX** (texto idéntico a versión ya aprobada).

**Acta (rellenar al cierre del trámite):** hasta que **fecha** y **responsable** estén completos, la acta **no** cuenta como cerrada (aunque el prompt ya esté aprobado en código).

- [x] Estado: `aprobado` (alternativas: `cambios` + enlace PR / `sin cambios vs vX`)
- [ ] Fecha: 11-04-2026
- [ ] Responsable PO/BA: BA

**Trazabilidad:** **T-224** (prompt + acta).

---

## D-06-036 — Vektor: legal, claims y glosario (2026-04-11)

**Contexto:** §1.11 y §1.13.7 consolidado.

**Decisión (cerrada para S6.2 — sustituye actas abiertas):**

1. **Límites legales / copy:** el nombre **Vektor** y el bloque “por qué” en bóveda **no** prometen rentabilidad, resultado deportivo ni certeza. La **confianza** mostrada es **atribución al modelo** sobre el insumo recibido (**§1.7** / **D-06-020**), no “probabilidad de acierto”.
2. **Texto canónico del glosario (fuente única para US-FE-058):** el párrafo siguiente es el que debe aparecer en **`GlossaryModal`** y puede resumirse en tooltips; cualquier cambio de redacción sustancial requiere **enmienda** de esta D con fecha.

**Texto glosario aprobado (Vektor):**

> **Vektor** es el nombre del bloque que explica *por qué* el protocolo sugiere una lectura concreta en la Bóveda. Resume la interpretación sobre el **insumo del día** (datos y cuotas disponibles para ese partido). La línea de confianza describe la postura del modelo respecto a ese insumo, **no** garantiza un resultado deportivo ni juzga la calidad de la ingesta. No constituye asesoría financiera ni promesa de ganancia.

3. **Implementación en repo:** la entrada vive en `apps/web/src/components/GlossaryModal.tsx` (arreglo `GLOSSARY`, término `Vektor`). **US-FE-058** se da por satisfecha en glosario cuando ese texto (o enmienda explícita de esta D) está desplegado; **US-FE-057** debe usar la misma semántica en superficie (sin contradecir el párrafo).

**Acta (cerrada):**

- [x] Revisión documental / límites de claims acordados para build S6.2 — **fecha:** 2026-04-11 — **responsable:** Producto (cierre **D-06-036** en repo)
- [x] Texto glosario: incrustado arriba + `GlossaryModal.tsx` (misma redacción)

**Trazabilidad:** **US-FE-057**, **US-FE-058**.

---

## D-06-037 — Ingesta SportMonks cubo A: includes y persistencia `raw` (2026-04-11)

**Contexto:** §1.9, §1.12-A consolidado.

**Decisión:**

1. Ampliar **`include`** en jobs que alimentan fixture (**lineups**, **formations**, **sidelined**, **statistics** según diseño técnico) para cerrar brecha vs v1.
2. Sustituir o complementar **`INSERT … ON CONFLICT DO NOTHING`** en `raw_sportmonks_fixtures` por política que permita **payload fresco** (**UPSERT** o job de refresh explícito documentado en **US-BE-040**).
3. **`fetch_upcoming`** (o sucesor) debe quedar alineado con la misma política de includes o justificar divergencia en **TASKS** (p. ej. solo `raw` vía job separado).

**Trazabilidad:** **US-BE-040**, **T-197–T-200**.

---

## D-06-038 — Cubo B: `team_season_stats` sin fuente hasta job dedicado (2026-04-11)

**Contexto:** §1.12-B, §1.13.6.

**Decisión:**

1. Mientras **no** exista tabla/fuente consultable de agregados de **temporada por equipo**, el builder publica **`available: false`** + **`diagnostics`** con causa real.
2. **No** se mezcla con el PR del cubo A sin decisión explícita y **US-BE-043** (o enmienda).
3. Si en S6.2 se implementa fuente, el **endpoint/agregación SM** queda documentado en **US-BE-043** y acta aquí.

**Trazabilidad:** **US-BE-043**, **T-208**.

---

## D-06-039 — Cubo C: serie temporal de cuotas (2026-04-11)

**Contexto:** §1.12-C, §1.13.5.

**Decisión:**

1. **Schema explícito** (p. ej. `bt2_odds_history` o política de snapshots con retención) + **índices** por `event_id` + tiempo + claves de mercado/selección canónicas.
2. El builder **solo** consulta **rangos acotados**; **prohibido** full-scan en producción.
3. Hasta existir tabla y job: bloque **no** al LLM o **`available: false`** + diagnostics.

**Trazabilidad:** **US-BE-042**, **T-205–T-207**.

---

## D-06-040 — Admin auditoría CDM: motivos = semántica del snapshot (2026-04-11)

**Contexto:** §1.10, nota [`../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`](../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md).

**Decisión:**

1. Los **motivos únicos** en español devueltos por la API (**US-BE-046**) deben **calcar** la lógica real de exclusión usada al armar el pool/snapshot (mismos predicados que en servidor, no copy aspiracional).
2. Conjunto mínimo de códigos alineado a §1.10: `sin_ingesta`, `liga_inactiva`, `estado_partido`, `fuera_ventana_dia`, `sin_cuota_minima`, `en_pool_sql`, `en_snapshot` (ampliaciones solo con decisión y bump doc).

**Trazabilidad:** **US-BE-046**, **US-FE-059**, **T-214**, **T-219**.

---

## D-06-041 — Disclaimer Vektor en Bóveda (zona superior + detalle de pick) (2026-04-11)

**Contexto:** **D-06-036** fija el texto del **glosario**; el producto exige además un **aviso visible** en la experiencia de Bóveda para que el usuario no interprete la señal como garantía (**§1.11**, **§1.7**).

**Decisión:**

1. Debe mostrarse un **mismo disclaimer** (misma semántica que **D-06-036**) en **dos** sitios:
   - **Vista Bóveda (lista / feed):** en la **parte superior** del contenido de bóveda (encima del listado de picks o equivalente), siempre visible al entrar a la vista (sin depender de abrir el glosario).
   - **Detalle de cada pick:** en la **vista detalle** de ese pick (modal o pantalla dedicada), de forma **persistente** en el flujo de lectura (p. ej. bajo el bloque Vektor o en pie de sección — el layout lo define **US-FE-060**, no esta D).
2. **Texto corto aprobado para superficie** (puede tipografía secundaria / menor contraste, pero **legible**):

   > Vektor resume la lectura del protocolo sobre los datos del día; **no garantiza** el resultado del partido **ni** constituye asesoría financiera.

3. Si legal/PO acortan o alargan el texto, **enmendar este apartado con fecha**; **GlossaryModal** sigue pudiendo usar el párrafo largo de **D-06-036**.
4. **No** sustituye términos de servicio ni avisos legales globales del producto; es **capa UX** de expectativas en Bóveda.

**Trazabilidad:** **US-FE-060**, **T-226**; coherencia con **US-FE-057**.

---

*Creación: 2026-04-11 — S6.2 kit ejecución. Actas pendientes: **D-06-034** (opción reset FSM), **D-06-035** (fecha + responsable PO/BA). **D-06-036** cerrada con texto canónico + `GlossaryModal.tsx`. **D-06-041** disclaimer superficie → **US-FE-060**.*
