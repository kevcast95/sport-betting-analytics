# Sprint 06.2 — TASKS

> **Sprint cerrado (2026-04-09):** acta única **[`CIERRE_S6_2.md`](./CIERRE_S6_2.md)** + **D-06-042**. Trabajo nuevo: **[`../sprint-06.3/PLAN.md`](../sprint-06.3/PLAN.md)**.  
> **Numeración:** continúa desde **T-194** (S6.1). Rango S6.2: **T-195** … **T-226**.  
> **S6.1 histórico:** [`../sprint-06.1/TASKS.md`](../sprint-06.1/TASKS.md) — **D-06-031**.  
> **US:** [`US.md`](./US.md). **Decisiones:** [`DECISIONES.md`](./DECISIONES.md). **Handoff:** [`HANDOFF_EJECUCION_S6_2.md`](./HANDOFF_EJECUCION_S6_2.md) — **§0** cierre (DSR integrado > v1), **§3** P0/P1/P2, **§6** diferidos.  
> **Modo de trabajo:** **D-06-023** — definición completa antes de merge; alcance = **inventario** + **consolidado**.

---

## Apto 100% para ejecución (Definition of Ready)

| ✓ | Qué se confirma | Quién (típico) |
|---|-----------------|----------------|
| [ ] | [`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](./FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md) §1.13 leído; **D-06-031** … **D-06-041** enlazadas al diseño de PRs. | TL / PO |
| [ ] | [`INVENTARIO_TECNICO_S6_2.md`](./INVENTARIO_TECNICO_S6_2.md) §3: cada fila tiene US asignada (matriz en **US.md**). | TL |
| [ ] | **D-06-034** acta kickoff: opción reset Regenerar **(a)/(b)** marcada antes de merge **US-BE-045**. | PO |
| [ ] | **D-06-035:** completar **fecha** + **responsable** en acta (estado “aprobado” solo no basta). **D-06-036** y **D-06-041:** cerradas en repo; revisión legal externa sigue siendo responsabilidad del negocio. | PO / Legal |

---

## Checklist de cobertura inventario §3 (no omitir filas)

| Clave inventario | US | Tareas |
|------------------|-----|--------|
| D1–D2, D5, JSON ref | US-BE-040 | T-197–T-200 |
| D3–D4, B1 | US-BE-041, US-DX-004 | T-195–T-196, T-201–T-204 |
| D7 | US-BE-042 | T-205–T-207 |
| D6 | US-BE-043 | T-208 |
| P1–P3 | US-BE-044 | T-209–T-211 |
| P4, B7 | US-BE-045 | T-212–T-213 |
| B6 | US-BE-046 | T-214 |
| B5 | US-BE-047 | T-215 |
| E1 | US-BE-048 | T-216 |
| X1 | US-DX-004 | T-195–T-196 |
| F1, F4 | US-FE-057 | T-217 |
| F2, F3 | US-FE-058 | T-218 |
| Admin UI | US-FE-059 | T-219 |
| Disclaimer Bóveda (**D-06-041**) | US-FE-060 | T-226 |
| G1 | Acta D-06-035 | T-224 |
| G2 | **D-06-036** cerrada | Entrada Vektor en `GlossaryModal.tsx` + **T-218** (fallback copy, etc.) |
| G4 | Runbooks | T-220 |
| G5 opcional | — | T-221 |
| B2–B4 regresión | — | T-223 |

---

## US-DX-004

- [x] **T-195** (US-DX-004) — Actualizar **`bt2_ds_input_v1_parity_fase1.md`** con claves nuevas acordadas (cubo A / cubo C); PR con revisión PO/DX.
- [x] **T-196** (US-DX-004) — Validador anti-fuga + bump **`contractVersion`** + OpenAPI + **`bt2Types.ts`** para campos nuevos expuestos al cliente.

---

## US-BE-040

- [x] **T-197** (US-BE-040) — Ampliar **`include`** SportMonks en `sportmonks_worker.py` / `fetch_upcoming.py` (y aliados); alinear con **D-06-037**.
- [x] **T-198** (US-BE-040) — **UPSERT** `raw_sportmonks_fixtures` o política de refresh documentada; eliminar congelamiento silencioso **DO NOTHING** donde aplique.
- [x] **T-199** (US-BE-040) — Artefacto **type_id → nombre** (JSON/tabla estática en repo o DB) consumible por mapper/job.
- [x] **T-200** (US-BE-040) — Volcar **1–2 JSON** referencia (programado vs terminado) en `docs/bettracker2/sprints/sprint-06.2/refs/` (o ruta acordada); enlazar desde **US-BE-041** / handoff.

---

## US-BE-041

- [x] **T-201** (US-BE-041) — Mapper **`statistics[]`** → `processed.*` con exclusiones pre-partido y anti-fuga.
- [x] **T-202** (US-BE-041) — **Lineups** desde `raw` cuando existan datos reales; si no, `available: false` + diagnostics.
- [x] **T-203** (US-BE-041) — **`diagnostics.raw_fixture_missing`** (o homólogo) para gap **429** / sin fila raw; tests.
- [x] **T-204** (US-BE-041) — Tests unitarios/integración builder con fixtures **T-200**.

---

## US-BE-042

- [ ] **T-205** (US-BE-042) — Migración **schema** historial cuotas + **índices** (**D-06-039**).
- [ ] **T-206** (US-BE-042) — Job o política de **ingesta** de puntos de cuota en el tiempo.
- [ ] **T-207** (US-BE-042) — Builder: lectura **por rango acotado**; prohibir full-scan; integración whitelist **T-195–T-196**.

---

## US-BE-043

- [x] **T-208** (US-BE-043) — **Mínimo:** diagnostics + documentación fuente temporada en PR y **D-06-038** acta; **opcional:** tabla+job si kickoff lo incluye.

---

## US-BE-044

- [x] **T-209** (US-BE-044) — Implementar límites snapshot **~20 / 5 tomables / slate 5** (**D-06-032**) en modelo/API.
- [x] **T-210** (US-BE-044) — Franjas **06–12 / 12–18 / 18–24** TZ usuario; **madrugada fuera** de promoción normal.
- [x] **T-211** (US-BE-044) — **Job nocturno** y/o integración **`session/open`** según **D-06-033**; coordinar con **US-BE-047**.

---

## US-BE-045

- [ ] **T-212** (US-BE-045) — Implementar **FSM Regenerar** + persistencia; documentar diagrama en US/anexo.
- [ ] **T-213** (US-BE-045) — **ADR** o comentario enlazado desde este **TASKS**; API sin filtrar IDs crudos de máquina a UI.

---

## US-BE-046

- [ ] **T-214** (US-BE-046) — Endpoint admin **auditoría CDM**; motivos **D-06-040**; OpenAPI; tests coherencia SQL ↔ motivo.

---

## US-BE-047

- [ ] **T-215** (US-BE-047) — **POST refresh snapshot**; idempotencia; auth admin; tests.

---

## US-BE-048

- [ ] **T-216** (US-BE-048) — Refactor **pool global + vista por usuario** tras **US-BE-044** estable.

---

## US-FE-057

- [x] **T-217** (US-FE-057) — UI bóveda **§1.11** (Vektor, orden, cuota, chips, confianza); **settlement** coherente; sin fugas de IDs internos.

---

## US-FE-058

- [x] **T-218** (US-FE-058) — Revisar entrada **Vektor** en `GlossaryModal.tsx` vs **D-06-036**; completar copy **fallback** / vacío / cobertura baja (**§1.3**, **§1.8**).

---

## US-FE-059

- [x] **T-219** (US-FE-059) — Pantalla admin: lista auditoría (**T-214**) + acción refresh (**T-215**); auth admin existente.

---

## US-FE-060

- [x] **T-226** (US-FE-060) — Disclaimer **D-06-041**: bloque arriba en vista Bóveda + mismo texto en **detalle** de pick; copy literal de **DECISIONES**; coherente con **US-FE-057**.

---

## Gobernanza y documentación

- [ ] **T-220** (S6.2) — Runbooks: enlazar en **DECISIONES** o `docs/bettracker2/runbooks/` cron `fetch_upcoming`, revisión **0 picks**, uso vista admin (nota VISTA_AUDITORIA).
- [ ] **T-221** (S6.2, **opcional**, **G5**) — Pasada **TASKS 06.1 vs código** con etiquetas `[hecho]` / `[difiere]` sin sustituir **D-06-031**.
- [ ] **T-224** (S6.2, **D-06-035**) — Sesión PO/BA prompt batch; completar acta en **DECISIONES.md**; si solo ajuste texto, PR en `bt2_dsr_deepseek.py` alineado a acta.
- [ ] **T-223** (S6.2 transversal) — **Regresión** pool + orquestación + Post-DSR (**§1.3–§1.5**) con snapshot **US-BE-044** integrado; documentar en **EJECUCION.md** cuando exista.

---

## Cierre transversal S6.2

- [x] **T-225** (S6.2) — `pytest` módulos BT2 tocados + `npm test` + `npm run build` en `apps/web`; checklist **US.md** DoD por US en alcance (incl. **US-FE-060** si está en alcance del sprint).

---

## Check cierre Sprint 06.2

- [x] **Cierre formal** — [`CIERRE_S6_2.md`](./CIERRE_S6_2.md) + **D-06-042** (2026-04-09). Ítems no cerrados → **S6.3** según acta.
- [ ] Todas las filas del **checklist inventario** arriba tienen tareas marcadas según alcance kickoff (si algo se difiere, **DECISIONES** enmienda + tachar fila en inventario) — *higiene opcional en S6.3*.
- [ ] **D-06-034** acta (reset FSM) — *pendiente / S6.3 si aplica*. **D-06-035** fecha + responsable — *pendiente / S6.3*. **D-06-036** / **D-06-041:** texto cerrado en **DECISIONES**; **US-FE-058** / **US-FE-060** verificadas en código al cierre si están en alcance.
- [x] **T-225** referenciado en entrega (ver **EJECUCION.md** / acta cierre).

---

*Creación: 2026-04-11 — trazabilidad completa vs `INVENTARIO_TECNICO_S6_2.md` §3.*
