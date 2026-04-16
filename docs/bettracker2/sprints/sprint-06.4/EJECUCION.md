# Sprint 06.4 — EJECUCION

> Registro de **evidencia** para cerrar **Fase 2 / F3** dentro de este sprint: frescura vs coste; ingesta SM/CDM vs DSR.  
> **TASKS:** [`TASKS.md`](./TASKS.md). **Handoff:** [`HANDOFF_BE_EJECUCION_S6_4.md`](./HANDOFF_BE_EJECUCION_S6_4.md).  
> **Verdad madre programa:** [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md).

**Congelación 061/062:** [`DECISIONES.md`](./DECISIONES.md) **D-06-068** (universo, cadencia, familias, disponible, matching).

---

## Plantilla — entorno y ventana de validación

| Campo | Valor |
|--------|--------|
| **Entorno** | *(p. ej. local API + Postgres `.env` / staging)* |
| **Rama / commit** | `sprint-06.4` @ *(hash)* |
| **Ventana temporal** | *(`operating_day_key` = día; universo **D-06-068** §1)* |
| **Cadencia** | **D-06-068** §2 + TZ documentada (**T-280**) |

---

## Plantilla — corridas obligatorias (F3)

Documentar cada corrida relevante (fecha, operador opcional):

| ID task | Tipo | Comando / job | Resultado esperado | ¿OK? |
|---------|------|----------------|----------------------|------|
| T-274 | CDM sin DSR | *(comando)* | Datos frescos sin incremento contador DSR | [ ] |
| T-274 | DSR autorizado | *(comando)* | DSR solo bajo condición de política | [ ] |
| T-275 | Regresión | `python3 -m unittest discover -s apps/api -p '*_test.py'` *(o subset)* | OK | [ ] |

**Salidas capturadas:** pegar bloques `text` o enlazar logs (ruta en repo si se archivan).

---

## Plantilla — métricas a validar (coste / frescura)

| Métrica | Fuente (log, tabla, endpoint) | Valor antes | Valor después | Notas |
|---------|-------------------------------|---------------|-----------------|-------|
| Ciclos ingesta SM / CDM | | | | |
| Invocaciones DSR | | | | |
| Latencia o antigüedad snapshot | | | | |
| Errores 429 / rate limit SM | | | | |

*Ajustar filas según lo implementado en **T-271**.*

---

## Evidencia esperada — US-BE-061 (medición intradía SM)

| Ítem | Qué dejar registrado |
|------|----------------------|
| Comando / cron | Ruta del job o script + ejemplo `crontab` o scheduler |
| Ventana | Día(s) y nº de fixtures observados |
| **Persistencia** | **Nombre exacto** de la tabla (migración **T-287**): `bt2_nonprod_sm_fixture_observation_s64` (append-only); volumen de filas ejemplo |
| **Análisis EOD** | **SQL pegado** (o ruta `.sql` en repo): (1) primera `observed_at` con lineup disponible por `sm_fixture_id`; (2) primera con mercados relevantes; (3) frecuencia (`count` por hora o por cambio de firma) |
| Familias observadas | **D-06-068** §3 (lineups, FT_1X2, OU_GOALS_2_5, BTTS) |
| Rate limit | Confirmación de intervalo mínimo usado y errores 429 si hubo |
| Alcance | Texto: **observabilidad / insumo política**, no fallback productivo |

*Relacionar con calibración de **US-BE-058** (texto breve en notas al pie de esta sección).*

### US-BE-061 — Comando y entorno (T-281 / T-282)

| Campo | Valor |
|--------|--------|
| **Migración** | `alembic upgrade head` (revisión `j4a5b6c7d8e9` → tabla `bt2_nonprod_sm_fixture_observation_s64`) |
| **Job** | `python3 scripts/bt2_cdm/job_sm_intraday_observation.py` |
| **Env** | `BT2_DATABASE_URL`, `SPORTMONKS_API_KEY`; opcional `BT2_SM_OBS_SLEEP_S` (default `0.35`) |
| **Día UTC** | `--operating-day 2026-04-16` (opcional; default hoy UTC) |
| **Cron sugerido** | `*/5 * * * *` (ver runbook **T-280** §9) |

Ejemplos:

```bash
python3 scripts/bt2_cdm/job_sm_intraday_observation.py --dry-run
python3 scripts/bt2_cdm/job_sm_intraday_observation.py --ignore-cadence
```

