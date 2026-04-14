# ACTA T-244 — Contrato técnico Fase 1 (S6.3)

> Referenciada en [`HANDOFF_BE_EJECUCION_S6_3.md`](./HANDOFF_BE_EJECUCION_S6_3.md) §0 y en **D-06-050** (`DECISIONES.md`).

## Propósito

Esta mini acta congela el contrato técnico mínimo de Fase 1 antes de abrir PRs de implementación de dominio.

Su objetivo es evitar que backend, jobs, admin y frontend avancen con definiciones distintas de:

- fuente oficial de verdad,
- mercados soportados v1,
- estados de evaluación,
- y motivos de descarte.

Esta acta debe quedar aprobada antes del merge del primer PR de dominio de Fase 1.

---

## Mini acta Fase 1 — congelación de contrato técnico (T-244)

| Campo | Contenido |
| --- | --- |
| **Fecha** | 2026-04-14 |
| **Responsable acta** | PO + apoyo Arq/BA/PM |
| **1. Fuente oficial de verdad** | **SportMonks / CDM BT2**. La verdad oficial de resultado para evaluación del modelo en v1 será el resultado oficial del fixture almacenado desde la integración de SportMonks en el CDM BT2. Fuente operativa base: `raw_sportmonks_fixtures` como insumo primario de resultado post-partido, normalizado/consumido por la capa BT2 para evaluar sugerencias. Si un fixture no tiene resultado oficial final confiable disponible desde SportMonks/CDM, queda **`pending_result`** o **`no_evaluable`** según el caso; no se usa liquidación del usuario como fuente de verdad. |
| **2. Mercados soportados v1** | **Lista cerrada v1:** `1X2` y `TOTAL_GOALS_OU_2_5` (Over/Under 2.5 goles). **Fuera de lista = `no_evaluable` por diseño**, no por bug. `BTTS` y otros mercados quedan fuera de evaluación oficial v1 hasta que completitud + builder + consenso estén suficientemente cerrados. |
| **3. Estados de evaluación** | **Enum final v1:** 1. `pending_result` = el pick existe pero todavía no hay resultado oficial final confiable para evaluarlo. 2. `evaluated_hit` = el pick fue evaluado contra resultado oficial y se cumplió. 3. `evaluated_miss` = el pick fue evaluado contra resultado oficial y no se cumplió. 4. `void` = el pick no cuenta para hit/miss por anulación, suspensión, cancelación o mercado inválido por causa oficial. 5. `no_evaluable` = el pick no puede entrar en evaluación formal por estar fuera de mercados soportados v1, faltar verdad oficial suficiente, o no cumplir contrato mínimo de evaluación. |
| **4. Motivos de descarte (códigos)** | **Catálogo canónico inicial v1:** `MISSING_FIXTURE_CORE` = fixture inconsistente o incompleto; `MISSING_VALID_ODDS` = sin cuotas válidas utilizables; `INSUFFICIENT_MARKET_FAMILIES` = no alcanza el mínimo de familias requeridas para elegibilidad del pool; `MISSING_DS_INPUT_CRITICAL` = faltante crítico en `ds_input`; `OUTSIDE_SUPPORTED_MARKET_V1` = mercado fuera de 1X2 u O/U 2.5; `MISSING_TRUTH_SOURCE` = no hay resultado oficial final confiable; `EVENT_NOT_SETTLED` = el evento aún no terminó/liquidó oficialmente; `MARKET_MAPPING_UNRESOLVED` = no fue posible mapear de forma canónica el mercado/selección; `VOID_OFFICIAL_EVENT` = evento o mercado oficialmente anulado/suspendido. |
| **Aprobación** | **PO: sí — 2026-04-14** / **TL: sí — validación técnica y literales alineados al acta para migración/job/admin (2026-04-14)** |

---

## Criterios de interpretación

### 1. Fuente oficial de verdad

La evaluación del modelo en Fase 1 se hará contra **resultado oficial del evento/mercado**, no contra picks liquidados por el usuario dentro de la app.

Esto mantiene alineado el sistema con la definición aprobada en Fase 0.

### 2. Subconjunto inicial de mercados

El subconjunto v1 queda cerrado a:

- `1X2`
- `TOTAL_GOALS_OU_2_5`

Todo pick fuera de este subconjunto será tratado como:

- `no_evaluable` en evaluación,
- o descartado por contrato si aplica en elegibilidad.

Esto evita abrir demasiados frentes mientras todavía se está cerrando verdad, builder y completitud.

### 3. Estados de evaluación

Los estados definidos en esta acta deben ser exactamente los mismos en:

- migraciones / DB,
- jobs de evaluación,
- métricas,
- admin,
- y contratos expuestos a frontend.

No deben aparecer aliases, enums paralelos o strings alternos.

### 4. Motivos de descarte

Los códigos definidos aquí deben considerarse canónicos para v1.

Su objetivo es servir tanto para:

- lógica de elegibilidad,
- como trazabilidad operativa,
- cobertura admin,
- y explicaciones entendibles en capas posteriores.

---

## Nota operativa sobre `EVENT_NOT_SETTLED`

Mientras un evento todavía no tenga resultado oficial final, el pick debe quedar preferiblemente en estado:

- `pending_result`

El motivo `EVENT_NOT_SETTLED` debe usarse cuando haga falta registrar explícitamente por qué aún no puede evaluarse o por qué quedó fuera de cierta corrida/reportería.

Si nunca llega una verdad confiable o existe inconsistencia persistente, el caso podrá terminar como:

- `no_evaluable`
- con motivo complementario `MISSING_TRUTH_SOURCE`

---

## Resolución

Queda congelado el contrato técnico mínimo de Fase 1 con estas definiciones iniciales:

1. La verdad oficial vendrá de **SportMonks / CDM BT2**
2. Los mercados soportados v1 serán **`1X2`** y **`TOTAL_GOALS_OU_2_5`**
3. Los estados de evaluación oficiales serán:
   - `pending_result`
   - `evaluated_hit`
   - `evaluated_miss`
   - `void`
   - `no_evaluable`
4. El catálogo canónico inicial de motivos de descarte será el definido en esta acta

---

## Checklist de salida §0

- [x] Los cuatro puntos tienen texto no ambiguo
- [x] `DECISIONES.md` S6.3 actualizado — ver **D-06-050**
- [x] **T-244** marcada en `TASKS.md` (acta mergeada en repo)
- [x] Validación técnica TL completada antes de PR-BE-1
