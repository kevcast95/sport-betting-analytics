# BT2 — Radiografía técnica actual y plan de hardening

Fecha: 2026-04-25  
Estado: documento de trabajo técnico  
Objetivo: consolidar, en un solo lugar, lo aprendido en las fases recientes de auditoría de BT2 y convertirlo en un plan de hardening concreto para ingesta, materialización, replay, evaluación oficial y analítica.

---

## 1. Resumen ejecutivo

BT2 ya pasó por una secuencia útil de auditorías técnicas que permitió descubrir y corregir varios problemas reales de integridad y semántica de datos.

Los hallazgos más importantes fueron:

- La evaluación oficial podía cerrar picks como `hit/miss` aunque el evento siguiera abierto o unresolved.
- `bt2_events` podía quedar en estados inconsistentes, por ejemplo `scheduled + scores`, o con drift entre raw y CDM.
- El replay/backtest actual no es parity replay fuerte con live; su comportamiento real corresponde a un **bounded replay** con corte temporal, scan cap y reglas propias de elegibilidad.
- El análisis de edge/selective release estuvo inicialmente contaminado por faltantes de `reference_decimal_odds`, problema que ya fue auditado y corregido para la ventana reciente.
- La muestra útil actual para selective release real sigue siendo muy pequeña.
- Para 2025 no existen picks históricos reales en esta base, pero sí existe suficiente raw para explorar un modo histórico reconstruido usando timestamps por línea de SportMonks (`latest_bookmaker_update`), siempre que se documente explícitamente como **exploratory historical replay** y no como parity replay.

Conclusión general:

BT2 está en mejor estado que al inicio, pero todavía necesita hardening estructural en contratos de datos, timestamps, persistencia de odds de referencia, trazabilidad de exclusiones y separación clara entre:

- live operativo
- bounded replay
- cohortes backfill
- histórico exploratorio reconstruido

---

## 2. Estado técnico actual por fase

### Fase 1 — auditoría operativa inicial

Qué se auditó:

- raw reciente del proveedor
- `bt2_odds_snapshot`
- `bt2_events`
- señales generales de consistencia operacional

Qué se descubrió:

- sí existía raw reciente y snapshots recientes en la ventana auditada
- `bt2_events` mostraba deuda real:
  - unresolved prolongados
  - algunos `finished` sin score
  - señales de materialización/cierre inconsistente

Lectura técnica:

Fase 1 dejó claro que no bastaba con mirar si “hay data”; había que validar cómo se estaba materializando y usando esa data aguas abajo.

---

### Fase 2 — linaje, drift y evaluación oficial

Qué se auditó:

- raw vs `bt2_events`
- `bt2_events` vs evaluación oficial
- estado de cierre, score y coherencia de verdad oficial

Hallazgos clave:

- había evaluaciones oficiales cerradas sobre eventos unresolved
- existía drift entre raw y `bt2_events`
- apareció el patrón `score + scheduled`
- hubo inconsistencias entre `truth_source = bt2_events_cdm` y estado real del evento

Resultado práctico:

De aquí salieron los fixes más importantes del ciclo.

---

## 3. PRs y correcciones ya ejecutadas

### PR A — Official evaluation integrity

Problema:

La evaluación oficial podía liquidar `hit/miss` usando score persistido aunque el evento no estuviera realmente cerrado.

Cambio aplicado:

- el resolver oficial pasó a exigir estado de cierre válido para liquidar
- si el evento seguía abierto o unresolved, quedaba `pending_result`
- se reabrieron históricamente filas mal cerradas

Impacto:

- se eliminó el patrón de evaluación cerrada sobre eventos abiertos en la ventana auditada
- se recuperó integridad lógica entre estado del evento y evaluación oficial

Hardening derivado:

- nunca cerrar por score solamente
- score y estado deben concordar
- toda reevaluación histórica debe ser conservadora y trazable

---

### PR B — Materialización de estados live/finished en `bt2_events`

Problema:

La normalización de fixtures colapsaba demasiados casos a `scheduled`, mientras otros caminos ya persistían marcador.

Cambio aplicado:

