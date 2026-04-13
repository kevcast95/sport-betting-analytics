# Siguientes pasos — post auditoría `raw_sportmonks_fixtures`

**Estado:** pendiente de ejecución BE/datos.  
**Evidencia:** [`AUDITORIA_RAW_SPORTMONKS_2026-04-09.md`](./AUDITORIA_RAW_SPORTMONKS_2026-04-09.md).

Usar esta lista como **checklist** en standup o PR.

---

## Checklist

- [x] **Lineups en payload** — Ejecutar **§4** de la auditoría (SQL subcadenas + script recursivo). Entregar `out/lineup_probe_paths.json` + conclusión construible / no / parcial.  
  *Instrucción detallada:* [AUDITORIA §4](./AUDITORIA_RAW_SPORTMONKS_2026-04-09.md#4-instrucción-be--validar-si-se-puede-construir-lineups-desde-este-payload).  
  *Hecho 2026-04-10:* `out/lineup_probe_paths.json`, §4 rellenada en la auditoría, gap en `V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md` §7, builder con `diagnostics` explícito.

- [x] **Búsqueda recursiva ampliada** — 5–10 `fixture_id` distintos; strings: `lineup`, `formation`, `sidelined`, `injur`, `missing` (puede fusionarse con el ítem anterior si el script ya lo cubre). Informe: `path → tipo → snippet`.  
  *Fusionado con ítem anterior:* `scripts/bt2_lineup_payload_probe.py` (10 fixtures, keys + `squad`/`suspension` en regex).

- [ ] **Payloads completos para mapper `statistics`** — Volcar **1–2** JSON completos en `out/` (fixture **programado** vs **terminado**), redactados si hace falta; objetivo: diseñar mapper `statistics[]` → shape tipo `process_statistics` y lista de campos **excluidos** del LLM en pre-partido (**D-06-002**).

- [ ] **429 eventos sin fila raw** — Exportar lista de `sportmonks_fixture_id` desde `bt2_events` LEFT JOIN `raw_sportmonks_fixtures` WHERE raw IS NULL; job de **backfill** **o** en builder `diagnostics.raw_fixture_missing` (y no fingir datos).

---

## Después de cerrar el checklist

- Actualizar [`V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md`](./V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md) con rutas JSON reales.
- Enlazar en **T-189** / **US-BE-037** el diseño de `processed.*` aprobado.

---

*2026-04-09*
