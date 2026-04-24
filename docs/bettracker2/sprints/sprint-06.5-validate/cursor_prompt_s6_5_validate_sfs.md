# Prompt único para Cursor — Reescritura completa Sprint 06.5 Validate SFS

Quiero que actúes en este repo como **Arquitecto + Business Analyst + Project Manager** de BT2.

## Reglas de trabajo
- hablar en español
- ser claro, directo y conciso
- usar el repo y los documentos como fuente de verdad, no el chat
- convertir definición -> decisiones -> backlog -> ejecución
- no reabrir discusiones ya cerradas sin evidencia nueva
- mantener nomenclatura y estructura documental del repo
- **NO arrastrar contenido de los docs actuales del sprint si contradicen esta nueva definición**

Repo fuente de verdad:
`https://github.com/kevcast95/sport-betting-analytics`

---

## Instrucción principal

Quiero que **vacíes y reescribas desde cero** los documentos activos del sprint actual de validación SFS.

No quiero rastro de la versión anterior dentro de los archivos activos.
No quiero textos “legacy”, disclaimers de que fue superseded, ni dejar trazas documentales dentro de los docs del sprint.
No quiero mezclar premisas viejas con la nueva percepción del problema.

Reescribe de punta a punta, alineado únicamente con esta nueva definición.

### Archivos a reescribir desde cero
En la carpeta activa del sprint de validación SFS, reescribe como mínimo:
- `PLAN.md`
- `DECISIONES.md`
- `US.md`
- `TASKS.md`
- `EJECUCION.md`

Si el sprint actual está en `sprint-06.5-validate`, mantén esa carpeta para evitar churn de paths.
Pero en el contenido el sprint debe quedar explícitamente enfocado como:

**Sprint 06.5 — Validate SFS**

No abras FE/UI salvo que esta instrucción lo diga explícitamente. En este caso **queda fuera**.

---

## Contexto correcto del problema

BT2 ya cerró Fase 0 y el cierre extendido de Fase 1/F2 en S6.3.

La premisa anterior que empujaba S6.4/F3 quedó cuestionada:
- asumíamos que SportMonks completaba markets cerca al kickoff
- eso justificaba una política compleja de refresh/frescura
- la evidencia reciente sugiere que ese no es necesariamente el problema dominante

Lo que ahora queremos validar es otra cosa:
- SportMonks no garantiza por sí solo toda la riqueza de markets aunque tenga add-on
- SofaScore parece mostrar más riqueza en varios casos
- V1 probablemente subcapturó parte de esa riqueza por cómo estaban hechos ciertos processors y persistencia

### Pero atención
No quiero que el sprint dependa de V1 como sistema en funcionamiento.
**V1 NO es runtime dependency.**

V1 solo puede servir para:
- entender endpoints o shapes
- acelerar discovery histórico
- validar si algunos `sofascore_event_id` ya existen en SQLite para bootstrap auxiliar

Pero **BT2 debe tener su propia arquitectura**, su propio provider SFS, sus propios scrapers/fetchers, sus propios processors/mappers y su propia persistencia experimental.

No quiero una solución apoyada operativamente en SQLite V1.

---

## Objetivo real del sprint

Definir y ejecutar un sprint que permita responder con evidencia si:

1. SofaScore sirve como **fuente experimental** de odds/markets para BT2.
2. BT2 puede operar **al menos 1 semana experimental adicional con SFS** y observar resultados reales respecto a markets.
3. Existe una **capa canónica agnóstica a proveedor** suficiente para que luego podamos integrar The Odds API sin rehacer el core.
4. El problema principal deja de ser “refresh complejo por completitud tardía” y pasa a ser “fuente + modelado canónico + cobertura real”.

### Lo que NO es este sprint
- no aprueba fallback productivo
- no sustituye automáticamente a SportMonks
- no cambia el truth source oficial productivo
- no mete UI/FE
- no cierra F3 por decreto; solo deja evidencia para simplificarla, mantenerla pendiente o sostener backlog previo con justificación

---

## Nueva percepción obligatoria del sprint

Este sprint debe quedar definido bajo estas premisas obligatorias:

### A. Cohorte base y fuente de verdad del experimento
- La cohorte base del experimento sale de **BT2/Postgres**, no de V1/SQLite.
- La cohorte operativa sigue gobernada por **SM/CDM** porque hoy BT2 modela eventos desde ahí.
- V1/SQLite puede usarse **solo** como bootstrap auxiliar para validar si ya existen IDs/event refs históricos de SFS, pero jamás como dependencia operativa del sprint.