- mejor lectura de `state_id` / `state.id`
- mejora de detección de `finished`
- mapeo de estados in-play observados en raw a `live`

Impacto:

- se redujo fuerte el patrón `scheduled + scores`
- mejoró la alineación entre raw del proveedor y estado materializado en el CDM

Hardening derivado:

- el mapeo de estado debe ser explícito, versionado y testeado
- el parser de estado y el parser de score no pueden vivir como si fueran universos independientes

---

### PR C — Residual NS + placeholder 0-0

Problema:

Fixtures `NS` podían persistir `0-0` placeholder como si fuera marcador real.

Cambio aplicado:

- se evitó persistir `0-0` placeholder bajo `NS/scheduled`
- se limpió `0-0` stale acotado en upserts scheduled

Impacto:

- se cerró el residual puntual de materialización detectado después de PR B

Hardening derivado:

- no toda presencia de score en raw implica score operativo utilizable
- hay que distinguir placeholder, score parcial y score real

---

## 4. Fase 3 — Replay parity / decision trace

### Qué se auditó

Se auditó el funnel real del replay para explicar por qué `candidateEvents > eligibleEvents` y qué parte del flujo tumbaba eventos antes del DSR.

### Hallazgos clave

Las principales causas del gap entre candidatos y elegibles fueron:

- `no_odds_before_cutoff`
- `beyond_scan_cap`
- `value_pool_fail`

También se confirmó que el replay actual:

- tiene corte temporal de odds
- tiene límite de barrido
- fuerza ciertas decisiones que no equivalen al flujo live

### Conclusión de fase

El replay actual **no es parity replay fuerte**. Es un **bounded replay** con semántica propia.

### Mejora aplicada

Se creó tooling read-only para dejar la primera causa de exclusión por evento trazable y reproducible.

Hardening derivado:

- siempre distinguir entre “candidato del universo” y “evento preparado para DSR”
- siempre poder explicar por qué un evento no avanzó

---

## 5. Fase 3B — bounded replay explícito

Problema:

La semántica de `candidateEvents`, `eligibleEvents` y del propio replay inducía a pensar en parity replay cuando en realidad el comportamiento era acotado y diferente al live.

Cambio aplicado:

- documentación explícita del replay como `bounded_backtest`
- metadatos descriptivos en `replay_meta`
- aclaración de la semántica de `candidate_events`, `eligible_events`, scan limit y cutoff

Hardening derivado:

- las métricas deben tener nombres semánticamente honestos
- la API debe explicitar el contrato del modo de replay

---

## 6. Fase 4 — Selective release / edge audit sobre picks reales recientes

### Qué se intentó

Buscar subconjuntos ex-ante con mejor desempeño que el agregado global.

### Metodología fijada

Se congeló una metodología inicial con:

- segmentos fijos
- métricas fijas
- mínimos de N
- reglas de estabilidad temporal
- anti-tuning explícito

### Hallazgo crítico inicial

`reference_decimal_odds` estaba incompleto en la ventana reciente, contaminando ROI, break-even y odds promedio.

---

## 7. Fase 4B — auditoría y backfill de `reference_decimal_odds`

### Hallazgo

Buena parte de los picks scored no tenían `reference_decimal_odds` usable por deuda histórica / falta de backfill.

### Cambio aplicado

- se auditó el circuito completo de `reference_decimal_odds`
- se ejecutó un backfill controlado para la ventana reciente

### Resultado

La cobertura pasó de parcial a completa en esa ventana y el análisis dejó de estar sesgado por faltantes de cuota.

### Lección

Si BT2 quiere usar ROI, break-even o bandas de cuota como parte de un edge audit serio, `reference_decimal_odds` no puede ser “best effort”; debe ser un campo persistentemente confiable y auditable.

---

## 8. Estado actual de selective release

### Qué quedó probado

Con metodología congelada y odds ya completas, el universo útil reciente sigue siendo demasiado pequeño.

Resultado honesto:

- no hay señal robusta todavía
- no hay segmentos “prometedores” bajo discovery/validation congelado
- la conclusión correcta hoy es negativa o, como mínimo, no concluyente

### Interpretación

