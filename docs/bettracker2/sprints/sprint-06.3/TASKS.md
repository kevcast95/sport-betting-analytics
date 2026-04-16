# Sprint 06.3 — TASKS

> Sprint en definición / ejecución inicial (2026-04-14): bajar Fase 1 a backlog ejecutable tras cierre de Fase 0.
> Numeración: continúa desde T-226 (S6.2). Rango propuesto S6.3: T-227 … T-245.
> S6.2 histórico: ../sprint-06.2/TASKS.md.
> US: US.md. Decisiones: DECISIONES.md. Backlog maestro del sprint: PLAN.md.
> Modo de trabajo: D-06-023 — definición completa antes de merge; foco S6.3 = verdad oficial + cierre de loop + elegibilidad reproducible + lectura admin mínima.

**Orden de ejecución BE (fuente viva):** [`HANDOFF_BE_EJECUCION_S6_3.md`](./HANDOFF_BE_EJECUCION_S6_3.md) — incluye §0 acta técnica (**T-244** primero), secuencia T-227…T-245, PRs sugeridos y reglas duras.

* * *

## Apto 100% para ejecución (Definition of Ready)

✓ Qué se confirma | Quién (típico)

- [ ] `ROADMAP_PO_NORTE_Y_FASES.md`, `PLAN.md` y `CIERRE_FASE_0_MODELO_Y_METRICA_DATOS.md` leídos; el equipo entiende que Fase 1 **no** depende de liquidación del usuario. | TL / PO
- [ ] `DECISIONES.md` S6.3 aprobado al menos en D-06-043 … D-06-049 antes de abrir PRs de implementación. | PO / TL
- [ ] `US.md` S6.3 congelado para este corte mínimo: US-BE-049 … US-BE-052 y US-FE-061. | PO
- [ ] Kickoff técnico confirma subconjunto inicial de mercados soportados para evaluación oficial v1 y cómo se mapearán a verdad oficial. | TL / BE
- [ ] Se acuerda dónde vive la fuente oficial consumida en backend (adapter, tabla raw, servicio o combinación mínima) antes de merge de US-BE-050. | TL / BE

* * *

## Checklist de cobertura Fase 1 (no omitir capas)

Capa / decisión | US | Tareas
--- | --- | ---
Verdad oficial del modelo (D-06-043) | US-BE-049, US-BE-050, US-FE-061 | T-227–T-234, T-238–T-243
Unidad base = pick sugerido (D-06-044) | US-BE-049, US-BE-050, US-FE-061 | T-227–T-234, T-239, T-241–T-243
Elegibilidad v1 del pool (D-06-045) | US-BE-051 | T-235–T-237
Auditoría persistida de elegibilidad (D-06-046) | US-BE-051, US-BE-052, US-FE-061 | T-236–T-240, T-241–T-243
Cierre de loop obligatorio (D-06-047) | US-BE-049, US-BE-050, US-FE-061 | T-227–T-234, T-241–T-243
Salida admin/reporte mínimo (D-06-048) | US-BE-052, US-FE-061 | T-238–T-243
Gobernanza / runbook / cierre técnico | transversal | T-244–T-245

* * *

## US-BE-049

- [x] **T-227 (US-BE-049)** — Crear migración/schema y modelo persistido de evaluación por pick con claves mínimas: `pick_id`, `event_id`, `market_key` o equivalente canónico, `selection_key`, `confidence` si aplica, `suggested_at`, `evaluated_at`, `evaluation_status`, `truth_source`, `truth_payload_ref` o equivalente.
- [x] **T-228 (US-BE-049)** — Implementar catálogo/enum de estados según **ACTA T-244** / **D-06-050**: `pending_result`, `evaluated_hit`, `evaluated_miss`, `void`, `no_evaluable` (mismos literales en DB, jobs, métricas, admin); prohibir valores ambiguos y aliases.
- [x] **T-229 (US-BE-049)** — Implementar resolver canónico de mapeo pick → verdad oficial para el subconjunto inicial de mercados acordados; si no hay mapeo reproducible, marcar `no_evaluable`.
- [x] **T-230 (US-BE-049)** — Tests unitarios de persistencia y estados: caso `hit`, `miss`, `void` y `no_evaluable` con fixtures controlados (alineado a ACTA T-244).

* * *

## US-BE-050