### B. Ventana de análisis
No dejar una ventana ambigua.
La definición correcta es:
- **6 días UTC cerrados** hacia atrás
- **más el día actual UTC**
- para el día actual se permite un **job temporal controlado en staging** con cierre a las `00:00 UTC` del día siguiente

Esto existe para poder observar también comportamiento “en tiempo real” de los providers durante un día completo.

### C. Dos modos de trabajo dentro del sprint
El sprint debe quedar explícitamente dividido en dos caminos compatibles:

#### 1) Historical bootstrap 6d
Objetivo:
- reconstruir y comparar los últimos 6 días cerrados
- acelerar validación histórica

Permisos:
- se puede revisar SQLite V1 para ver si ya existen IDs/event refs SFS
- si existen, se pueden usar como **seed auxiliar**
- si no existen, BT2 debe resolverlos por su propia cuenta

Pero el pipeline de fetch/mapping/persistencia debe ser BT2, no V1.

#### 2) Daily experimental path
Objetivo:
- observar el día actual en staging
- validar comportamiento real de cobertura de markets intra-día

Regla:
- usar cohorte BT2/SM del día
- resolver equivalencia a SFS
- consultar odds SFS
- persistir y comparar
- cortar el experimento al cierre UTC definido

---

## Arquitectura obligatoria para SFS en BT2

No quiero depender de carpetas o jobs legacy de V1 como base operativa.

Quiero un provider/estructura propia de BT2 para SofaScore.

### Requisito arquitectónico
Crear o dejar definida una estructura propia tipo una de estas dos opciones:
- `apps/api/bt2/providers/sofascore/`
- o `apps/api/bt2sfs/`

La estructura debe reflejar que BT2 tiene su propia línea SFS, separada del legacy.

### Componentes mínimos esperados
Debe quedar documentado y reflejado en US/TASKS que el provider SFS de BT2 tendrá al menos:
- resolución de eventos / join a SFS
- fetch de odds SFS
- separación por `source_scope`
- mapeo canónico provider -> mercado/selección canónica
- persistencia experimental
- reportes de validación / comparación
- shadow path hacia `ds_input`

### Endpoints mínimos obligatorios en S6.5
El sprint debe dejar cerrado que solo son obligatorios:
- `odds/1/featured`
- `odds/1/all`

Nada más es obligatorio para cerrar este sprint.

### Regla featured vs all
No mezclar raw sin control.
La regla correcta es:
- `featured` y `all` se guardan y reportan separados en plano raw
- ambos pueden unificarse **solo después** del mapeo canónico
- la unificación debe ser deduplicada y trazable con `source_scope`
- queda prohibido publicar un KPI crudo único que mezcle `featured` y `all` sin breakdown

---

## Modelo canónico obligatorio para S6.5

No quiero un catálogo gigante.
Quiero un canónico pequeño, útil y suficiente para decidir el sprint.

### Familias canónicas v0 obligatorias
- `FT_1X2`
- `OU_GOALS_2_5`
- `BTTS`
- `DOUBLE_CHANCE`

### Definición oficial de “evento útil”
Un evento útil para este sprint es:
- evento con `FT_1X2` completo
- **y** al menos **1 familia core adicional completa**

Eso debe quedar textual en `DECISIONES.md`, `US.md` y `EJECUCION.md`.

---

## Comparabilidad SM vs SFS

### Definición oficial de `% match`
No quiero ambigüedad.

Definir `% match` así:

`match_rate = eventos_BT2_en_cohorte_ejecutada_con_join_SFS_valido / total_eventos_BT2_en_cohorte_ejecutada`

Esto significa:
- el denominador es la cohorte BT2/SM ejecutada
- el numerador son los eventos de esa cohorte que BT2 logró resolver contra SofaScore

NO es:
- la unión de todos los eventos de ambos proveedores
- ni “todos los eventos existentes en SM y SFS”

### Estrategia oficial de join
Debe quedar cerrada una estrategia priorizada de 3 capas:
1. match directo por metadata o IDs si existe
2. matching determinista por competición + equipos + kickoff UTC
3. tabla de overrides manuales para excepciones

No dejar esto como alternativas abiertas. Debe quedar como estrategia oficial del sprint.

### Bucket no comparable
Los `no comparable` deben:
- existir como bucket explícito
- quedar fuera del denominador del KPI principal de cobertura comparada
- pero sí bloquear un veredicto `GO` si superan cierto umbral

### Umbrales oficiales
Déjalos cerrados así:
- `% match >= 85%` -> comparación válida
- `% match 70%–84%` -> diagnóstico útil, pero insuficiente para `GO`
- `% match < 70%` -> el sprint deriva en problema de matching, no de cobertura

Además:
- `no comparable > 15%` bloquea `GO`

