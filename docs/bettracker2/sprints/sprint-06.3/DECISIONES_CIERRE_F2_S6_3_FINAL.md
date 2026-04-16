# DECISIONES_CIERRE_F2_S6_3_FINAL

## Relación con el cierre operativo “core” de S6.3 (no confundir)

| Documento | Qué cierra |
|-----------|------------|
| [`DECISIONES_CIERRE_S6_3.md`](./DECISIONES_CIERRE_S6_3.md) | **Evidencia operativa** mínima: loop oficial, auditoría, admin, paralelo F2 *como validación puntual* (D-06-051 … D-06-054). |
| [`EJECUCION_CIERRE_S6_3.md`](./EJECUCION_CIERRE_S6_3.md) | Mapa **decisión → task T-246…T-257 → evidencia** en [`EJECUCION.md`](./EJECUCION.md). |
| **Este archivo** | **Norma de producto/datos del frente F2**: completitud, Tier Base/A, bloques SM, familias core, KPI `pool_eligibility_rate_official`, 5 ligas objetivo. |

**Tiene sentido con lo que viene:** el cierre “core” demuestra que el pipeline y el admin funcionan con datos reales; **este** documento fija **hacia dónde** debe converger la implementación y la medición de F2. Parte del contenido aquí (p. ej. §5 modo relajado `min_familias=1` solo observabilidad) está alineado con la variable `BT2_POOL_ELIGIBILITY_MIN_FAMILIES` y la trazabilidad en admin; el **Tier A**, la whitelist extendida y el KPI formal pueden requerir **tareas de ingeniería adicionales** fuera del checklist T-246…T-257.

---

## Objetivo

Este documento consolida las decisiones finales para cerrar el frente **F2** dentro de **S6.3**, evitando mantener abierta la discusión en formato exploratorio.

El foco de este cierre es dejar definido:

- qué significa completitud mínima del pool,
- qué exige la elegibilidad oficial,
- qué bloques de SportMonks son obligatorios o deseables,
- cómo tratar lineups y `available: false`,
- qué familias de mercado deben estar soportadas en datos,
- cómo se medirá el cierre real de F2,
- y cuál será el universo oficial inicial de ligas objetivo.

---

## Alcance de este cierre

Con este documento se cierra **F2** en el sentido de:

- definición de completitud mínima,
- definición de elegibilidad oficial,
- definición de bloques mínimos de soporte en datos,
- y criterio operativo para medir cierre.

No se cierra aquí:

- política de frescura / refresh / regeneración de snapshot,
- variedad de mercados en la señal o mezcla de picks,
- UX, preview, DP o comportamiento de exposición al usuario.

Esos temas quedan fuera de este cierre porque pertenecen a fases y frentes posteriores.

---

# 1. Completitud mínima por liga

## Decisión

Se adopta una **regla canónica global única** de completitud mínima para todo el sistema.

Sobre esa base podrá existir un único endurecimiento adicional para **Tier A**, reservado a las ligas objetivo del producto con mejor cobertura y mayor prioridad operativa.

## Criterio

- No se adopta una matriz distinta por liga individual en esta etapa.
- La completitud mínima no se define para inflar el porcentaje elegible, sino para que el evento tenga una base de dato defendible.
- El modelo de gobernanza será:
  - **Tier Base**: regla canónica global
  - **Tier A**: regla reforzada

## Implicación

La completitud mínima será comparable, auditable y fácil de leer en admin.

---

# 2. Qué bloques de SportMonks son obligatorios

## Decisión

Se adopta un esquema de bloques **mínimos**, **reforzados** y **opcionales**.

## Tier Base — bloques mínimos

Para considerar que un evento está mínimamente soportado, deberán existir:

- fixture válido,
- odds válidas,
- familias mínimas de mercado requeridas,
- y ausencia de faltantes críticos en `ds_input`.

## Tier A — bloques reforzados

Para eventos de Tier A se exigirá, además de lo anterior:

- `raw` obligatorio,
- mayor exigencia de soporte de mercados,
- y `lineups` cuando la cobertura real de la liga lo permita de forma estable.

## Bloques opcionales

Permanecen como opcionales los enriquecimientos de SM o del builder que no cambian todavía ni la elegibilidad ni la trazabilidad mínima.

## Implicación

No se adopta una política de “todo lo que entrega SM es obligatorio”.
Se exige solo lo necesario para sostener elegibilidad, auditoría y base mínima del modelo.

---

# 3. Tratamiento de lineups y de `available: false`

## Decisión

Un evento **sin lineup** podrá seguir siendo elegible en el **Tier Base** mientras cumpla la regla oficial de elegibilidad vigente.

El lineup no será requisito universal; será un requisito reforzado de **Tier A** en ligas donde la cobertura real lo permita.

## Regla operativa

