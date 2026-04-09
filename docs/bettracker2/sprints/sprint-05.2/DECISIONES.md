# Sprint 05.2 — DECISIONES

> **Sprint:** bóveda **franjas + cupo + post–kickoff** (**RFB-05**, **RFB-06**).  
> **Refinement:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md).

---

## D-05.2-001 — RFB-05: política después del kickoff

**Contexto:** ¿Bloqueo **en el instante** `kickoffUtc` o **ventana de gracia** (minutos) **en servidor**?

**Estado:** *Implementación en código con **opción A** (estricto, sin gracia). **Ratificación formal PO** sigue siendo requisito de merge/cierre **T-190** / **T-195**.*

**Opciones** (resumen del refinement):

| Código | Descripción |
|--------|-------------|
| **A** | Estricto al kickoff: `isAvailable` y `POST /bt2/picks` alineados a **sin** toma tras inicio (salvo reglas de mercado ya existentes). |
| **C** | Ventana en BE: parámetro **`graceMinutes`** (constante o config) aplicado al calcular disponibilidad y en validación del POST. |

**Propuesta backlog (default si PO no objeta):** **A** — cero gracia; coherencia inmediata con **`kickoffUtc`** ya expuesto (**US-BE-019**). Si se elige **C**, documentar aquí el valor numérico y actualizar tests/OpenAPI.

**Anti-patrón:** ventana **solo en FE** sin alinear POST (riesgo 422 y pérdida de confianza).

---

## D-05.2-002 — RFB-06: franjas, mezcla, cupo y pool diario

**Contexto:** El PO pidió sensación de **franjas del día**, **switcher** sin inflar cupo, y **límite diario 3 estándar + 2 premium = 5** tomas.

**Decisión (producto — alineada al borrador refinement 2026-04-08):**

1. **Franjas** en **TZ del usuario** (`userTimeZone` u homólogo en contrato BT2): **Mañana** 08:00–12:00, **Tarde** 12:00–18:00, **Noche** 18:00–23:00. Límites **12:00** y **18:00**: criterio de inclusión en franja (inclusivo/exclusivo) documentado en OpenAPI y tests.
2. **Hueco 23:00–08:00:** *Pendiente PO* — opciones: (a) solo **relleno** desde franja más cercana sin nombre propio; (b) cuarta franja; (c) extensión de Noche. **En código (T-188):** esos kickoffs se etiquetan **`timeBand` = `overnight`** hasta nueva decisión PO.
3. **Vista por defecto:** **mezcla** priorizando picks cuya franja local está **más cercana al instante actual**.
4. **Switcher:** **mezcla** \| **mañana** \| **tarde** \| **noche** — **filtro de presentación** sobre el **mismo** payload del día; **no** dispara cupo ni exige nuevo GET por cambiar filtro.
5. **Cupo diario:** techo **3** tomas estándar + **2** premium por **día operativo**; el FE muestra **restantes** coherentes con ledger/sesión ya existentes (**alinear** con **US-FE-040** / **US-BE-029** sobre si **unlock premium** consume cupo premium sin tomar — gap explícito en refinement; **cerrar sub-bullet** en implementación o dejar copy honesto “según reglas actuales”).
6. **Pool servidor — “los ~15 picks” del PO:** en **`GET /bt2/vault/picks`** el objetivo de negocio es devolver **≈15 candidatos** por día operativo cuando el CDM tenga stock suficiente (**target operativo = 15**; no es cupo de toma: el cupo sigue siendo **3 std + 2 prem**). Si hay menos eventos disponibles, devolver **todos los válidos** y documentar en respuesta/meta que el pool está **por debajo del target**. **Tope duro** de payload p. ej. **20** ítems (ajustar en PR si PO/ingeniería lo exigen). Composición: **sesgar** hacia **~3 std + ~2 prem por franja** cuando haya stock; si falta en una franja, **rellenar** desde la franja **más cercana** por `kickoffUtc` local.
7. **Campo opcional en contrato vault:** cada ítem puede incluir **`timeBand`**: `morning` \| `afternoon` \| `evening` \| `mixed` \| `overnight` (si se usa) — derivado en servidor desde `kickoffUtc` + TZ usuario.

**Gaps a cerrar en DoD de **T-188** / revisión PO:** (a) hueco nocturno; (b) unlock premium vs cupo; (c) confirmar **target 15** vs tope **20** en entorno real (latencia/payload).

---

## D-05.2-003 — Refresh del mismo día operativo *(opcional / diferido)*

**Decisión:** Por defecto **fuera de 05.2**. Un **`POST /bt2/vault/refresh`** o GET no idempotente que **regenera** candidatos implica coste CDM, fairness e idempotencia — spike o **Sprint 06+**. Si PO exige botón “Actualizar bóveda” en 05.2, añadir tarea explícita en [`TASKS.md`](./TASKS.md) y ampliar esta decisión.

---

*Última actualización: 2026-04-09.*
