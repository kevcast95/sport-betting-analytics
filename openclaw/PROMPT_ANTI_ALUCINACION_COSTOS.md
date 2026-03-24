# Guardrails OC — anti-alucinación, costes y evidencias

**Cárgalo en OpenClaw** (reglas o documentación del agente) junto a `openclaw.md` y `OPTIMIZACION_TOKENS.md`.

---

## 1. Regla de oro: sin evidencia, sin conclusión

**Prohibido** afirmar como hecho:

- “SofaScore nos baneó / API bloqueada / rate limit / IP ban”
- “El pipeline está roto por bloqueo upstream”
- “`openclaw cron list` quemó el presupuesto” (salvo que muestres métricas reales por invocación)

**Permitido** sin evidencia fuerte:

- “Hipótesis no verificada: …”
- “Para confirmar, ejecutar: … y pegar salida completa”

---

## 2. Evidencia mínima para “error de red / API”

Antes de decir **403 / 429 / timeout de red**, el reporte debe incluir **todas** estas piezas:

| Campo | Ejemplo |
|-------|---------|
| Comando exacto | `python3 jobs/ingest_daily_events.py --sport football --date 2026-03-22 --db ./db/sport-tracker.sqlite3` |
| Fecha usada | Debe ser **real** (`YYYY-MM-DD` válido), no el texto literal del README |
| Código HTTP o traza | `HTTPError 403` con URL completa, o stack trace de `urllib` / Playwright |
| Timestamp | Hora del log |
| Entorno | Host / cron / manual |

Si el job terminó con `"status": "complete"` y `events_skipped_finished > 0`, la clasificación es: **respuesta OK, eventos filtrados (p. ej. ya terminados)**, **no** “ban”.

---

## 3. Interpretación de `ingest_daily_events` (no confundir)

- `already_complete` → no re-fetch; **no** implica bloqueo.
- `events_persisted: 0` + `events_skipped_finished: N` → los N eventos eran **no aptos** por reglas (p. ej. partido terminado); **no** implica ban.
- Error al usar `--date YYYY-MM-DD` literal → **404** por URL inválida; **no** es ban.

---

## 4. Coste y tokens (cron 08:00 / 16:00)

- **No** usar modelo “reasoner” para corridas programadas con muchos eventos; modelo **rápido** salvo orden explícita del operador.
- Tras `select` y `event_splitter`, **siempre** considerar `split_ds_batches.py` con **`--slim`** y **`--chunk-size` 3–4** (ver `OPTIMIZACION_TOKENS.md`).
- Un análisis = **varias llamadas cortas** (una por lote) + `merge_telegram_payload_parts.py` + un solo `render_telegram_payload` por ventana.
- Archivos: **`NAMING_ARTIFACTS.md`** (`candidates_{DATE}_select`, `exec_08h`, `exec_16h`); **no** reutilizar un `candidates.json` genérico mezclando días.

Si una corrida supera tiempo o tokens razonables: **reducir chunk** y repetir; **no** alargar un solo prompt gigante.

---

## 5. Heartbeat / pulso

- Si envías pulso por Telegram vía modelo: **mensaje fijo corto** (pocas líneas, sin pegar logs largos ni repo completo).
- Objetivo: **&lt; ~100 tokens** de input efectivo; **no** re-analizar candidatos en el heartbeat.
- Estado en disco: `out/heartbeat.md` puede actualizarse **sin** pasar por LLM si el operador lo prefiere.

---

## 6. Gateway / puertos / `cron list`

- “Puerto en uso” → proceso duplicado o reinicio; **no** atribuir a SofaScore.
- `openclaw cron list` repetido: investigar **quién** lo agenda; no asumir coste masivo sin datos.

---

## 7. Plantilla de incidente (obligatoria antes de “soluciones”)

```text
## Incidente
- Qué falló (una frase)

## Evidencia
- Comando(s) exactos:
- Salida relevante (pegar bloque, no parafrasear):
- Código HTTP / mensaje de error literal:

## Lo que NO es
- (ej. no es ban si status=complete y skipped_finished)

## Siguiente paso mínimo
- Un solo comando de verificación
```

---

## 8. Bloque para pegar a OC (resumen operativo)

```text
Reglas duras:
1) No digas "API bloqueada/ban/rate limit" sin HTTP 403/429 (o equivalente) + comando + URL + timestamp en logs del job Python ingest o del fetch que uses.
2) ingest complete + skipped_finished → OK con filtros, no ban.
3) Cron análisis: lotes con split_ds_batches --slim, chunk 3-4, merge, render; un Telegram por ventana; archivos con fecha según NAMING_ARTIFACTS.md.
4) No uses reasoner en volumen programado sin orden explícita.
5) Heartbeat: texto corto fijo, sin contexto enorme.
6) Separar hipótesis de hechos; plantilla de incidente antes de proponer proxies o APIs alternativas.
```

---

## Relación con otros archivos

| Archivo | Uso |
|---------|-----|
| `openclaw.md` | Contrato jobs y Telegram |
| `OPTIMIZACION_TOKENS.md` | Lotes, timeout, modelos |
| `NAMING_ARTIFACTS.md` | Rutas `out/` |
| `CRON_COLOMBIA.md` | Secuencia horaria |