- **Tier Base**:
  - lineup deseable,
  - no bloqueante por sí solo.
- **Tier A**:
  - lineup exigible solo en ligas donde exista cobertura estable.

## Interpretación de `available: false`

`available: false` no se interpretará automáticamente como exclusión.
Significa que ese bloque no está disponible o no es usable en esa evaluación.

## Efecto operativo

- si afecta un bloque **opcional o deseable**, degrada calidad/score,
- si afecta un bloque **obligatorio** del tier, excluye,
- si deriva en una causal oficial de elegibilidad, excluye por esa causal.

## Distinción obligatoria en auditoría

La auditoría debe distinguir entre:

- dato ausente temporalmente,
- dato no soportado por la fuente,
- dato no propagado o no normalizado internamente,
- bloque no requerido para ese tier.

---

# 4. Soporte de familias de mercado en snapshot y `ds_input`

## Decisión

El soporte mínimo de mercados en datos no se definirá por el catálogo comercial completo de SportMonks, sino por una **whitelist operativa pequeña y validable**.

## Familias mínimas en `bt2_odds_snapshot`

Se define como whitelist core inicial:

- `FT_1X2` (obligatoria)
- `OU_GOALS_2_5`
- `BTTS`
- `DOUBLE_CHANCE`

## Requisito mínimo de soporte

Para elegibilidad base se exigirá:

- `FT_1X2` obligatorio,
- más **una familia core adicional**.

## Reglas para `ds_input`

`ds_input` deberá exigir únicamente las familias que realmente soportan:

- elegibilidad,
- auditoría,
- y señal base.

No todo lo que entre al snapshot será automáticamente obligatorio en builder.

## Restricción explícita

No se adopta todavía una familia única universal obligatoria como `OU_GOALS_2_5` para todo el sistema.
La lógica será:

- `FT_1X2` + 1 familia core adicional

## Implicación

Esto mantiene el estándar de al menos 2 familias sin convertir la elegibilidad en una regla demasiado rígida para el estado actual del stack.

---

# 5. Regla oficial final de elegibilidad

## Decisión

La regla oficial actual no se reemplaza; **evoluciona** a una versión refinada manteniendo su estructura como **filtro duro**.

## Regla oficial

La referencia oficial seguirá exigiendo:

- fixture válido,
- odds válidas,
- **mínimo 2 familias de mercado**,
- ausencia de faltantes críticos de `ds_input`.

## Modo relajado

Se mantiene una versión relajada exclusivamente para observabilidad interna:

- mínimo 1 familia,
- solo diagnóstico,
- nunca como KPI oficial.

## Filtro duro vs score

- **Verdad oficial**: filtro duro
- **Capa auxiliar opcional**: score de completitud

## Lineups y raw

- **Tier Base**:
  - raw deseable,
  - lineup deseable.
- **Tier A**:
  - raw obligatorio,
  - lineup obligatorio solo cuando la liga lo soporte de forma estable.

## Mínimo de familias

Se mantiene en **2** como valor oficial.
El valor **1** queda solo como modo relajado de observabilidad.

---

# 6. KPI final de cierre de F2

## Decisión

El KPI principal de cierre de F2 será el **`pool_eligibility_rate_official`**, medido únicamente con la **regla oficial canónica**.

## Definición

`eligible_events_count / candidate_events_count`

calculado con la regla oficial de elegibilidad.

## Métricas secundarias obligatorias

El KPI principal se acompañará de:

- breakdown de causas de descarte,
- cobertura por familias core,
- cobertura de `raw`,
- cobertura de `lineups.available`,
- y comparación contra el modo relajado.

## Ventana de validación

La validación de cierre se hará sobre:

- las **5 ligas objetivo del producto**,
- ventana de **30 días**,
- lectura agregada,
- lectura por liga,
- y lectura sobre días operativos con picks reales.

## Umbral propuesto de cierre

Se propone considerar F2 cerrado cuando:

- el KPI oficial agregado alcance al menos **60%**, y
- ninguna liga objetivo quede por debajo de **40%**, y
- `INSUFFICIENT_MARKET_FAMILIES` deje de ser una causa dominante estructural.

## Candados anti-maquillaje

Para evitar mejoras aparentes producto de relajar la regla:

- siempre se reportará **oficial vs relajado**,
- se revisará el mix de descartes,
- y se medirán por separado las coberturas reales de familias, `raw` y `lineups`.

---

# 7. Selección inicial de las 5 ligas objetivo

## Decisión

Se adopta como set inicial oficial de producto el siguiente grupo de 5 ligas:

1. Premier League
2. LaLiga
3. Serie A
4. Bundesliga
5. Ligue 1

## Justificación

Este set se elige por maximizar simultáneamente:

- valor de producto,
- regularidad competitiva,
- volumen útil de eventos,
- probabilidad de mejor cobertura en SM,
- y estabilidad operativa para una primera versión defendible.

## Criterio de arquitectura

Esta decisión **no implica** que SportMonks haya quedado validado definitivamente como proveedor óptimo de odds a largo plazo.

Sí implica que:

- estas 5 ligas serán el universo oficial sobre el cual se medirá la completitud,
- sobre estas 5 se evaluará el KPI de cierre de F2,
- y sobre estas 5 se decidirá si SM estándar da la talla o si más adelante debe reabrirse la mejora de proveedor independiente de odds.

## Restricción

No se seguirá abriendo en S6.3 la discusión sobre cuáles ligas elegir entre las 120 disponibles.
La selección oficial inicial queda cerrada con estas 5.

---

# Resultado de cierre

Si se adopta este documento, F2 quedará cerrado a nivel de decisiones con este alcance:

- completitud mínima definida,
- bloques mínimos y reforzados definidos,
- política de lineups y `available: false` definida,
- familias core de mercado definidas,
- regla oficial de elegibilidad definida,
- KPI de cierre definido,
- universo oficial inicial de 5 ligas definido.

## Qué quedará resuelto

- qué eventos merecen entrar al pool oficial,
- bajo qué nivel de soporte mínimo en datos,
- cómo distinguir base vs Tier A,
- y cómo medir si realmente mejoró la completitud del sistema.

## Qué quedará pendiente para fases posteriores

- política de frescura / refresh / regeneración,
- discusión avanzada de variedad de mercados en la señal,
- y decisiones de UX/preview/DP.

---

# Resumen ejecutivo

Con estas decisiones, BT2 queda con una postura operativa clara:

- la verdad oficial sigue gobernada por filtro duro,
- la elegibilidad exige 2 familias como estándar oficial,
- el sistema no se degrada a puro 1X2,
- el modo relajado existe solo para observabilidad,
- Tier A se endurece con `raw` y lineups cuando aplique,
- y el universo inicial de producto queda acotado a 5 ligas oficiales.

Esto permite cerrar F2 de manera defendible sin mezclar todavía temas de frescura o variedad avanzada de señal.

---

# Anexo — Validación frente al código (2026-04-15)

Este anexo **no** reabre el texto normativo de arriba: solo documenta **qué parte ya existe en el repo** frente a cada bloque, para no confundir **decisión aprobada** con **implementación completa**.

Leyenda: **Sí** = alineado de forma clara · **Parcial** = existe algo relacionado pero no cubre la norma entera · **No** = no está implementado como aquí se describe · **N/A** = fuera de código (proceso/manual).

| Bloque normativo | Estado en código / producto actual | Notas breves |
|------------------|-------------------------------------|--------------|
| §1 Tier Base vs Tier A como **gobernanza de elegibilidad** | **Parcial** | Hay `SelectionTier` A/B en `ds_input` y `premium_tier_eligible` / tiers de liga en CDM, pero **`bt2_pool_eligibility_v1` no aplica reglas distintas “Tier A”** (raw obligatorio, más mercados) frente a Base. |
| §2 Bloques SM mínimos vs reforzados | **Parcial** | Pool v1 exige fixture, odds utilizables (`event_passes_value_pool`), familias y faltantes críticos en `ds_input`. **No** hay rama “Tier A = raw obligatorio + lineups obligatorios por liga” en la misma regla. |
| §3 Lineups / `available: false` | **Parcial** | Faltantes críticos (p. ej. marcadores de lineups/raw en diagnostics) pueden descartar; **no** hay auditoría con los cuatro subtipos de §3 (ausente vs fuente vs normalización vs no requerido). |
| §4 Whitelist core (`FT_1X2`, `OU_GOALS_2_5`, `BTTS`, `DOUBLE_CHANCE`) | **Parcial** | Agregación y `market_diversity_family` reconocen esas familias. La regla v1 pide **≥ N familias distintas** con cobertura; **`event_passes_value_pool`** pide al menos **un** mercado canónico completo (no exige explícitamente **FT_1X2 obligatorio + una core adicional** como filtro duro antes del conteo). |
| §5 Regla oficial 2 familias + modo relajado 1 | **Sí** / **Parcial** | Umbral **2** y env `BT2_POOL_ELIGIBILITY_MIN_FAMILIES` para observabilidad: **Sí**. **“Nunca como KPI oficial”** para modo 1: **Parcial** (el admin muestra umbral activo vs referencia; el KPI sigue saliendo de auditoría calculada con ese umbral si se re-ejecuta el job). |
| §6 KPI `pool_eligibility_rate_official` + secundarias + ventana 30d + 5 ligas + umbrales 60%/40% | **Parcial** / **No** | Existe `poolEligibilityRatePct` (misma idea operativa). **No** hay campo nominal `_official` separado de serie “relajada” en paralelo; **no** hay job/report automático 30d sobre las 5 ligas con umbrales 60/40; breakdown de descartes **sí** en admin; coberturas agregadas raw/lineups como KPI de cierre **no** como en §6. |
| §7 Las **5 ligas** como universo oficial de medición | **Parcial** | `bt2_leagues` + tiers en normalizador; filtro opcional `BT2_PRIORITY_LEAGUE_IDS`. **No** está cableado como “solo estas 5 por ID” para el KPI de cierre F2 descrito aquí. |