El cuello de botella actual ya no es de odds faltantes ni de metodología; es de tamaño real de muestra.

Hardening derivado:

- evitar sobreajuste por tuning en muestras pequeñas
- no mover segmentos ni bandas post-hoc
- mantener discovery/validation congelado mientras no aumente N

---

## 9. Fase 3C — emulabilidad histórica 2025 desde raw

### Pregunta correcta

No era “¿hay picks 2025 persistidos?”, sino:

> ¿Podemos usar los raw y datos históricos de 2025 para emular el flujo diario completo en backtest?

### Hallazgos

- `bt2_daily_picks` no tiene picks 2025 en esta BD
- `bt2_odds_snapshot` para eventos 2025 tiene `fetched_at` backfilleado en 2026, por lo que no sirve como verdad ex-ante para el replay actual
- `raw_sportmonks_fixtures` sí tiene información útil 2025 y timestamps por línea (`latest_bookmaker_update`, `created_at`) que sí pueden usarse como señal temporal exploratoria

### Veredicto

2025 quedó clasificado como:

**B — emulable con caveats fuertes**

No sirve para el replay actual, pero sí abre la puerta a un modo histórico exploratorio basado en timestamps por línea de SM.

---

## 10. Fase 3C.2 — contrato temporal para histórico exploratorio

### Objetivo

Determinar qué cutoff temporal era más defendible para reconstruir odds históricas desde raw SM.

### Resultado

El contrato recomendado fue:

**T−60**  
Usar solo líneas con `latest_bookmaker_update <= kickoff_utc - 60 minutos`

### Hallazgo clave

- el problema no era usar line timestamps
- el problema era un cutoff demasiado agresivo tipo día previo
- T−60 mantuvo buena cobertura y estabilidad del consenso

Hardening derivado:

- si se construye un replay histórico desde raw, el contrato temporal debe ser explícito y congelado
- no puede mezclarse con el bounded replay actual sin nombre distinto y advertencias claras

---

## 11. Fase 3C.3 — prototipo `historical_sm_lbu`

### Qué se construyó

Un prototipo mínimo, aislado y read-only que:

- toma eventos/fixtures 2025
- lee `raw_sportmonks_fixtures`
- filtra líneas por T−60
- reutiliza el agregador actual
- calcula `value_pool`
- no usa `bt2_odds_snapshot.fetched_at`
- se marca explícitamente como:
  - `mode = historical_sm_lbu`
  - `live_parity = false`
  - `exploratory_only = true`

### Resultado

El prototipo ya funciona de punta a punta y escala razonablemente a lotes moderados.

Conclusión:

Esta ruta ya no está en modo “idea”; ya es una base técnica válida para un replay histórico exploratorio, separado del bounded replay actual.

---

## 12. Radiografía técnica actual: principales frentes de hardening

### 12.1 Integridad de verdad oficial

Estado actual:

- Mejoró mucho con PR A
- El resolver ya no debe cerrar sobre eventos abiertos

Riesgo remanente:

- cualquier nuevo flujo que use score sin validar estado puede reintroducir el bug

Acción concreta:

- mantener tests de cierre estricto
- validar regularmente que no reaparezcan evaluaciones sobre abiertos
- añadir chequeo automático en auditorías recurrentes

---

### 12.2 Materialización de `bt2_events`

Estado actual:

- Los principales bugs ya fueron corregidos con PR B y C

Riesgo remanente:

- drift futuro entre raw y CDM si cambian proveedores o semántica de estado

Acción concreta:

- mantener tabla/capa de mapeo de estados explícita
- separar placeholder score de score operativo
- auditar regularmente `scheduled + scores`, `finished + null score`, `live + stale result`

---

### 12.3 Contrato temporal de odds

Estado actual:

- El live y el bounded replay actual dependen de semánticas distintas
- 2025 demostró que `fetched_at` backfilleado no sirve como verdad ex-ante

Riesgo remanente:

- confundir snapshot operativo con backfill histórico
- mezclar cohortes temporales incompatibles

Acción concreta:

- definir y documentar claramente tres modos:
  1. live operativo
  2. bounded replay
  3. historical SM LBU exploratorio
