# Backtesting, reconciliación atraco vs tiempo real, y odds en CDM

> Notas de conversación técnica (2026) para retomar con equipo / BA / datos.  
> Relacionado: Sprint 02–04 (atraco, `normalize_fixtures`, `fetch_upcoming`), tablas `bt2_*`.  
> Producto “verdad de odds / edge en el tiempo” y calidad de señal DSR: [`../sprints/sprint-06.1/OBJETIVO_SENAL_Y_EDGE_DSR.md`](../sprints/sprint-06.1/OBJETIVO_SENAL_Y_EDGE_DSR.md) (**D-06-020**).

---

## 1. ¿Dónde viven los datos: atraco vs operación diaria?

### Atraco (histórico)

1. Ingesta masiva SportMonks → **`raw_sportmonks_fixtures`** (JSON por fixture).
2. **`scripts/bt2_cdm/normalize_fixtures.py`** lee el raw y hace upsert al **CDM**:
   - `bt2_leagues` → `bt2_teams` → **`bt2_events`** → **`bt2_odds_snapshot`**.

### Tiempo real / día a día (`fetch_upcoming`)

- **No** escribe en `raw_sportmonks_fixtures` (va directo al CDM).
- Reutiliza helpers del normalizador (`upsert_event`, `insert_odds_bulk`, etc.).
- Destino: las **mismas tablas** `bt2_events` y `bt2_odds_snapshot`.

### Cuando el usuario consulta picks (API)

- Los endpoints leen **solo PostgreSQL** (p. ej. `bt2_events`, `bt2_odds_snapshot`, `bt2_daily_picks`).
- **No** se llama a SportMonks en cada `GET` de bóveda.
- El snapshot diario se materializa en **`session/open`** con el estado de la DB **en ese momento**; si después cambian cuotas en SM, hace falta **nueva ingesta** para actualizar `bt2_odds_snapshot` — el snapshot guardado no se regenera solo.

---

## 2. Reconciliación “atraco + último mes en vivo” para un backtest de 3 meses

### Eventos / partidos (`bt2_events`)

- Clave natural: **`sportmonks_fixture_id`**.
- Upsert: `ON CONFLICT (sportmonks_fixture_id) DO UPDATE` (status, resultados con `COALESCE` donde aplica).
- **Conclusión:** el mismo fixture cargado por atraco y tocado luego por `fetch_upcoming` es **una sola fila**; no hay dos versiones paralelas del partido en CDM.

### Cuotas (`bt2_odds_snapshot`)

- Upsert por **`(event_id, market, selection, bookmaker)`**:
  - `ON CONFLICT … DO UPDATE SET odds, fetched_at`.
- **Conclusión:** el CDM guarda el **último valor ingerido** por esa clave, **no** un historial completo de movimientos de línea.

### Implicación para backtesting 3 meses atrás

- **Identidad de partido:** reconciliada en una tabla.
- **Cuotas “como estaban el día de la decisión”:** **no** se deducen solas del esquema actual si hubo re-ingestas posteriores: lo que queda puede ser la **última** snapshot, no la de hace 3 meses.

### Estrategias recomendadas (a planear con datos)

1. **Base congelada:** dump o schema `*_as_of_*` antes de seguir refrescando producción.
2. **Historial de odds:** tablas append-only o versionado por `fetched_at` si el negocio exige CLV / backtest de precio.
3. **Backtest solo con resultado** (sin precio histórico fiel): más simple pero más débil para edge.

---

## 3. Referencias de código

- `scripts/bt2_cdm/fetch_upcoming.py` — comentario: no toca `raw_sportmonks_fixtures`.
- `scripts/bt2_cdm/normalize_fixtures.py` — `upsert_event`, `insert_odds_bulk` (conflictos y updates).
- `docs/bettracker2/sprints/sprint-03/US.md` — flujo raw → CDM.
- `docs/bettracker2/sprints/sprint-04/US.md` — `fetch_upcoming` y CDM.

---

## 4. (Anexo) Calidad de picks / DSR — líneas de trabajo con BA

Objetivo producto citado: **menos picks, más probabilidad de éxito**, sin confundir **etiqueta de confianza del LLM** con **calidad del dato SM** ni con **edge real**.

Palancas a diseñar con BA (métricas y reglas explícitas, no solo prompt):

| Palanca | Idea |
|--------|------|
| Elegibilidad dura | Solo eventos con líneas completas (p. ej. 1X2 + O/U 2.5) en snapshot antes de entrar al pool DSR. |
| Techo de pool | Reducir N máximo o subir odd mínima en el SQL de candidatos. |
| Edge en BE | Calcular edge implícito en servidor y filtrar / marcar por umbral (no depender solo de “Baja/Media” del modelo). |
| Prompt | Pedir explícitamente menos picks con más edge (alineado a v1). |
| Confianza vs datos | Renombrar o separar en UX/API “confianza modelo” vs “completitud de líneas” / “score dato”. |

*Este anexo resume preferencias para planning; la decisión de alcance queda con PO/BA.*

---

*Última actualización: 2026-04-08.*