**Conclusión:** este archivo **sí** cierra **decisiones de producto/datos** para F2; **no** implica que todo lo descrito esté ya implementado y medido en producción. El cierre operativo **S6.3 core** (`DECISIONES_CIERRE_S6_3.md`, evidencia en `EJECUCION.md`) es **otra capa**: demostró pipeline con datos reales, no cumplimiento íntegro de la norma F2 de este documento.

**Backlog ejecutable (tareas T-258…T-266):** [`TASKS_CIERRE_F2_S6_3.md`](./TASKS_CIERRE_F2_S6_3.md) · [`US_CIERRE_F2_S6_3.md`](./US_CIERRE_F2_S6_3.md) · [`HANDOFF_CIERRE_F2_S6_3.md`](./HANDOFF_CIERRE_F2_S6_3.md). Propuesta de texto largo (GPT / remoto): [`PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md`](./PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md).

*Añadido: 2026-04-15 — auditoría honesta repo vs norma.*  
*Actualización: 2026-04-15 — enlaces al paquete de backlog F2.*

**Actualización implementación 2026-04-15:** las tareas **T-258–T-264** quedaron implementadas en repo (constantes 5 ligas, regla `pool-eligibility-f2-v1`, métricas/API `f2-pool-eligibility-metrics`, script `job_f2_closure_report.py`). Evidencia de primer run y notas: [`EJECUCION_CIERRE_F2_S6_3.md`](./EJECUCION_CIERRE_F2_S6_3.md). La tabla del anexo superior describe el estado *previo* a este corte; el cierre de producto sobre umbrales 60/40 sigue siendo **dato de entorno**, no automáticamente “OK” al merge.

---

## Anexo (b) — Validación post-implementación T-258–T265 (repo, 2026-04-15)

Tabla **sustitutiva del estado de implementación** respecto a la tabla histórica de arriba. No modifica el texto normativo de §1–§7.

| Bloque normativo | Estado en código actual | Notas |
|------------------|-------------------------|--------|
| §1 Tier Base vs Tier A | **Parcial** | Tier **A** = ligas del universo F2 (`f2_pool_tier_label` en `bt2_f2_league_constants.py`); refuerzo **raw** obligatorio en A (`_ds_input_critical_f2`). “Mayor exigencia de mercados” vs Base **no** codificada como umbral extra. |
| §2 Bloques SM mínimos vs reforzados | **Parcial** | Raw/lineups vía `ds_input` + regla `pool-eligibility-f2-v1`. `available: false` por bloque SM **no** mapeado 1:1 a causal; se usa `lineups_ok` / `raw_fixture_missing`. |
| §3 Auditoría fina | **Parcial** | `causal_audit_class` en `detail_json` (`bt2_pool_eligibility_v1.py`); heurística, no las cuatro etiquetas literales §3. |
| §4 Whitelist FT_1X2 + 1 core | **Sí** | `_f2_core_whitelist_satisfied` + conteo familias cuando `official_style`. |
| §5 Oficial vs relajado | **Sí** / **Parcial** | KPI F2 recalcula oficial `min_fam=2` vs relajado `min_fam=1` (`bt2_f2_metrics.py`). Job batch `job_pool_eligibility_audit.py` **persiste siempre** con `min_fam=2` oficial (el env `BT2_POOL_ELIGIBILITY_MIN_FAMILIES` no altera filas append-only). |
| §6 KPI + secundarias + 30d + 5 ligas + 60/40 | **Parcial** | Endpoint + script **30d**; umbrales 60/40 en payload (**meta acta**, no bloqueo S6.3). Candidatos = **`bt2_events`** en 5 ligas con kickoff en ventana (fecha **America/Bogota**); `core_family_coverage_counts` incluye raw/lineups. Ver [`EJECUCION_CIERRE_F2_S6_3.md`](./EJECUCION_CIERRE_F2_S6_3.md) § acuerdos. |
| §7 Cinco ligas | **Sí** | `bt2_f2_league_constants.py` + env `BT2_F2_OFFICIAL_LEAGUE_IDS`. |
| §6 lectura admin / T-265 | **Sí** | `AdminFase1OperationalPage.tsx` bloque F2 + `fetchBt2AdminF2PoolEligibilityMetrics`. |
