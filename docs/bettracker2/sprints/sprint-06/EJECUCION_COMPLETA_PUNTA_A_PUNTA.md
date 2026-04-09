# Sprint 06 — Ejecución completa punta a punta (sin revalidar cada paso)

> **Para qué sirve:** una sola checklist **ordenada** desde cero hasta “API + web + bóveda + admin DSR” funcionando. Si un paso falla, el siguiente **no** se considera cerrado.  
> **Fuente de verdad de tareas:** [`TASKS.md`](./TASKS.md) — **esta guía no la sustituye**; úsala como **script de demo / smoke** y como orden operativo punta a punta.  
> **DSR con DeepSeek en vivo:** **T-169** + **D-06-018**.

---

## 1) Clave admin `BT2_ADMIN_API_KEY` (respuesta directa al FE)

**El servidor no te “da” ese valor.** No aparece en ningún endpoint ni en logs como valor por defecto.

- **Vos (u operación) elegís un secreto** (string largo aleatorio, como una contraseña). Ejemplo de generación: `openssl rand -hex 32`.
- **Mismo valor en dos sitios:**
  1. **API (raíz del repo):** en tu `.env` → `BT2_ADMIN_API_KEY=<el-secreto>`
  2. **Web:** en `apps/web/.env` → `VITE_BT2_ADMIN_API_KEY=<el-mismo-secreto>`

**Por qué:** el API compara el header `X-BT2-Admin-Key` con **`bt2_settings.bt2_admin_api_key`** (carga desde `BT2_ADMIN_API_KEY` en el `.env` raíz vía Pydantic — `apps/api/bt2_router.py`, `_require_bt2_admin`). El FE embebe la clave en build (Vite) para enviar ese header al llamar `GET /bt2/admin/analytics/dsr-day`.

**Si falta en el API:** respuesta **503** (“defina BT2_ADMIN_API_KEY”).  
**Si falta en el FE:** error en UI (“Falta VITE_BT2_ADMIN_API_KEY”).  
**Si no coinciden:** **401** (“Clave admin inválida”).

**Después de cambiar `VITE_*`:** reiniciar `npm run dev` (Vite no siempre recarga env).

**Trampa corregida en código (2026-04-08):** `BT2_ADMIN_API_KEY` en el `.env` raíz **no** entraba en `os.environ` porque solo **Pydantic** lee ese archivo para los campos de `BT2Settings`. El admin ahora usa `bt2_settings.bt2_admin_api_key` (campo que mapea a `BT2_ADMIN_API_KEY`). Tras actualizar, **reiniciar uvicorn**.

---

## 2) Variables de entorno mínimas (checklist)

| Dónde | Variable | Obligatorio para | Notas |
|-------|----------|------------------|--------|
| **Raíz `.env`** | `BT2_DATABASE_URL` | API BT2 | Postgres |
| **Raíz `.env`** | `SPORTMONKS_API_KEY` | Ingesta CDM | Puede ser placeholder solo si no corrés jobs |
| **Raíz `.env`** | `BT2_ADMIN_API_KEY` | Vista admin analytics | Lo inventás vos (ver §1) |
| **Raíz `.env`** | `DEEPSEEK_API_KEY` | DSR **LLM** | Solo si `BT2_DSR_PROVIDER=deepseek` (**T-169** implementado) |
| **Raíz `.env`** | `BT2_DSR_PROVIDER` | Comportamiento DSR | `deepseek` en staging/prod con PO; `rules` sin API |
| **`apps/web/.env`** | `VITE_BT2_ADMIN_API_KEY` | Admin en UI | **Igual** que `BT2_ADMIN_API_KEY` |
| **`apps/web/.env`** | URL API / auth JWT | Bóveda y sesión | Según [`LOCAL_API.md`](../../LOCAL_API.md) |

Plantilla comentada: [`.env.example`](../../../../.env.example) (raíz) y `apps/web/.env.example`.

---

## 3) Orden de ejecución (backend + datos + frontend)

Ejecutar **en este orden**. Si algo falla, **parar** y corregir antes de seguir.

### Fase A — Infra y código

1. **Postgres** arriba y `BT2_DATABASE_URL` correcta.
2. **Migraciones Alembic** aplicadas en la misma DB que usa la API (`apps/api/alembic`).
3. **Arrancar API:** desde raíz, `uvicorn` según [`LOCAL_API.md`](../../LOCAL_API.md).
4. **Definir** `BT2_ADMIN_API_KEY` en `.env` raíz **y** `VITE_BT2_ADMIN_API_KEY` en `apps/web/.env` (**mismo valor**).
5. **Arrancar web:** `npm run dev` en `apps/web` (o monorepo script que use).

### Fase B — Datos para que existan eventos en el día

6. **Ingesta CDM** para que haya `bt2_events` + `bt2_odds_snapshot` en la ventana del **día operativo** del usuario (job documentado en runbook **T-160**, p. ej. `scripts/bt2_cdm/job_fetch_upcoming.py` y pipeline que alimente odds). **Sin eventos programados hoy → el snapshot puede insertar 0 filas** (bóveda vacía no es bug de DSR).

### Fase C — Usuario y snapshot (esto materializa `bt2_daily_picks`)