**Nota hacia US-BE-058:** estas series miden **disponibilidad SM intradía** para calibrar política F3; no fijan por sí solas cupos DSR.

#### SQL — análisis EOD (tabla T-287)

**1) Primera observación con lineup disponible (§4) por fixture**

```sql
SELECT DISTINCT ON (sm_fixture_id)
  sm_fixture_id,
  observed_at AS first_lineup_available_at
FROM bt2_nonprod_sm_fixture_observation_s64
WHERE lineup_available = true
ORDER BY sm_fixture_id, observed_at ASC;
```

**2) Primera observación con las tres familias de mercado usables (§5)**

```sql
SELECT DISTINCT ON (sm_fixture_id)
  sm_fixture_id,
  observed_at AS first_all_markets_at
FROM bt2_nonprod_sm_fixture_observation_s64
WHERE ft_1x2_available = true
  AND ou_goals_2_5_available = true
  AND btts_available = true
ORDER BY sm_fixture_id, observed_at ASC;
```

**3) Frecuencia de observaciones por hora (día UTC en `observed_at`)**

```sql
SELECT date_trunc('hour', observed_at AT TIME ZONE 'UTC') AS hour_utc,
       count(*) AS n_rows
FROM bt2_nonprod_sm_fixture_observation_s64
WHERE observed_at >= date '2026-04-16'
  AND observed_at < date '2026-04-16' + interval '1 day'
GROUP BY 1
ORDER BY 1;
```

*(Sustituir fechas por el día corrido; el conteo de fixtures del universo F2 sale de `bt2_events` filtrado por ligas y `kickoff_utc`.)*

---

## Evidencia esperada — US-BE-062 (benchmark SM vs SofaScore)

| Ítem | Qué dejar registrado |
|------|----------------------|
| Universo | **D-06-068** §1 (todos los partidos del día, 5 ligas) |
| Mapeo (**T-283**) | Regla **D-06-068** §6 + conteo `needs_review` |
| **T-288** | Solo observaciones **SofaScore**; migración + nombre tabla |
| **T-287** | Lado **SM** del comparativo (no duplicar en 062) |
| Pipeline SofaScore | Rutas o comandos que invocan `processors/lineups_processor.py`, `core/scraped_odds_anchor.py`, `processors/odds_all_processor.py`, `processors/odds_feature_processor.py` (los usados realmente) |
| **SQL comparativo** | `JOIN`/`UNION ALL` **T-287** + **T-288** por `sm_fixture_id` + tiempo: primera lineup y mercados por lado; frecuencia |
| Informe | Export Markdown/JSON **derivado** de esas queries + tabla resumen pegada aquí |
| **Disclaimer** | Frase explícita: **SofaScore solo benchmark/discovery; sin fallback productivo aprobado en S6.4** (**D-06-066**, **T-286**) |
| Gate | Checklist **T-286**: sin feature flag de fallback; sin consumo SofaScore en rutas productivas BT2/CDM; tablas benchmark **no** usadas por producto |

---

## Criterios para declarar **cerrado F3 dentro de S6.4**

1. **Política** US-BE-058 mergeada y referenciada en `DECISIONES.md` / `PLAN.md` según **T-268**.  
2. **Comportamiento** acorde a **D-06-064**: evidencia de **T-274** con los dos modos (CDM solo + DSR condicionado).  
3. **Observabilidad** mínima: runbook **T-272** + checklist **T-273** ejecutado al menos una vez.  
4. **Regresión** **T-275** sin fallos en el alcance acordado.  
5. **Línea base de alcance:** ninguna evidencia cierra **F4/F5** ni reabre **F2/S6.3**.  
6. **US-BE-061 / US-BE-062** (si se declaran cerradas): secciones arriba con **T-287**, **T-288**, SQL; **T-286** OK (**D-06-065**: no hay medición paralela US-BE-060).

---

## Registro de PRs / merges (rellenar durante el sprint)

| PR | Descripción breve | Tasks |
|----|-------------------|-------|
| | | |

---

## Notas de kickoff / desviaciones

*(Espacio libre para TL/PO durante ejecución.)*

---

*2026-04-15 — EJECUCION S6.4; **D-06-068** + tablas **T-287** / **T-288** + SQL.*
