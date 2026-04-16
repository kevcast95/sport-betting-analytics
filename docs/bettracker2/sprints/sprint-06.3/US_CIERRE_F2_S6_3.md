# Sprint 06.3 — US_CIERRE_F2 (norma extendida)

> **Alcance:** historias de usuario para **implementar y medir** lo definido en [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).  
> **No reemplaza** el cierre operativo core ya cubierto en [`US_CIERRE_S6_3.md`](./US_CIERRE_S6_3.md) (T-246…T-257).  
> **Referencia de trabajo (borrador GPT, remoto):** [`PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md`](./PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md) — úsala como catálogo de texto; la fuente normativa es **DECISIONES_CIERRE_F2_FINAL** + este archivo.  
> **Tasks:** [`TASKS_CIERRE_F2_S6_3.md`](./TASKS_CIERRE_F2_S6_3.md) · **Handoff:** [`HANDOFF_CIERRE_F2_S6_3.md`](./HANDOFF_CIERRE_F2_S6_3.md).

* * *

## Matriz norma → US

| Fuente | US |
|--------|-----|
| [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md) §1–2, §7 | **US-BE-055** (extendido) |
| §3–5, anexo validación | **US-BE-056** |
| §6 | **US-BE-057** |
| §6 (lectura admin) + admin existente | **US-FE-062** (extendido) |

* * *

## US-BE-055 — Contrato operativo F2: universo de 5 ligas, Tier Base / A y bloques SM

### Objetivo

Materializar en datos y configuración el **universo oficial de medición** (5 ligas) y el modelo **Tier Base vs Tier A** alineado a §1–2 y §7 del documento final F2.

### Alcance (mínimo)

- Lista canónica de **5 ligas** (Premier, LaLiga, Serie A, Bundesliga, Ligue 1) referenciada por `bt2_leagues` / `sportmonks_id` o mecanismo equivalente acordado con BE.
- Gobernanza explícita: **una** regla global Base + **un** refuerzo Tier A (sin matriz por cada liga individual salvo lo ya decidido).
- Documentar qué significa “bloque mínimo” vs “reforzado” en términos de **checks** implementables.

### Fuera de alcance

- Política de frescura / regeneración de snapshot (fuera del cierre F2 normativo).
- Rediseño completo de ingest SM más allá de lo necesario para los checks.

### Criterios de aceptación

1. Las 5 ligas objetivo son **direccionables** en SQL/jobs sin ambigüedad.
2. Tier Base / Tier A es **evaluable** en código o por configuración (no solo texto).
3. DoD enlazado en `TASKS_CIERRE_F2_S6_3.md` (T-258–T-260 aprox.).

* * *

## US-BE-056 — Regla oficial refinada de elegibilidad y auditoría F2

### Objetivo

Alinear **`pool-eligibility`** con §4–5 del final F2: **FT_1X2 + una familia core adicional** de la whitelist; modo relajado solo observabilidad; Tier A con exigencias mayores (raw, lineups donde aplique).

### Alcance

- Endurecer o versionar reglas en `evaluate_pool_eligibility_*` / agregación para reflejar **filtro duro** oficial vs **env** de observabilidad (ya existe `BT2_POOL_ELIGIBILITY_MIN_FAMILIES` — integrar con KPI “oficial”).
- Extender **auditoría** para distinguir causas §3 (ausente temporal / fuente / normalización / no requerido por tier) — vía `detail_json` y/o códigos nuevos acordados ACTA.

### Criterios de aceptación

1. La regla **no** contradice el anexo de validación del doc final sin decisión explícita.
2. Auditoría permite **explicar** descartes más allá de un solo string genérico cuando el PO lo exija.
3. DoD en tasks T-261–T-263.

* * *

## US-BE-057 — Medición oficial de cierre F2 (`pool_eligibility_rate_official`)

### Objetivo

Implementar el **KPI §6**: tasa oficial vs relajada, métricas secundarias, ventana **30 días**, **5 ligas**, umbrales **60% / 40%** y lectura de causa dominante (`INSUFFICIENT_MARKET_FAMILIES`).

### Alcance

- Endpoint batch y/o job de reporte reproducible; salida apta para **evidencia** en `EJECUCION.md` (nueva sección F2 extendido).
- No sustituye el summary diario actual; puede vivir en admin separado o reporte CLI.

### Criterios de aceptación

1. Se puede demostrar **oficial vs relajado** lado a lado (candados anti-maquillaje §6).
2. Resultado agregado + por liga en la ventana acordada.
3. DoD T-264–T-266.

* * *

## US-FE-062 (extensión) — Admin: lectura de cierre F2 cuando backend exponga KPI

### Objetivo

Cuando existan campos/endpoint del **US-BE-057**, mostrar en `/v2/admin/fase1-operational` (o vista hermana) el bloque mínimo de **KPI F2** sin reescribir números en cliente.

### Dependencias

- Contrato estable desde BE (tipos OpenAPI / `bt2Types.ts`).
- Misma clave admin que hoy.

### Criterios de aceptación

1. Estados loading / error / vacío coherentes con el resto de la vista.
2. No se mezcla “oficial” con “relajado” en un solo número sin etiqueta.

* * *

*Creación: 2026-04-15 — US derivadas de [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).*