7. **Usuario BT2** creado y **login** en V2 (JWT válido).
8. **Abrir sesión del día:** `POST /bt2/session/open` (desde la app al iniciar estación). Eso dispara **`_generate_daily_picks_snapshot`** la **primera vez** para `(user_id, operating_day_key)` — ver `bt2_router.py`. Ahí se llama hoy a `suggest_from_candidate_row` (**rules** o **DeepSeek** cuando exista **T-169**).
9. **Abrir bóveda** en la UI: debe listar picks del día si la fase B pobló eventos.

### Fase D — Admin precisión DSR

10. En la web, abrir **`/v2/admin/dsr-accuracy`** (menú lateral **Precisión DSR**, T-166). Debe llamar a `GET /bt2/admin/analytics/dsr-day` con `X-BT2-Admin-Key`; si §1 está bien, ves KPIs, `summaryHumanEs` y tabla de auditoría para el `operatingDayKey` elegido.

### Fase E — DSR “real” (DeepSeek, **semántica v1 por lotes**)

11. Con **T-169** + **T-170** (**D-06-018**, **D-06-019**): `BT2_DSR_PROVIDER=deepseek` + `DEEPSEEK_API_KEY` en `.env` API, **reiniciar API**. El criterio de producto es **lotes** (`picks_by_event` / comparación cruzada en prompt), no “1 evento por request” como diseño final sin excepción PO.
12. **Importante:** el snapshot **ya generado** no se re-ejecuta solo (idempotencia: si ya hay filas para ese usuario/día, `_generate_daily_picks_snapshot` retorna sin insertar). Para **volver a generar** con LLM hace falta **nuevo día operativo**, **otro usuario de prueba**, o **borrar filas** `bt2_daily_picks` de ese par (u operación explícita que el BE documente). Hasta que exista endpoint “regenerar snapshot”, esto es el comportamiento actual del código. **Si la API DeepSeek falla** en la **primera** generación, el día igual se materializa con **`dsr_source=rules_fallback`** (degradación — ver [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md) § DeepSeek).

### Fase F — Settlement y ledger (T-167, si hay pick tomado)

13. Con al menos un pick **tomado** y, si aplica, **liquidado**: abrir **Liquidación** (`/v2/settlement/...`) y comprobar **mercado** con etiqueta canónica / CDM según API.  
14. Abrir **Libro mayor** (`/v2/ledger`): columna de mercado debe mostrar **`marketCanonicalLabelEs`** cuando el API la envía (fallback a clase CDM / `—`).

---

## 4) Definition of done “todo corre” (producto)

| # | Criterio |
|---|----------|
| 1 | API levanta sin 503 en admin por falta de `BT2_ADMIN_API_KEY` |
| 2 | Web tiene `VITE_BT2_ADMIN_API_KEY` alineada → admin carga analytics |
| 3 | Hay datos CDM en ventana del día → `session/open` crea filas en `bt2_daily_picks` |
| 4 | Bóveda muestra esos picks (T-165 para narrativa UX completa) |
| 5 | **T-169** + **T-170** hechos + `deepseek` + key → snapshots con `dsr_source=dsr_api` y **lotes v1-equivalentes** (**D-06-019**) cuando la API responde OK |

---

## 5) Smoke manual FE — cierre **T-168** (orden sugerido)

Ejecutar en **staging o local** con API + web ya levantados y variables de §2 cargadas. Complementa `npm test` / `npm run build` en `apps/web` (automatizado).

| Paso | Qué validar |
|------|-------------|
| 1 | **Login** V2 → JWT válido; sin errores de red en consola. |
| 2 | **Sesión / día operativo:** flujo que dispara **`POST /bt2/session/open`** (apertura de estación) sin 4xx inesperados. |
| 3 | **Bóveda:** picks del día; bloque **DSR** (narrativa o copy honesto “reglas” si no hay LLM); sin JSON crudo de proveedor. |
| 4 | **Admin DSR:** `VITE_BT2_ADMIN_API_KEY` = `BT2_ADMIN_API_KEY` → **`/v2/admin/dsr-accuracy`** carga KPIs y tabla (o mensaje coherente si no hay datos). |
| 5 | **Settlement + ledger** (si hay datos T-167): etiquetas de mercado alineadas al API tras liquidar / hidratar ledger. |

---

## 6) Referencias rápidas

- Matriz FE/BE: [`EJECUCION.md`](./EJECUCION.md)  
- DSR proveedor: [`DECISIONES.md`](./DECISIONES.md) **D-06-018**  
- Handoff campos vault/admin: [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md)

---

## 7) DX — `bt2Types.ts` cuando cierren **T-153** / **T-155**

Mientras **T-153** (catálogo `MarketCanonical` + tipos) y **T-155** (`operatorProfile`, `reason` ledger, OpenAPI) sigan **abiertas** en [`TASKS.md`](./TASKS.md), el FE mantiene tipos **manuales** en `apps/web/src/lib/bt2Types.ts` alineados al handoff vigente.

**Cuando el DX cierre** esas tareas y exista **OpenAPI / pipeline de tipos** acordado: **regenerar o fusionar** `bt2Types.ts` según el procedimiento del equipo (no automatizado en este doc). Revisar también `contractVersion` en `GET /bt2/meta` (**T-156**).

---

*Última actualización: 2026-04-07 — §5 smoke T-168; §7 DX; ruta admin explícita; fase settlement/ledger (§3 F).*