- nunca mezclar métricas entre esos modos sin explicitar equivalencia limitada

---

### 12.4 Persistencia de `reference_decimal_odds`

Estado actual:

- el circuito ya fue auditado
- hubo backfill exitoso para la ventana reciente

Riesgo remanente:

- volver a insertar picks con `reference_decimal_odds = NULL`
- depender de backfills ad hoc

Acción concreta:

- convertir `reference_decimal_odds` en campo operativamente confiable
- añadir logging/metric cuando no se pueda poblar
- dejar un backfill oficial e idempotente
- incorporar control de cobertura por ventana y por fuente

---

### 12.5 Trazabilidad de exclusión del funnel

Estado actual:

- ya existe tooling para explicar primera causa de exclusión

Riesgo remanente:

- perder esa trazabilidad si cambia el replay o si se agregan nuevas reglas sin instrumentación

Acción concreta:

- mantener un artefacto estándar con causas como:
  - beyond_scan_cap
  - no_odds_before_cutoff
  - value_pool_fail
  - prepared_for_dsr
- exponerlo o persistirlo en modo admin o script recurrente

---

### 12.6 Semántica de candidatos/elegibles

Estado actual:

- ya se aclaró que `candidate_events` y `eligible_events` del replay no equivalen al live pool real

Riesgo remanente:

- que producto, QA o analítica vuelvan a leer estas métricas con semántica equivocada

Acción concreta:

- mantener docs y metadatos del replay
- usar naming más explícito en outputs y dashboards
- distinguir siempre:
  - universo candidato
  - pasa value pool
  - preparado para DSR
  - pick final emitido

---

### 12.7 Selective release / edge audit

Estado actual:

- metodología inicial congelada y limpia
- sin señal robusta todavía

Riesgo remanente:

- sobreajuste por muestra pequeña
- reabrir tuning oportunista

Acción concreta:

- no tocar segmentos ni bandas mientras no aumente N
- rerunear con más muestra futura o cohortes históricas explícitamente documentadas
- si se usa histórico exploratorio 2025, marcarlo como señal exploratoria, no prueba productiva definitiva

---

## 13. Plan de acción específico

### Prioridad P0 — integridad y contratos operativos

#### P0.1 — Formalizar contratos de tiempo y modo

Qué resolver:

- distinguir claramente live, bounded replay y historical SM LBU

Acciones:

- documentar cada modo con contrato temporal y limitaciones
- agregar metadatos obligatorios en outputs/scripts/API admin cuando aplique:
  - `mode`
  - `cutoff_mode`
  - `live_parity`
  - `exploratory_only`
  - `temporal_truth`

Resultado esperado:

- nadie vuelve a confundir bounded replay con parity replay
- nadie vuelve a tratar cohortes backfill como evidencia ex-ante operativa

---

#### P0.2 — Hardening de `reference_decimal_odds`

Qué resolver:

- evitar faltantes futuros y simplificar analítica

Acciones:

- instrumentar write path para detectar `ref_odds = None`
- crear métrica/alerta de cobertura por operating_day_key
- dejar script oficial de backfill idempotente
- generar reporte periódico de cobertura de odds en picks scored

Resultado esperado:

- edge audit reproducible y sin sesgo por faltantes de cuota

---

### Prioridad P1 — observabilidad y trazabilidad

#### P1.1 — Trazabilidad de exclusión por evento

Qué resolver:

- explicar consistentemente por qué eventos no avanzan en el funnel

Acciones:

- consolidar script/artefacto que produzca primera causa de exclusión por `event_id`
- dejar output compacto y reusable
- enlazarlo con runbooks internos

Resultado esperado:

- diagnóstico rápido cuando `candidateEvents > eligibleEvents`
- menos discusión ambigua sobre si “el modelo descartó” algo que en realidad nunca llegó al modelo

---

#### P1.2 — Auditorías recurrentes de consistencia CDM

Qué resolver:

- prevenir regresiones en estado/score/evaluación

Acciones:

- automatizar chequeos mínimos:
  - `scheduled + scores`
  - `finished + null result`
  - official eval sobre abiertos
  - drift raw vs `bt2_events`