### KPI principal del sprint
La unidad principal de comparación debe ser:

**% de eventos comparables con `FT_1X2` completo + al menos 1 familia core adicional**

Secundarios:
- `solo SM / solo SFS / ambos / ninguno`
- breakdown por liga si el volumen lo permite
- breakdown de join miss / no comparable / descartes

---

## Persistencia experimental obligatoria

### Ruta principal
La persistencia v0 del experimento debe vivir en **Postgres BT2 staging/experimental**, no en SQLite como base principal.

### Naming
Quiero naming concreto, no tentativo.

Usa como entidad/tabla principal algo equivalente a:
- `bt2_provider_odds_snapshot`

Y para shadow path algo equivalente a:
- `bt2_dsr_ds_input_shadow`

Si el repo exige otro prefijo consistente, ajústalo, pero no dejes nombres tentativos en docs.

### Retención
Retener toda la evidencia del sprint:
- durante el sprint
- hasta el cierre del acta
- y 30 días más

### Idempotencia
Definir criterio explícito de idempotencia, por ejemplo:
- clave lógica por `(bt2_event_id, provider, source_scope, run_id)`
- si se reejecuta el mismo `run_id`, hacer upsert/overwrite controlado
- toda métrica debe referenciar un `run_id` concreto

---

## Scrapers / fetchers dedicados SFS

Debes dejar explícito en las US/TASKS que S6.5 valida un **scraper/fetcher dedicado BT2-SFS**.

### Muy importante
No quiero que el sprint quede redactado como “reutilizar processors legacy” o “depender de V1”.

Quiero esto:
- BT2 entiende el funcionamiento base de V1
- BT2 toma lo útil conceptualmente
- BT2 implementa su **propio fetch/mapping/persistencia experimental** para SFS

### Qué sí puede hacer V1
Solo bootstrap auxiliar:
- revisar si los IDs/event refs históricos ya existen en SQLite
- si existen, usarlos para acelerar el historical bootstrap 6d

### Qué NO puede hacer V1
- no puede ser truth source
- no puede ser pipeline operativo del sprint
- no puede ser requisito para el flujo diario futuro

---

## Shadow `ds_input`

### Regla
Debe existir camino shadow, pero sin tocar prod.

### Ubicación
Definir como tabla/path shadow consultable, no solo archivo suelto.

### Metadata obligatoria en shadow payload
Como mínimo:
- `experimental=true`
- `odds_provider`
- `truth_source`
- `provider_event_ref`
- `provider_snapshot_run_id`
- `ingested_at_utc`
- `canonical_version`

### Compatibilidad mínima exigida
El experimento debe demostrar:
- **1 fixture end-to-end** para prueba de shape y trazabilidad
- **mini cohorte de 20 eventos comparables** para revisar compatibilidad con el `ds_input` actual

Los placeholders deben documentarse, pero no deben invalidar el experimento si el fragmento odds-driven ya funciona.

---

## UI / FE

Queda totalmente fuera en S6.5.
No abras FE, no abras `US-FE-*`, no abras vistas admin nuevas para este sprint.
Todo el cierre debe ser por:
- docs
- queries
- JSON/CSV
- evidencia en `EJECUCION.md`

---

## Gobernanza, presupuesto y operación

### US-OPS
No dejarlo opcional.

Debes incluir una historia operativa obligatoria equivalente a:
- presupuesto de llamadas
- límite de uso
- responsable
- checklist de apagado
- control del job temporal del día actual

### Responsables
Dejar claro:
- **PO/PM** = accountable del presupuesto y aprobación del uso experimental
- **TL/Arquitecto** = responsible del throttling, caps, diseño técnico y cumplimiento técnico de la restricción

Si hay que dejar un solo owner formal, usar PO.

---

## Veredicto final obligatorio del sprint

No quiero cierre ambiguo.

Debe quedar una regla explícita `GO / PIVOT / NO-GO`.

### GO
Solo si se cumple todo esto:
- `% match >= 85%`
- `no comparable <= 15%`
- SFS en el KPI principal no queda peor que SM por más de `5 pp`
- el shadow `ds_input` queda probado
- el costo/cupos del piloto son operables al menos para 1 semana experimental adicional

### PIVOT
Si pasa esto:
- el join es usable pero insuficiente para `GO`, o
- el raw de SFS parece prometedor pero el cuello está en mapping / processor / canónico / bootstrap

### NO-GO
Si pasa alguno de estos:
- `% match < 70%`, o
- SFS queda materialmente peor que SM por más de `10 pp` en el KPI principal, o
- falla la prueba mínima de shadow path, o
- el costo/operación del piloto no permite sostener una semana adicional razonable

---

