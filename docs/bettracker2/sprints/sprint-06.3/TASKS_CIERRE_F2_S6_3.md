# Sprint 06.3 — TASKS_CIERRE_F2 (backlog norma F2 extendida)

> **Propósito:** backlog **ejecutable** para cumplir [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).  
> **Numeración:** **T-258 … T-266** (siguiente bloque tras T-257 del cierre core).  
> **Prerequisito:** cierre operativo core [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md) (T-246…T-257) **hecho** salvo brecha explícita.  
> **US:** [`US_CIERRE_F2_S6_3.md`](./US_CIERRE_F2_S6_3.md) · **Handoff:** [`HANDOFF_CIERRE_F2_S6_3.md`](./HANDOFF_CIERRE_F2_S6_3.md).  
> **Borrador de referencia (GPT / repo remoto):** [`PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md`](./PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md) — **no** sustituye decisiones PO; sirve para copiar redacción larga si hace falta.

* * *

## Matriz decisión F2 → tasks

| § / tema en DECISIONES_F2_FINAL | Tasks |
|----------------------------------|-------|
| §1–2 Tier Base/A, bloques SM | T-258, T-259 |
| §4–5 Whitelist core, 2 familias, FT_1X2 + 1 core | T-260, T-261 |
| §3 Causales auditoría | T-262 |
| §6 KPI oficial, secundarias, 30d, 5 ligas, 60/40 | T-263, T-264 |
| §6–7 FE lectura KPI | T-265 |
| Evidencia documental | T-266 |

* * *

## US-BE-055 (extendido)

- [x] **T-258** — **Universo 5 ligas:** definir en código o config estable los `sportmonks_id` / `bt2_leagues.id` para Premier, LaLiga, Serie A, Bundesliga, Ligue 1; documentar en runbook corto o `.env.example` si aplica lista de IDs.
- [x] **T-259** — **Tier Base vs Tier A:** modelo datos o flags (p. ej. en `bt2_leagues` + reglas por evento) para que elegibilidad/Audit sepan qué tier aplica; alinear con tiers existentes si ya hay `tier` S/A/B en CDM sin duplicar conceptos incompatibles.

## US-BE-056

- [x] **T-260** — **Filtro duro §4–5:** asegurar que la elegibilidad oficial exige **FT_1X2 completo** + **al menos una** familia core adicional de la whitelist (`OU_GOALS_2_5`, `BTTS`, `DOUBLE_CHANCE_*` según `market_diversity_family`); ajustar `event_passes_value_pool` / orden de chequeos para no contradecir el doc final.
- [x] **T-261** — **Tier A reforzado:** implementar reglas adicionales para eventos Tier A (raw obligatorio, mayor exigencia de mercados, lineups condicionados §2–3) dentro de `pool_eligibility` o módulo dedicado versionado.
- [x] **T-262** — **Auditoría causales §3:** extender `bt2_pool_eligibility_audit.detail_json` y/o códigos para distinguir: ausente temporal / no soportado fuente / no normalizado / no requerido por tier — sin romper ACTA T-244 (ampliación acordada con PO).

## US-BE-057

- [x] **T-263** — **API métricas F2:** exponer `pool_eligibility_rate_official` (y serie relajada si aplica) **separado** del modo observabilidad; breakdown causas; hooks para cobertura familias core / raw / lineups según §6.
- [x] **T-264** — **Job o script de cierre:** ventana **30 días**, agregado y por liga en las **5** oficiales; evaluar umbrales **60%** global y **40%** por liga; reportar si `INSUFFICIENT_MARKET_FAMILIES` sigue dominante (salida Markdown/JSON para pegar en `EJECUCION.md`).

## US-FE-062 (extensión)

- [ ] **T-265** — **Admin:** consumir contrato T-263 (tipos TS + UI) para mostrar bloque F2 sin recalcular métricas en cliente; coherencia con [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md).

## Gobernanza

- [x] **T-266** — **Documentación:** [`EJECUCION_CIERRE_F2_S6_3.md`](./EJECUCION_CIERRE_F2_S6_3.md) (evidencia primer run T-264 + enlaces). Screenshot FE T-265 pendiente.

* * *

## Check cierre F2 normativo (definición)

- [x] Las 5 ligas y el tier son **reproducibles** en entorno dev/staging.
- [x] KPI oficial vs relajado **no** se confunden en un solo número en API/UI.
- [x] Reporte T-264 ejecutado al menos una vez con resultado archivado.
- [ ] Anexo de [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md) actualizado o sustituido por “validación OK” cuando corresponda.

* * *

*Creación: 2026-04-15 — backlog F2 extendido post–cierre core S6.3.*
