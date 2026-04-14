# Evidencia — UI admin Fase 1 (S6.3 / US-FE-061)

## Ruta

`/v2/admin/fase1-operational` (misma clave `VITE_BT2_ADMIN_API_KEY` que Precisión DSR).

## Base de datos local

Si el API devuelve **500** o el pool muestra solo «sin auditoría reciente», suele faltar una migración. Desde la **raíz del repo** (misma `BT2_DATABASE_URL` que en `.env`):

```bash
PYTHONPATH=apps/api python3 -m alembic -c apps/api/alembic.ini upgrade head
```

Si `python3 -m alembic` dice que no existe el módulo: `pip install -r requirements.txt -r apps/api/requirements.txt` (ver [`LOCAL_API.md`](../../LOCAL_API.md)).

Incluye `bt2_pool_eligibility_audit` y `bt2_pick_official_evaluation`. Sin esas tablas, el endpoint intenta degradar con métricas vacías y aviso en texto; lo correcto en dev es estar en **head**.

## QA manual mínimo

1. Con API y clave configuradas, abrir la vista: deben verse **tres bloques** (pool, loop, desempeño).
2. **Hit rate global**: texto explícito “solo hit+miss”; pendientes y no evaluables en KPIs separados.
3. **Día sin datos**: candidatos 0 y picks 0 → aviso ámbar de vacío operativo.
4. **Error**: quitar o falsificar clave → mensaje de configuración o 401/503 entendible.
5. **Actualizar**: cambiar fecha o pulsar botón → nueva llamada a `fase1-operational-summary`.

## Contrato

- Tipos TS: `Bt2AdminFase1OperationalSummaryOut` en `apps/web/src/lib/bt2Types.ts`.
- Ejemplo JSON backend: `apps/api/fixtures/bt2_admin_fase1_operational_summary.example.json`.

## Tests automáticos

`npm run test -- --run src/pages/AdminFase1OperationalPage.test.tsx`

## Build / regresión web (T-245)

- Resumen de comandos y tabla DoD: [`EJECUCION.md`](./EJECUCION.md).
- **`apps/web`:** `npm run build` — OK (`tsc -b && vite build`).
- **`VaultPage.tsx`:** se corrigió **TS2367** en el botón de regeneración bajo el bloque que ya exige `picksLoadStatus === 'loaded'` y `apiPicks.length > 0`: no se compara `picksLoadStatus === 'loading'` (imposible tras el estrechamiento de tipos). `disabled` quedó como `apiPicks.length === 0` (en esa rama es falso, pero mantiene la intención si cambia el layout).