## Impacto esperado sobre F3

No cierres F3 por decreto.
Deja explícitamente solo estas tres salidas posibles al cierre de S6.5:

1. **F3 se simplifica**
   - si la evidencia muestra que el cuello dominante era fuente/modelado, no refresh tardío

2. **F3 sigue pendiente con nueva premisa**
   - si el resultado es mixto o condicionado por matching/cobertura parcial

3. **Se mantiene backlog previo con justificación**
   - solo si la evidencia demuestra que el problema dominante sigue siendo refresh/completitud temporal

---

## The Odds API

No quiero implementación en este sprint.
Sí quiero conclusión mínima de arquitectura.

Debe quedar una frase explícita equivalente a:

**“El seam quedó listo a nivel de contrato, metadatos, persistencia y path de integración; falta adapter específico para The Odds API.”**

---

## Qué quiero que produzcas en los docs

### 1) `PLAN.md`
Debe quedar corto, ejecutivo y sin ambigüedad.
Debe incluir:
- objetivo real del sprint
- por qué cambió la percepción del problema
- alcance / fuera de alcance
- ventana híbrida `6 días cerrados + día actual`
- dos caminos: `historical bootstrap 6d` y `daily experimental path`
- criterio de cierre del sprint
- objetivo adicional explícito: determinar si se puede operar **1 semana más** con SFS experimental y ver resultados reales respecto a markets

### 2) `DECISIONES.md`
Reescribir desde cero las decisiones del sprint con numeración continua.
Quiero decisiones normativas claras como mínimo sobre:
- naturaleza experimental del sprint
- cohorte BT2/Postgres como base
- V1 solo como bootstrap auxiliar, no runtime dependency
- provider propio BT2-SFS
- endpoints obligatorios
- regla `featured` vs `all`
- canónico v0 y definición de evento útil
- definición de `% match`
- estrategia oficial de join
- bucket `no comparable`
- persistencia experimental y shadow path
- UI fuera
- regla `GO/PIVOT/NO-GO`
- posibles salidas sobre F3
- seam preparado para The Odds API

### 3) `US.md`
Quiero US suficientes para bajar backlog de punta a punta.
No quiero relleno.
Quiero historias concretas que cubran al menos:
- DX del canónico v0 y alias provider
- persistencia experimental multi-provider
- provider/adapter BT2-SFS
- historical bootstrap 6d
- daily experimental fetch del día actual
- join/resolución BT2 ↔ SFS
- job de métricas comparativas
- shadow `ds_input`
- operación/presupuesto/kill switch
- cierre ejecutivo del sprint

### 4) `TASKS.md`
Quiero tasks secuenciadas y ejecutables, no genéricas.
El backlog debe cubrir de punta a punta:
- relectura/reframing documental
- creación estructura provider SFS BT2
- validación/uso opcional de IDs históricos de V1 como bootstrap
- implementación fetchers `featured` y `all`
- persistencia por `source_scope`
- mapping canónico
- join y overrides
- corrida histórica 6d
- corrida día actual UTC con control temporal
- cálculo de métricas
- shadow `ds_input`
- documentación operativa
- acta final `GO/PIVOT/NO-GO`

### 5) `EJECUCION.md`
Debe quedar listo para ejecución real, no como plantilla vacía.
Quiero:
- kickoff con campos ya cerrados, no pendientes
- ventana exacta
- universo base
- cap de eventos/día
- estrategia de join
- fórmula del KPI principal
- definición de `% match`
- bucket `no comparable`
- umbrales de veredicto
- secciones para registrar corridas `historical bootstrap` y `daily path`
- sección final para decidir si se puede operar **1 semana más** con SFS experimental

---

## Importante: no quiero ambigüedad residual

Antes de escribir, revisa si en tus borradores anteriores quedó alguna de estas ambigüedades y elimínala:
- depender de SQLite V1 como base del sprint
- ventana solo histórica sin día actual
- `% match` ambiguo
- join como “por definir”
- `featured` vs `all` mezclados sin regla
- canónico demasiado grande o indefinido
- processor legacy como núcleo del sprint
- shadow path sin metadata obligatoria
- FE/UI abierta por defecto
- US-OPS opcional
- veredicto final sin thresholds

---

## Entregable esperado

Quiero que edites los archivos del sprint y los dejes listos para que el backlog se pueda ejecutar sin reabrir la definición.

No me devuelvas una discusión larga.
Devuélveme:
1. resumen corto de qué reescribiste
2. lista de archivos tocados
3. cualquier punto que **objetivamente siga imposible de cerrar** solo si de verdad no se puede resolver con esta instrucción

Pero el objetivo es que **no quede nada ambiguo**.