- [x] **T-231 (US-BE-050)** — Implementar job/comando/servicio backend que tome picks en `pending_result` y ejecute evaluación contra resultado oficial disponible.
- [x] **T-232 (US-BE-050)** — Añadir idempotencia y política mínima de reintento para picks aún sin resultado; no duplicar cierres ni sobrescribir evaluaciones válidas sin criterio explícito.
- [x] **T-233 (US-BE-050)** — Exponer métricas/counters operativos del loop: picks emitidos, evaluados, pendientes, no evaluables y hit rate sobre evaluados.
- [x] **T-234 (US-BE-050)** — Documentar runbook mínimo de ejecución/dry-run del evaluador (manual o programado), incluyendo precondiciones y lectura de estados.

* * *

## US-BE-051

- [x] **T-235 (US-BE-051)** — Implementar evaluador determinístico de elegibilidad v1 por evento candidato: fixture utilizable, cuotas válidas, >= 2 familias de mercado y ausencia de faltantes críticos en `ds_input`.
- [x] **T-236 (US-BE-051)** — Crear persistencia/auditoría de elegibilidad con: `event_id`, `evaluated_at`, `eligibility_rule_version`, `eligible/ineligible`, `primary_discard_reason` y detalle complementario si aplica.
- [x] **T-237 (US-BE-051)** — Definir catálogo canónico de motivos de descarte y tests por cada causa principal: fixture inválido, cuotas inválidas, familias insuficientes, faltantes críticos en `ds_input`.

* * *

## US-BE-052

- [x] **T-238 (US-BE-052)** — Implementar endpoint o servicio admin de resumen con: eventos candidatos, elegibles, `pool_eligibility_rate`, picks emitidos, evaluados, pendientes, no evaluables e hit rate global sobre evaluados.
- [x] **T-239 (US-BE-052)** — Implementar endpoint o payload complementario para desglose por motivo de descarte, mercado y bucket de confianza si existe; el hit rate debe excluir pendientes y no evaluables.
- [x] **T-240 (US-BE-052)** — Actualizar contrato técnico consumible por FE: OpenAPI/schema/tipos compartidos para respuesta admin de elegibilidad + loop + precisión oficial; dejar ejemplo de payload en docs o fixtures de test.

* * *

## US-FE-061

- [x] **T-241 (US-FE-061)** — Construir vista admin mínima conectada a US-BE-052 con tres bloques claramente separados: cobertura del pool, estado del cierre de loop y desempeño del modelo.
- [x] **T-242 (US-FE-061)** — Renderizar KPIs mínimos: eventos candidatos, elegibles, `pool_eligibility_rate`, motivos de descarte, picks emitidos, evaluados, no evaluables, hit rate global y por mercado.
- [x] **T-243 (US-FE-061)** — Resolver estados `loading`, vacío y error; si existen picks pendientes o no evaluables, mostrarlos explícitamente sin mezclarlos dentro del hit rate.

* * *

## Gobernanza y documentación

- [x] **T-244 (S6.3 transversal)** — Acta de congelación: [`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md) + [`HANDOFF_BE_EJECUCION_S6_3.md`](./HANDOFF_BE_EJECUCION_S6_3.md) §0 + **D-06-050** en `DECISIONES.md`. **TL validado** — §0 cerrado; siguiente paso **PR-BE-1** (T-227, T-228).
- [x] **T-245 (S6.3 transversal)** — Regresión final backend/frontend: tests BT2 tocados + build web + checklist DoD por US; evidencia en [`EJECUCION.md`](./EJECUCION.md) y detalle UI en [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md). Trazabilidad de cierre **D-06-051…054** → tasks T-246…T-257: [`EJECUCION_CIERRE_S6_3.md`](./EJECUCION_CIERRE_S6_3.md) + [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md).

* * *

## Check cierre Sprint 06.3

- [x] Todas las filas del checklist de cobertura arriba tienen al menos una tarea implementada o diferida por decisión explícita.
- [x] La medición del modelo contra resultado oficial ya no depende de `bt2_picks` liquidados por usuario.
- [x] Existe evidencia de cierre de loop para un subconjunto real de picks — ver [`EJECUCION.md`](./EJECUCION.md) § T-247 / T-248 y [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md).
- [x] `pool_eligibility_rate` sale de auditoría persistida y no de conteos ad hoc.
- [x] La vista admin separa cobertura, loop y precisión sin mezclar pendientes/no evaluables dentro del hit rate.
- [x] T-245 referenciado en entrega / acta de cierre.

* * *

Creación: 2026-04-14 — borrador inicial S6.3 orientado a Fase 1.