- generar summary recurrente

Resultado esperado:

- detectar regresiones antes de que contaminen análisis o producto

---

### Prioridad P2 — histórico exploratorio 2025+

#### P2.1 — estabilizar `historical_sm_lbu`

Qué resolver:

- convertir el prototipo en herramienta histórica exploratoria más utilizable

Acciones:

- correr por bloques mensuales/semanales 2025
- generar summaries compactos por bloque
- medir estabilidad operativa del modo
- documentar limitaciones metodológicas

Resultado esperado:

- saber si 2025 es suficientemente estable para exploración más grande

---

#### P2.2 — decidir si se escala a lotes históricos grandes

Qué resolver:

- determinar si vale la pena batch histórico completo o si el costo metodológico no lo justifica

Acciones:

- consolidar meses 2025
- evaluar cobertura, VP, estabilidad y drift entre bloques
- decidir si se abre “historical SM LBU batch replay”

Resultado esperado:

- decisión explícita: escalar o frenar

---

### Prioridad P3 — selective release futuro

#### P3.1 — no mover metodología hasta tener más N

Qué resolver:

- evitar sobreajuste prematuro

Acciones:

- congelar segmentos, bandas y umbrales actuales
- rerunear solo cuando aumente muestra o exista cohorte histórica bien definida

Resultado esperado:

- disciplina metodológica
- menos riesgo de autoengaño estadístico

---

#### P3.2 — reintento de edge audit solo cuando cambie el universo

Qué resolver:

- no repetir análisis idéntico sobre el mismo N sin valor nuevo

Acciones:

- gatillar rerun cuando:
  - aumenten `hit/miss`
  - disminuya `pending_result`
  - se habilite cohorte histórica exploratoria utilizable

Resultado esperado:

- selective release basado en evidencia nueva, no en reiteración de la misma muestra

---

## 14. Qué conviene hacer cuando se reactive SportMonks

Cuando vuelva la ingesta normal, el protocolo debería ser más estricto que antes.

### Recomendaciones concretas

1. **Preservar tiempo útil de ingesta**  
   No colapsar backfills tardíos en un `fetched_at` indistinguible de snapshot operativo.

2. **Separar snapshot operativo vs backfill**  
   Dejar bandera o semántica explícita para distinguir ambos.

3. **Guardar suficiente granularidad temporal**  
   Idealmente por snapshot o por línea, no solo por consolidación final.

4. **Validar `reference_decimal_odds` al persistir picks**  
   Si falta, registrar por qué.

5. **Mantener trazabilidad de elegibilidad**  
   Toda exclusión debería tener una primera causa trazable.

6. **No reutilizar nombres ambiguos**  
   `candidate`, `eligible`, `replay`, `historical`, `live_parity`, `exploratory_only` deben tener significado explícito.

7. **Backfills con contrato claro**  
   Todo backfill debe dejar documentado si es compatible o no con análisis ex-ante.

---

## 15. Estado actual resumido

### Ya resuelto o muy mejorado

- official evaluation sobre abiertos
- materialización principal de estados live/finished
- residual NS + 0-0 placeholder
- semántica de bounded replay
- cobertura reciente de `reference_decimal_odds`
- trazabilidad básica de exclusión en replay
- prototipo histórico exploratorio basado en LBU + T−60

### Todavía abierto

- hardening completo de ingesta al reactivar SM
- observabilidad recurrente de consistency checks
- decisión de escalar histórico exploratorio 2025 por bloques
- selective release con evidencia robusta (todavía no)

---

## 16. Recomendación final

No seguir mezclando todas las preguntas en una sola línea de trabajo.

Separar explícitamente estos frentes:

1. **Hardening operativo de ingesta y contratos**  
2. **Observabilidad / auditoría recurrente**  
3. **Replay histórico exploratorio 2025+**  
4. **Selective release / edge audit**, solo cuando el universo ya sea suficiente y comparable

La idea no es “hacer más cosas”, sino evitar que una mejora analítica se base en una base semánticamente frágil.

En este momento, BT2 ya tiene suficiente aprendizaje para pasar de auditoría reactiva a hardening deliberado.

