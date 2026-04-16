# Propuesta integrada — cierre extendido de F2 dentro de S6.3

> Documento de trabajo para actualizar directamente los artefactos del sprint sin tener que fusionar manualmente el delta.
> 
> Base usada:
> - `DECISIONES_CIERRE_F2_S6_3_FINAL.md`
> - `DECISIONES_CIERRE_S6_3.md`
> - `US_CIERRE_S6_3.md`
> - `TASKS_CIERRE_S6_3.md`
> - `HANDOFF_CIERRE_S6_3.md`
>
> Objetivo:
> - traer el contenido objetivo completo de cada archivo,
> - conservar lo vigente que sí sigue aplicando,
> - integrar lo nuevo del cierre extendido de F2 dentro de S6.3,
> - y dejar una guía operativa clara para BE / FE / documentación.
>
> **Backlog ejecutable en repo (2026-04-15):** el trabajo priorizado para F2 extendido está en [`TASKS_CIERRE_F2_S6_3.md`](./TASKS_CIERRE_F2_S6_3.md), [`US_CIERRE_F2_S6_3.md`](./US_CIERRE_F2_S6_3.md) y [`HANDOFF_CIERRE_F2_S6_3.md`](./HANDOFF_CIERRE_F2_S6_3.md). Este MD sigue siendo útil como **texto largo** y catálogo; no sustituye decisiones PO en [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).

---

## 0. Criterio de uso de este documento

Este documento está pensado para que puedas:

1. copiar y pegar el contenido completo propuesto por archivo,
2. reemplazar el contenido actual del repo local donde aplique,
3. evitar revisar línea por línea qué mover, qué conservar y qué agregar.

### Regla de integración

- `DECISIONES_CIERRE_S6_3.md` → reemplazar por la versión objetivo de este documento.
- `US_CIERRE_S6_3.md` → reemplazar por la versión objetivo de este documento.
- `TASKS_CIERRE_S6_3.md` → reemplazar por la versión objetivo de este documento.
- `HANDOFF_CIERRE_S6_3.md` → reemplazar por la versión objetivo de este documento.
- `EJECUCION.md` → no reemplazar completo desde aquí; insertar el bloque nuevo propuesto al final del frente F2 o como sección nueva de cierre extendido.

---

# 1. Contenido objetivo completo — `DECISIONES_CIERRE_S6_3.md`

```md
# Sprint 06.3 — DECISIONES_CIERRE

> Jerarquía: norte y fases en `ROADMAP_PO_NORTE_Y_FASES.md`; backlog maestro del sprint en `PLAN.md`.
> Base vigente del sprint: `DECISIONES.md`, `US.md`, `TASKS.md`, `EJECUCION.md`.
> Documento base de este cierre: `CIERRE_RESTANTE_S6_3.md`.
> Base aprobada previa: `CIERRE_FASE_0_MODELO_Y_METRICA_DATOS.md`.
> Convención alcance: D-06-023 (cambio en código → nueva US / decisión antes de merge).
> Fuente funcional adicional obligatoria para este cierre extendido: `DECISIONES_CIERRE_F2_S6_3_FINAL.md`.

* * *

## D-06-051 — El slice principal de Fase 1 no se considera cerrado sin evidencia operativa real (2026-04-14)

Contexto: S6.3 ya implementó el slice técnico principal de Fase 1, pero no basta con tener tabla/modelo, job, endpoint, vista, tests y build satisfactorios si no existe evidencia real del loop con picks existentes en entorno operativo.

Decisión:
  1. S6.3 no podrá declararse cerrado solo con implementación técnica del slice principal de Fase 1.
  2. Para cerrar realmente este frente deberá existir evidencia operativa real de que picks existentes en `bt2_daily_picks` generan fila en `bt2_pick_official_evaluation`.
  3. La evidencia mínima aceptable deberá mostrar, para un subconjunto real identificado por `operating_day_key`:
     * picks reales procesados,
     * filas reales en `bt2_pick_official_evaluation`,
     * al menos estado `pending_result` y, cuando aplique, estados evaluados reales,
     * y evidencia documentada del job o SQL usado.
  4. Si esa evidencia no existe, el sprint permanece en estado “implementado técnicamente, pero no cerrado operativamente”.

Trazabilidad: US-BE-053, US-BE-054, US-FE-062.

* * *

## D-06-052 — La elegibilidad y la vista admin solo cierran con datos reales no vacíos y consistentes (2026-04-14)

Contexto: El summary no puede darse por válido si domina el patrón “sin auditoría reciente”, y la vista `/v2/admin/fase1-operational` no puede considerarse cerrada si solo fue validada con estructura vacía o datos de prueba.

Decisión:
  1. La elegibilidad v1 y su auditoría no se considerarán cerradas solo porque la lógica exista en código.
  2. Para cerrar este frente deberá existir evidencia real de filas en `bt2_pool_eligibility_audit` sobre eventos reales de la ventana validada, con:
     * `is_eligible` o `primary_discard_reason`,
     * coverage real distinta de cero cuando aplique,
     * y desaparición del patrón dominante “sin auditoría reciente” como explicación principal.
  3. La vista admin de Fase 1 no se considerará validada mientras solo muestre estructura vacía o datos de prueba.
  4. La validación mínima de UI deberá probar consistencia entre:
     * BD,
     * endpoint summary,
     * y `/v2/admin/fase1-operational`,
     con datos reales no vacíos.

Trazabilidad: US-BE-054, US-FE-062.

* * *

## D-06-053 — El antiguo paralelo mínimo de F2 queda sustituido por el cierre extendido aprobado dentro de S6.3 (2026-04-15)

Contexto: La restricción anterior de tratar F2 solo como una validación mínima paralela quedó superada por la aprobación explícita del documento `DECISIONES_CIERRE_F2_S6_3_FINAL.md`, que baja el cierre completo de F2 todavía dentro de S6.3 y sin abrir S6.4.

Decisión:
  1. A partir de esta actualización, F2 ya no se trata en S6.3 como un “mínimo paralelo” limitado a una lectura exploratoria.
  2. Dentro de S6.3 se baja a backlog y ejecución el cierre extendido de F2, limitado a:
     * completitud mínima,
     * bloques obligatorios/reforzados/opcionales,
     * política de `lineups` y `available: false`,
     * familias core de mercado en snapshot y `ds_input`,
     * regla oficial final de elegibilidad,
     * KPI de cierre,
     * y universo oficial de 5 ligas objetivo.
  3. Esta ampliación no abre un sprint nuevo ni autoriza arrastrar frentes posteriores.
  4. Siguen fuera de alcance dentro de S6.3:
     * política de frescura / refresh / regeneración,
     * mix avanzado de señal,
     * UX futura,
     * F3 / F4 / F5,
     * y rediseños laterales no exigidos por el cierre de F2.

Trazabilidad: US-BE-055, US-BE-056, US-BE-057, US-FE-062.

* * *

## D-06-054 — El cierre formal de S6.3 exige evidencia documental explícita en `EJECUCION.md` y `TASKS.md` (2026-04-14)

Contexto: El cierre real de S6.3 requiere que el pendiente final no solo exista operativamente, sino que quede evidenciado y trazado en los documentos de ejecución del sprint.

Decisión:
  1. S6.3 solo podrá cerrarse formalmente cuando `EJECUCION.md` documente explícitamente:
     * evidencia de loop oficial para picks reales,
     * evidencia de auditoría de elegibilidad sobre eventos reales,
     * evidencia de la vista admin con datos no vacíos,
     * y resultado del cierre extendido de F2.
  2. `TASKS.md` deberá reflejar ese cierre restante con tasks finales marcables y evidencia enlazada.
  3. Si durante la validación real aparece una brecha operativa bloqueante, el sprint no se cierra por intención; deberá quedar como pendiente explícito o nueva task antes del cierre formal.
  4. La resolución final permitida para S6.3 será solo una de estas dos:
     * “cerrado realmente”, con evidencia completa;
     * o “implementado pero no cerrado operativamente”, con brecha explícita documentada.

Trazabilidad: US-BE-053, US-BE-054, US-BE-055, US-BE-056, US-BE-057, US-FE-062.

* * *

## D-06-055 — La completitud mínima oficial se define con una regla canónica global y un refuerzo adicional para Tier A (2026-04-15)

Contexto: El cierre aprobado de F2 define que la completitud mínima ya no se evaluará con lecturas aisladas por liga/mercado piloto, sino mediante una regla canónica comparable y auditable.

Decisión:
  1. Se adopta una regla canónica global única de completitud mínima para todo el sistema.
  2. Sobre esa base podrá existir un único endurecimiento adicional para Tier A.
  3. El modelo oficial queda gobernado por:
     * Tier Base: regla canónica global,
     * Tier A: regla reforzada sobre ligas objetivo del producto.
  4. No se adopta en esta etapa una matriz distinta por liga individual.

Trazabilidad: US-BE-055, US-BE-056.

* * *

## D-06-056 — Los bloques de SportMonks se separan en mínimos, reforzados y opcionales (2026-04-15)

Contexto: El cierre aprobado de F2 exige una postura explícita sobre qué bloques de datos son realmente obligatorios para sostener elegibilidad, auditoría y base mínima del modelo.

Decisión:
  1. Se adopta un esquema oficial de bloques:
     * mínimos,
     * reforzados,
     * opcionales.
  2. Tier Base deberá exigir como mínimo:
     * fixture válido,
     * odds válidas,
     * familias mínimas de mercado requeridas,
     * y ausencia de faltantes críticos en `ds_input`.
  3. Tier A deberá exigir además:
     * `raw` obligatorio,
     * mayor exigencia de soporte de mercados,
     * y `lineups` cuando la cobertura real de la liga lo permita de forma estable.
  4. No se adopta una política de “todo lo que entrega SM es obligatorio”.

Trazabilidad: US-BE-055, US-BE-056.

* * *

## D-06-057 — `lineups` y `available: false` se interpretan por tier y por causal, no como exclusión automática universal (2026-04-15)

Contexto: El cierre aprobado de F2 exige distinguir explícitamente entre ausencia temporal, no soporte de fuente, no propagación interna y bloque no requerido por tier.

Decisión:
  1. Un evento sin lineup podrá seguir siendo elegible en Tier Base mientras cumpla la regla oficial de elegibilidad vigente.
  2. El lineup no será requisito universal; será exigible en Tier A solo cuando la cobertura real de la liga lo permita de forma estable.
  3. `available: false` no se interpretará automáticamente como exclusión.
  4. El efecto operativo será:
     * si afecta un bloque opcional o deseable, degrada calidad/score,
     * si afecta un bloque obligatorio del tier, excluye,
     * si deriva en una causal oficial de elegibilidad, excluye por esa causal.
  5. La auditoría deberá distinguir obligatoriamente entre:
     * dato ausente temporalmente,
     * dato no soportado por la fuente,
     * dato no propagado o no normalizado internamente,
     * bloque no requerido para ese tier.

Trazabilidad: US-BE-056, US-BE-057.

* * *

## D-06-058 — El soporte mínimo de mercados en snapshot y `ds_input` se define con una whitelist core pequeña y validable (2026-04-15)

Contexto: El cierre aprobado de F2 no amarra el sistema al catálogo comercial completo de mercados de SportMonks, sino a una whitelist operativa mínima y auditable.

Decisión:
  1. La whitelist core inicial en `bt2_odds_snapshot` queda definida como:
     * `FT_1X2` (obligatoria),
     * `OU_GOALS_2_5`,
     * `BTTS`,
     * `DOUBLE_CHANCE`.
  2. Para elegibilidad base se exigirá:
     * `FT_1X2` obligatorio,
     * más una familia core adicional.
  3. `ds_input` deberá exigir únicamente las familias que realmente soportan:
     * elegibilidad,
     * auditoría,
     * y señal base.
  4. No se adopta todavía una segunda familia universal única obligatoria para todo el sistema.

Trazabilidad: US-BE-055, US-BE-056.

* * *

## D-06-059 — La verdad oficial de elegibilidad permanece gobernada por filtro duro; el modo relajado es solo observabilidad (2026-04-15)

Contexto: El cierre aprobado de F2 mantiene la lógica oficial como filtro duro y evita maquillar la mejora relajando la elegibilidad oficial.

Decisión:
  1. La referencia oficial seguirá exigiendo:
     * fixture válido,
     * odds válidas,
     * mínimo 2 familias de mercado,
     * ausencia de faltantes críticos de `ds_input`.
  2. Se mantiene una versión relajada exclusivamente para observabilidad interna:
     * mínimo 1 familia,
     * solo diagnóstico,
     * nunca KPI oficial.
  3. Tier Base:
     * `raw` deseable,
     * lineup deseable.
  4. Tier A:
     * `raw` obligatorio,
     * lineup obligatorio solo cuando la liga lo soporte de forma estable.

Trazabilidad: US-BE-056, US-BE-057.

* * *

## D-06-060 — El KPI oficial de cierre de F2 será `pool_eligibility_rate_official` medido sobre 5 ligas / 30 días (2026-04-15)

Contexto: El cierre aprobado de F2 exige pasar de lectura exploratoria puntual a criterio de cierre medible y defendible.

Decisión:
  1. El KPI principal de cierre de F2 será `pool_eligibility_rate_official`.
  2. Su definición será:
     * `eligible_events_count / candidate_events_count`,
     * calculado únicamente con la regla oficial canónica.
  3. La validación de cierre se hará sobre:
     * las 5 ligas objetivo del producto,
     * ventana de 30 días,
     * lectura agregada,
     * lectura por liga,
     * y lectura sobre días operativos con picks reales.
  4. El umbral propuesto de cierre será:
     * agregado al menos 60%,
     * ninguna liga objetivo por debajo de 40%,
     * y `INSUFFICIENT_MARKET_FAMILIES` deja de ser una causa dominante estructural.
  5. Siempre se reportará oficial vs relajado como candado anti-maquillaje.

Trazabilidad: US-BE-057, US-FE-062.

* * *

## D-06-061 — El universo oficial inicial de F2 queda restringido a 5 ligas objetivo (2026-04-15)

Contexto: El cierre aprobado de F2 cierra explícitamente la discusión sobre universo inicial de ligas dentro de S6.3.

Decisión:
  1. Las ligas objetivo oficiales iniciales serán:
     * Premier League,
     * LaLiga,
     * Serie A,
     * Bundesliga,
     * Ligue 1.
  2. Estas 5 ligas serán el universo oficial sobre el cual se medirá la completitud y el KPI de cierre de F2.
  3. Esta decisión no valida definitivamente a SportMonks como proveedor óptimo de odds a largo plazo.
  4. Sí obliga a que el cierre de F2 dentro de S6.3 se mida exclusivamente sobre este set inicial.

Trazabilidad: US-BE-055, US-BE-057.

* * *

Creación: 2026-04-14 — decisiones puntuales para cierre real de S6.3.
Actualización: 2026-04-15 — ampliación aprobada para cierre extendido de F2 dentro de S6.3.
Pendiente siguiente artefacto: `US_CIERRE_S6_3.md`.
```

---

# 2. Contenido objetivo completo — `US_CIERRE_S6_3.md`

```md
# Sprint 06.3 — US_CIERRE

> Base normativa: `PLAN.md`, `DECISIONES.md`, `DECISIONES_CIERRE_S6_3.md`, `ROADMAP_PO_NORTE_Y_FASES.md`.
> Base vigente del sprint: `US.md`, `TASKS.md`, `EJECUCION.md`.
> Documento base de cierre: `CIERRE_RESTANTE_S6_3.md`.
> Fuente funcional adicional obligatoria: `DECISIONES_CIERRE_F2_S6_3_FINAL.md`.
> Contrato de formato US: `../../01_CONTRATO_US.md`.
> Numeración continua: BE desde `US-BE-053`; FE desde `US-FE-062`.
> Convención: cambios de alcance en código → nueva US o nueva DECISIÓN.

### Convención

Este documento no redefine Fase 0 ni abre S6.4.
Solo baja el cierre restante de S6.3 a ejecución real, separando:

* pendiente operativo de Fase 1,
* cierre extendido de F2 dentro de S6.3,
* y cierre documental honesto del sprint.

* * *

## Matriz de trazabilidad (decisiones → US)

Decisión | US
--- | ---
D-06-051 evidencia operativa real del loop | US-BE-053, US-BE-054, US-FE-062
D-06-052 elegibilidad + admin con datos reales | US-BE-054, US-FE-062
D-06-053 sustitución del paralelo mínimo por cierre extendido F2 | US-BE-055, US-BE-056, US-BE-057, US-FE-062
D-06-054 cierre formal documentado | US-BE-053, US-BE-054, US-BE-055, US-BE-056, US-BE-057, US-FE-062
D-06-055 completitud mínima Base/Tier A | US-BE-055, US-BE-056
D-06-056 bloques SM mínimos / reforzados / opcionales | US-BE-055, US-BE-056
D-06-057 política de `lineups` y `available: false` | US-BE-056, US-BE-057
D-06-058 whitelist core de mercados | US-BE-055, US-BE-056
D-06-059 elegibilidad oficial vs relajada | US-BE-056, US-BE-057
D-06-060 KPI oficial 5 ligas / 30 días | US-BE-057, US-FE-062
D-06-061 5 ligas objetivo oficiales | US-BE-055, US-BE-057

* * *

## Backend — cierre operativo real de Fase 1

### US-BE-053 — Operación real del loop oficial con picks reales

#### 1) Objetivo de negocio

Demostrar que la capacidad ya implementada de evaluación oficial por pick y cierre de loop funciona con picks reales del sistema, no solo con tests o fixtures.

#### 2) Alcance

* Incluye: validación de migraciones/tablas en entorno real; ejecución de job o backfill sobre uno o más `operating_day_key`; confirmación de filas en `bt2_pick_official_evaluation`; evidencia SQL o salida de job; documentación del subconjunto real procesado.
* Incluye: confirmación de estados reales al menos en `pending_result` y, cuando exista verdad oficial disponible, también estados evaluados.
* Excluye: rediseñar la lógica de evaluación; ampliar mercados fuera del subconjunto v1; recalcular PnL o settlement usuario.

#### 3) Dependencias

* Requiere que el slice principal de Fase 1 ya esté desplegado o disponible en el entorno validado.
* Requiere acceso a picks reales en `bt2_daily_picks`.

#### 4) Criterios de aceptación

1. Existe evidencia de un subconjunto real de picks identificado por `operating_day_key`.
2. Esos picks generan filas reales en `bt2_pick_official_evaluation`.
3. La evidencia muestra estados reales (`pending_result` y/o evaluados) sin depender de liquidación del usuario.
4. Queda documentado el comando/job/SQL utilizado para producir y verificar esa evidencia.

#### 5) Definition of Done

* Evidencia operativa real del loop anexada en `EJECUCION.md`.
* SQL o salida de job documentada.
* Estado del cierre reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: US-BE-049, US-BE-050.

* * *

### US-BE-054 — Operación real de elegibilidad/auditoría y validación backend del summary admin

#### 1) Objetivo de negocio

Demostrar que la capa de elegibilidad, su auditoría persistida y el summary admin funcionan con datos reales y producen lectura útil del sistema.

#### 2) Alcance

* Incluye: correr la auditoría de elegibilidad sobre eventos reales del día o ventana validada.
* Incluye: confirmación de filas reales en `bt2_pool_eligibility_audit` con `is_eligible` o `primary_discard_reason`.
* Incluye: validación del endpoint summary contra BD con datos no vacíos.
* Incluye: documentación del coverage real y de los motivos de descarte observados.
* Excluye: rediseño de la regla mínima; sistema avanzado de tiers; nueva arquitectura de datos.

#### 3) Dependencias

* Requiere US-BE-051 y US-BE-052 ya implementadas.
* Requiere ventana real con eventos candidatos suficientes para validar coverage.

#### 4) Criterios de aceptación

1. Existen eventos reales con filas en `bt2_pool_eligibility_audit`.
2. El patrón dominante “sin auditoría reciente” deja de ser la explicación principal en la ventana validada.
3. El summary admin refleja coverage real no vacío y consistente con BD.
4. Queda documentada la evidencia SQL y/o de endpoint usada para validar.

#### 5) Definition of Done

* Evidencia de auditoría real anexada en `EJECUCION.md`.
* Endpoint summary validado contra BD.
* Coverage y descarte real documentados para el cierre del sprint.

Madre: US-BE-051, US-BE-052.

* * *

## Backend — cierre extendido de F2 dentro de S6.3

### US-BE-055 — Contrato operativo F2 para snapshot, `ds_input` y universo oficial de medición

#### 1) Objetivo de negocio

Bajar a contrato operativo ejecutable el cierre de F2 dentro de S6.3, definiendo exactamente qué ligas, qué familias y qué soporte mínimo de datos se considerarán válidos para medir la completitud real del pool.

#### 2) Alcance

* Incluye: fijar como universo oficial de trabajo las 5 ligas objetivo aprobadas.
* Incluye: fijar la whitelist core inicial de familias de mercado.
* Incluye: fijar el requisito mínimo de soporte de mercados para elegibilidad base.
* Incluye: dejar explícito qué exige `ds_input` y qué no exige todavía.
* Excluye: catálogo comercial completo de mercados; snapshot/frescura; mezcla avanzada de señal; expansión fuera de las 5 ligas objetivo.

#### 3) Reglas de dominio

* Las 5 ligas oficiales iniciales son:
  * Premier League,
  * LaLiga,
  * Serie A,
  * Bundesliga,
  * Ligue 1.
* La whitelist core inicial será:
  * `FT_1X2` (obligatoria),
  * `OU_GOALS_2_5`,
  * `BTTS`,
  * `DOUBLE_CHANCE`.
* La elegibilidad base exigirá:
  * `FT_1X2`,
  * más una familia core adicional.
* `ds_input` exigirá únicamente las familias que realmente soportan elegibilidad, auditoría y señal base.

#### 4) Criterios de aceptación

1. Existe definición explícita y trazable del universo oficial de 5 ligas.
2. Existe definición explícita y trazable de la whitelist core de familias.
3. Existe validación real de cobertura por familia core y por liga objetivo en snapshot y/o capa equivalente.
4. Queda documentado qué exige `ds_input` para este cierre y qué queda fuera.

#### 5) Definition of Done

* Contrato operativo F2 documentado en `EJECUCION.md`.
* Evidencia por liga y por familia core anexada.
* Estado reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: D-06-055, D-06-056, D-06-058, D-06-061.

* * *

### US-BE-056 — Regla oficial refinada de elegibilidad y contrato de auditoría F2

#### 1) Objetivo de negocio

Convertir las decisiones de cierre de F2 en una regla operativa clara para elegibilidad y auditoría, sin relajar la verdad oficial y dejando explícito el tratamiento de tiers, `raw`, `lineups` y `available: false`.

#### 2) Alcance

* Incluye: formalizar la regla oficial final de elegibilidad.
* Incluye: mantener el modo relajado solo como observabilidad interna.
* Incluye: definir Tier Base y Tier A a nivel de soporte exigido.
* Incluye: fijar el tratamiento operativo de `raw`, `lineups` y `available: false`.
* Incluye: fijar la semántica mínima obligatoria de auditoría para distinguir causalidad de descarte.
* Excluye: score productizado al usuario; rediseño UX; decisiones de variedad de mercados en señal.

#### 3) Reglas de dominio

* La verdad oficial seguirá exigiendo:
  * fixture válido,
  * odds válidas,
  * mínimo 2 familias de mercado,
  * ausencia de faltantes críticos de `ds_input`.
* El modo relajado:
  * mínimo 1 familia,
  * solo diagnóstico,
  * nunca KPI oficial.
* Tier Base:
  * `raw` deseable,
  * lineup deseable.
* Tier A:
  * `raw` obligatorio,
  * lineup obligatorio solo cuando la cobertura real de la liga lo soporte de forma estable.
* La auditoría deberá distinguir al menos entre:
  * dato ausente temporalmente,
  * dato no soportado por la fuente,
  * dato no propagado o no normalizado internamente,
  * bloque no requerido para ese tier.

#### 4) Criterios de aceptación

1. La regla oficial final queda documentada y reflejada en la lectura operativa del sistema.
2. El modo relajado queda separado explícitamente del KPI oficial.
3. Queda definida la diferencia operativa entre Tier Base y Tier A.
4. La auditoría permite distinguir causalidad relevante de descarte y no tratar `available: false` como exclusión automática universal.

#### 5) Definition of Done

* Regla oficial y relajada documentadas en `EJECUCION.md`.
* Causalidad de auditoría descrita y evidenciada.
* Estado reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: D-06-056, D-06-057, D-06-059.

* * *

### US-BE-057 — Medición oficial y criterio de cierre real de F2 dentro de S6.3

#### 1) Objetivo de negocio

Medir el cierre real de F2 con un KPI oficial defendible y emitir una resolución explícita sobre si F2 queda realmente cerrado dentro de S6.3.

#### 2) Alcance

* Incluye: cálculo de `pool_eligibility_rate_official`.
* Incluye: lectura agregada y por liga.
* Incluye: comparación oficial vs relajado.
* Incluye: breakdown de causas de descarte.
* Incluye: cobertura por familias core, `raw` y `lineups.available`.
* Incluye: validación sobre ventana de 30 días y días operativos con picks reales.
* Excluye: decisiones de proveedor futuro; CLV; señal productizada; UX futura.

#### 3) Reglas de dominio

* El KPI principal será:
  * `eligible_events_count / candidate_events_count`.
* Se medirá con la regla oficial canónica.
* La ventana oficial será de 30 días.
* Debe existir lectura:
  * agregada,
  * por liga,
  * y sobre días operativos con picks reales.
* El umbral propuesto de cierre será:
  * agregado al menos 60%,
  * ninguna liga objetivo por debajo de 40%,
  * y `INSUFFICIENT_MARKET_FAMILIES` deja de ser causa dominante estructural.

#### 4) Criterios de aceptación

1. Existe cálculo explícito del KPI oficial agregado.
2. Existe lectura explícita por cada una de las 5 ligas objetivo.
3. Existe comparación oficial vs relajado.
4. Existe breakdown de descartes y lectura de coberturas auxiliares.
5. Se emite resolución final explícita: F2 cerrado realmente o implementado/documentado pero no cerrado operativamente.

#### 5) Definition of Done

* Evidencia de medición anexada en `EJECUCION.md`.
* Resolución final explícita documentada.
* Estado reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: D-06-057, D-06-059, D-06-060, D-06-061.

* * *

## Frontend

### US-FE-062 — Validación operativa de la vista admin con datos reales no vacíos y lectura de cierre F2 cuando backend ya la exponga

#### 1) Objetivo de negocio

Confirmar que la vista `/v2/admin/fase1-operational` funciona correctamente con datos reales, no vacíos y consistentes con backend y BD, y validar además la lectura de cierre F2 si backend ya la expone dentro del summary o ruta equivalente.

#### 2) Alcance

* Incluye: validación de la vista con datos reales provenientes del summary/backend.
* Incluye: revisión de candidatos, auditoría reciente, evaluación oficial y estados reales visibles.
* Incluye: validación de métricas F2 de cierre si backend ya las expone:
  * oficial vs relajado,
  * breakdown principal,
  * cobertura por familias core,
  * cobertura de `raw`,
  * cobertura de `lineups.available`,
  * agregado y por liga.
* Incluye: evidencia visual o funcional de consistencia con la capa backend validada.
* Excluye: cambios cosméticos grandes; nuevo dashboard; UX futura.

#### 3) Dependencias

* Requiere US-BE-053 y US-BE-054 al menos en versión operativa real.
* Requiere US-BE-057 si se espera validar lectura F2 desde backend.
* Requiere ruta admin desplegada o accesible en entorno validado.

#### 4) Criterios de aceptación

1. La vista muestra datos reales no vacíos.
2. La vista refleja al menos:
   * candidatos > 0,
   * con auditoría reciente > 0,
   * con fila evaluación oficial > 0,
   * y picks reales al menos en `pending_result` cuando aplique.
3. Si backend ya expone lectura F2, la vista permite validar consistencia básica de esa lectura sin abrir dashboard nuevo.
4. La lectura visual es consistente con endpoint y BD.
5. La evidencia funcional queda documentada para cierre del sprint.

#### 5) Definition of Done

* Validación visual/funcional anexada en `EJECUCION.md` o anexo asociado.
* Consistencia endpoint ↔ UI revisada.
* Estado final del frente reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: US-FE-061.

* * *

Última actualización: 2026-04-15 — backlog final de cierre real para S6.3 con ampliación aprobada de F2.
```

---

# 3. Contenido objetivo completo — `TASKS_CIERRE_S6_3.md`

```md
# Sprint 06.3 — TASKS_CIERRE

> Cierre restante de S6.3 tras implementación del slice principal de Fase 1.
> Numeración: continúa desde T-245 (S6.3). Rango actualizado de cierre: T-246 … T-261.
> Base vigente del sprint: `TASKS.md`, `US.md`, `EJECUCION.md`, `EJECUCION_UI_FASE1.md`.
> Documentos de cierre: `DECISIONES_CIERRE_S6_3.md`, `US_CIERRE_S6_3.md`, `HANDOFF_CIERRE_S6_3.md`.
> Foco: evidencia operativa real de Fase 1 + cierre extendido de F2 dentro de S6.3 + cierre documental honesto.

* * *

## Apto 100% para ejecución (Definition of Ready)

✓ Qué se confirma | Quién (típico)

- [ ] `CIERRE_RESTANTE_S6_3.md` leído y entendido como documento base del cierre restante. | PO / TL
- [ ] `DECISIONES_CIERRE_S6_3.md` aprobado antes de ejecutar tasks operativas de cierre. | PO / TL
- [ ] `DECISIONES_CIERRE_F2_S6_3_FINAL.md` leído y entendido como fuente funcional obligatoria del cierre extendido F2. | PO / TL / BE
- [ ] La implementación principal de Fase 1 ya está desplegada o accesible en el entorno donde se validará. | TL / BE
- [ ] Se definió la ventana real a usar para evidencia (`operating_day_key`, día o rango). | TL / BE
- [ ] Existe acceso a BD / logs / ruta admin para levantar evidencia real. | TL / BE / FE

* * *

## Checklist de cobertura cierre S6.3

Capa / decisión | US | Tareas
--- | --- | ---
Evidencia operativa real del loop | US-BE-053 | T-246–T-248
Evidencia operativa real de elegibilidad/auditoría | US-BE-054 | T-249–T-251
Contrato operativo F2 (ligas + whitelist + `ds_input`) | US-BE-055 | T-252–T-253
Regla oficial refinada + auditoría F2 | US-BE-056 | T-258–T-259
Medición oficial y resolución de cierre F2 | US-BE-057 | T-260–T-261
Validación admin con datos reales | US-FE-062 | T-254–T-255
Cierre documental del sprint | transversal | T-256–T-257

* * *

## US-BE-053

- [x] **T-246 (US-BE-053)** — Validar en entorno real que migraciones/tablas/código del loop oficial estén efectivamente disponibles para operar sobre picks reales.
- [x] **T-247 (US-BE-053)** — Ejecutar job o backfill de official evaluation sobre uno o más `operating_day_key` reales y confirmar filas en `bt2_pick_official_evaluation`.
- [x] **T-248 (US-BE-053)** — Documentar evidencia del loop con picks reales: SQL, salida de job, subconjunto procesado y estados observados (`pending_result`, evaluados si aplica).

* * *

## US-BE-054

- [x] **T-249 (US-BE-054)** — Ejecutar auditoría de elegibilidad sobre eventos reales del día o ventana validada y confirmar filas en `bt2_pool_eligibility_audit`.
- [x] **T-250 (US-BE-054)** — Validar endpoint summary/admin contra BD con datos reales no vacíos; confirmar coverage, auditoría reciente y consistencia básica.
- [x] **T-251 (US-BE-054)** — Documentar evidencia de elegibilidad/auditoría real: SQL, coverage observado, motivos de descarte y desaparición del patrón dominante “sin auditoría reciente”, si aplica.

* * *

## US-BE-055

- [ ] **T-252 (US-BE-055)** — Formalizar el contrato operativo F2 para las 5 ligas objetivo oficiales, la whitelist core de familias y el requisito `FT_1X2` + 1 familia core adicional.
- [ ] **T-253 (US-BE-055)** — Medir cobertura real por liga objetivo y por familia core en snapshot y/o capa equivalente; documentar además qué exige `ds_input` y qué gaps estructurales siguen abiertos para este cierre.

* * *

## US-BE-056

- [ ] **T-258 (US-BE-056)** — Bajar a lectura operativa la regla oficial final de elegibilidad y el modo relajado de observabilidad, manteniendo la verdad oficial como filtro duro de 2 familias.
- [ ] **T-259 (US-BE-056)** — Formalizar y evidenciar el tratamiento de Tier Base / Tier A, `raw`, `lineups` y `available: false`, incluyendo la semántica mínima obligatoria de auditoría por causal.

* * *

## US-BE-057

- [ ] **T-260 (US-BE-057)** — Ejecutar medición oficial de 30 días sobre Premier League, LaLiga, Serie A, Bundesliga y Ligue 1, con lectura agregada, lectura por liga y comparación oficial vs relajado.
- [ ] **T-261 (US-BE-057)** — Emitir resolución final de cierre F2 dentro de S6.3 usando el umbral aprobado: agregado ≥ 60%, ninguna liga < 40% y `INSUFFICIENT_MARKET_FAMILIES` deja de ser causa dominante estructural.

* * *

## US-FE-062

- [ ] **T-254 (US-FE-062)** — Validar `/v2/admin/fase1-operational` con datos reales no vacíos y revisar consistencia visual con summary/backend, incluyendo lectura F2 si backend ya la expone. *(Sin abrir dashboard nuevo.)*
- [ ] **T-255 (US-FE-062)** — Capturar evidencia funcional del admin: candidatos, auditoría reciente, evaluación oficial, estados visibles y, si existen en backend, oficial vs relajado, breakdown principal, cobertura core, `raw`, `lineups.available`, agregado y por liga.

* * *

## Gobernanza y cierre documental

- [ ] **T-256 (S6.3 transversal)** — Actualizar `EJECUCION.md` con evidencia real del loop, de elegibilidad/auditoría, de la vista admin y del cierre extendido F2: contrato de datos, regla oficial/refinada, medición 30 días, 5 ligas objetivo y resolución final.
- [ ] **T-257 (S6.3 transversal)** — Reflejar el cierre extendido en `DECISIONES_CIERRE_S6_3.md`, `US_CIERRE_S6_3.md`, `TASKS_CIERRE_S6_3.md` y `HANDOFF_CIERRE_S6_3.md`, dejando trazabilidad explícita del nuevo alcance aprobado dentro de S6.3.

* * *

## Check cierre real S6.3

- [x] Existe evidencia de loop oficial para un subconjunto real de picks.
- [x] Existe evidencia de auditoría de elegibilidad para eventos reales del día o ventana analizada.
- [ ] Existe contrato operativo explícito de F2 para 5 ligas objetivo, whitelist core y `ds_input` mínimo exigible.
- [ ] Existe regla oficial refinada de elegibilidad y causalidad de auditoría F2 claramente documentada.
- [ ] Existe medición oficial F2 de 30 días con lectura agregada, por liga y oficial vs relajado.
- [ ] La vista admin de Fase 1 muestra datos operativos no vacíos y consistentes con BD, y valida la lectura F2 si backend ya la expone.
- [ ] `EJECUCION.md` y `TASKS_CIERRE_S6_3.md` reflejan el cierre real del pendiente restante y del cierre extendido F2 dentro de S6.3.

* * *

Creación: 2026-04-14 — tasks finales para cierre real de S6.3.
Actualización: 2026-04-15 — tasks ampliadas para cierre extendido de F2 dentro de S6.3.
```

---

# 4. Contenido objetivo completo — `HANDOFF_CIERRE_S6_3.md`

```md
# Handoff — Cierre real Sprint 06.3

> Orden óptimo de ejecución para cerrar honestamente S6.3.
> Backlog de cierre: `TASKS_CIERRE_S6_3.md`.
> US: `US_CIERRE_S6_3.md`.
> Decisiones: `DECISIONES_CIERRE_S6_3.md`.
> Fuente funcional adicional obligatoria: `DECISIONES_CIERRE_F2_S6_3_FINAL.md`.
> Base de contexto: `CIERRE_RESTANTE_S6_3.md`.
> Este handoff no redefine el sprint: ordena la operación final y la evidencia del cierre extendido todavía dentro de S6.3.

* * *

## 0. Regla madre de este cierre

Lo pendiente ya no es construir nuevas capacidades principales.

Lo que falta es:

1. operar la capacidad ya construida con datos reales,
2. evidenciarla,
3. validar el admin con datos no vacíos,
4. y cerrar F2 completo dentro de S6.3 según el alcance ya aprobado.

Si durante la ejecución aparece una brecha operativa real, debe quedar documentada; no se maquilla el cierre.

* * *

## 1. Orden óptimo BE

### Paso 1 — Confirmar entorno real de validación
Tareas: T-246.

Qué debe quedar claro:
* qué entorno se usará,
* qué ventana real se validará,
* qué `operating_day_key` o rango se tomará como muestra.

Salida mínima:
* entorno identificado,
* ventana identificada,
* acceso a BD/job confirmado.

### Paso 2 — Demostrar loop oficial real
Tareas: T-247, T-248.

Objetivo:
* correr el job/backfill de official evaluation sobre picks reales,
* confirmar filas reales en `bt2_pick_official_evaluation`,
* documentar estados observados.

Reglas duras:
* no usar fixtures de test como evidencia principal,
* no depender de liquidación usuario,
* si solo hay `pending_result`, eso sirve como evidencia mínima si está bien trazado.

Salida mínima:
* SQL o salida de job,
* subconjunto real procesado,
* evidencia anexable a `EJECUCION.md`.

### Paso 3 — Demostrar elegibilidad/auditoría real
Tareas: T-249, T-250, T-251.

Objetivo:
* correr auditoría sobre eventos reales,
* confirmar filas en `bt2_pool_eligibility_audit`,
* validar summary admin contra BD.

Reglas duras:
* el patrón “sin auditoría reciente” no puede seguir siendo la lectura dominante en la ventana validada,
* no basta con decir “la lógica existe”; debe haber filas reales.

Salida mínima:
* coverage real observado,
* descarte por causa principal,
* consistencia BD ↔ endpoint documentada.

### Paso 4 — Formalizar contrato operativo F2
Tareas: T-252, T-253.

Objetivo:
* dejar fijo el universo oficial de 5 ligas,
* dejar fija la whitelist core de familias,
* dejar fijo el requisito `FT_1X2` + 1 familia core adicional,
* y evidenciar cómo eso vive en snapshot y `ds_input`.

Reglas duras:
* no abrir discusión nueva de ligas,
* no abrir catálogo comercial completo de mercados,
* no meter todavía snapshot/frescura,
* no inventar requisitos que el documento final no aprobó.

Salida mínima:
* contrato F2 documentado,
* cobertura por familia core,
* cobertura por liga objetivo,
* y nota explícita de qué exige `ds_input` para este cierre.

### Paso 5 — Bajar regla oficial refinada y causalidad F2
Tareas: T-258, T-259.

Objetivo:
* dejar operativa la diferencia entre regla oficial y modo relajado,
* dejar operativa la diferencia entre Tier Base y Tier A,
* y dejar explícito el tratamiento de `raw`, `lineups` y `available: false`.

Reglas duras:
* la verdad oficial sigue siendo filtro duro,
* el modo relajado no se usa como KPI,
* `available: false` no se trata como exclusión automática universal.

Salida mínima:
* regla oficial documentada,
* regla relajada documentada,
* semántica mínima de auditoría por causal,
* lectura operativa Base / Tier A clara.

### Paso 6 — Medir y resolver cierre F2
Tareas: T-260, T-261.

Objetivo:
* medir `pool_eligibility_rate_official` en ventana de 30 días,
* hacerlo sobre las 5 ligas objetivo,
* comparar oficial vs relajado,
* y emitir resolución final explícita.

Reglas duras:
* no usar cortes de 1 día como evidencia única,
* no mezclar ligas fuera del universo oficial,
* no declarar cierre solo por intuición o mejora aparente.

Salida mínima:
* KPI agregado,
* KPI por liga,
* breakdown de descartes,
* cobertura core / `raw` / `lineups.available`,
* resolución final documentada.

* * *

## 2. Orden óptimo FE

### Paso 1 — Esperar backend con datos reales
FE no debe validar la vista final usando solo mocks en este cierre.
El punto de arranque real FE es cuando BE ya tenga:
* evidence de loop,
* evidence de auditoría,
* contrato F2 documentado,
* y summary/backend con datos no vacíos.

### Paso 2 — Validar `/v2/admin/fase1-operational`
Tareas: T-254, T-255.

Checklist visual mínimo:
* candidatos > 0,
* con auditoría reciente > 0,
* con fila evaluación oficial > 0,
* picks reales visibles al menos en `pending_result` cuando aplique,
* consistencia con summary/backend.

Si backend ya expone lectura F2, validar además:
* oficial vs relajado,
* breakdown principal,
* cobertura core,
* `raw`,
* `lineups.available`,
* agregado y por liga.

Reglas duras:
* no mezclar pendientes o no evaluables dentro del hit rate,
* no corregir números en frontend,
* no bloquear el cierre por polish visual,
* no abrir dashboard nuevo en S6.3.

Salida mínima:
* evidencia funcional y/o screenshots útiles,
* consistencia UI ↔ endpoint ↔ BD reportada.

* * *

## 3. Orden conjunto de ejecución

### Secuencia recomendada

1. **BE**
   * T-246
   * T-247
   * T-248

2. **BE**
   * T-249
   * T-250
   * T-251

3. **BE**
   * T-252
   * T-253

4. **BE**
   * T-258
   * T-259

5. **BE**
   * T-260
   * T-261

6. **FE**
   * T-254
   * T-255

7. **Cierre conjunto**
   * T-256
   * T-257

* * *

## 4. Qué debe quedar en `EJECUCION.md`

`EJECUCION.md` debe salir de este cierre con cinco bloques explícitos:

1. evidencia de loop oficial real,
2. evidencia de auditoría/elegibilidad real,
3. evidencia de vista admin con datos no vacíos,
4. contrato operativo F2,
5. medición oficial y resolución final de cierre F2.

Si falta uno de esos cinco, S6.3 no queda cerrado realmente.

* * *

## 5. Sección nueva para el dev — qué cambió y qué ejecutar ahora

### Qué cambió respecto al handoff anterior

Antes, el handoff trataba F2 como un paralelo mínimo de validación.
Ahora, dentro de S6.3, el dev debe ejecutar el cierre extendido aprobado de F2 sin abrir otro sprint.

Eso significa que ya no basta con:
* medir coverage de un mercado piloto,
* emitir una nota corta,
* y declarar que “la regla actual se sostiene”.

Ahora sí hay que ejecutar además:
* contrato operativo de 5 ligas objetivo,
* whitelist core de familias,
* regla `FT_1X2` + 1 familia core adicional,
* distinción Base / Tier A,
* tratamiento formal de `raw`, `lineups` y `available: false`,
* KPI oficial de 30 días,
* y resolución explícita de cierre F2.

### Ruta exacta para BE

1. Confirmar que la medición y la evidencia se restringen a:
   * Premier League,
   * LaLiga,
   * Serie A,
   * Bundesliga,
   * Ligue 1.

2. Confirmar qué datos existen realmente para la whitelist core:
   * `FT_1X2`,
   * `OU_GOALS_2_5`,
   * `BTTS`,
   * `DOUBLE_CHANCE`.

3. Confirmar el criterio oficial base:
   * fixture válido,
   * odds válidas,
   * mínimo 2 familias,
   * sin faltantes críticos de `ds_input`.

4. Confirmar el criterio relajado solo para diagnóstico:
   * mínimo 1 familia,
   * nunca KPI oficial.

5. Confirmar qué parte de `raw`, `lineups` y `available: false`:
   * excluye,
   * degrada,
   * o no aplica según tier.

6. Correr medición de 30 días y documentar:
   * agregado,
   * por liga,
   * oficial vs relajado,
   * breakdown de descarte,
   * cobertura core,
   * cobertura `raw`,
   * cobertura `lineups.available`.

7. Emitir resolución final:
   * “F2 cerrado realmente dentro de S6.3”,
   * o “implementado/documentado pero no cerrado operativamente”.

### Ruta exacta para FE

1. No abrir nueva vista ni nuevo dashboard.
2. Validar la ruta actual con backend real.
3. Si backend ya trae lectura F2, validar que lo visible no contradiga la BD/endpoint.
4. Capturar evidencia clara de:
   * datos no vacíos,
   * consistencia,
   * y lectura F2 si existe en backend.

### Qué no hacer

No hacer en este cierre:
* snapshot/frescura,
* CLV,
* costo,
* UX futura,
* expansión fuerte de mercados,
* mezcla avanzada de señal,
* abrir S6.4,
* abrir F3 / F4 / F5.

* * *

## 6. Qué NO debe pasar ahora

No hacer en este cierre:

* snapshot/frescura,
* CLV,
* costo,
* UX futura,
* expansión fuerte de mercados,
* megaproyecto de completitud fuera del cierre aprobado,
* rediseño de producto lateral a F2,
* ni discusión nueva sobre qué ligas escoger.

Este handoff existe para **cerrar S6.3 honestamente**, no para agrandarlo sin control.

* * *

## 7. Resolución esperada

La salida correcta de este handoff debe terminar en una de estas dos conclusiones:

### A. S6.3 cerrado realmente
Con evidencia operativa real, admin validado, F2 cerrado según el alcance aprobado y documentación actualizada.

### B. S6.3 implementado pero no cerrado operativamente
Con brecha explícita documentada y sin fingir cierre.

* * *

Creación: 2026-04-14 — handoff de ejecución para cierre restante de S6.3.
Actualización: 2026-04-15 — handoff ampliado para cierre extendido de F2 dentro de S6.3.
```

---

# 5. Bloque nuevo propuesto para insertar en `EJECUCION.md`

> Nota: aquí no reemplazo el archivo completo porque en este trabajo no se cargó el contenido íntegro actual de `EJECUCION.md`. Lo correcto es insertar esta sección nueva después del bloque de evidencia actual o como subsección nueva de cierre extendido F2.

```md
---

## Cierre extendido F2 dentro de S6.3

### 1. Fuente funcional aprobada

La referencia funcional obligatoria para este cierre es `DECISIONES_CIERRE_F2_S6_3_FINAL.md`.

Este bloque sustituye la lectura anterior de “paralelo mínimo F2” por una ejecución completa pero acotada al alcance ya aprobado dentro de S6.3.

### 2. Universo oficial de medición

Las 5 ligas objetivo oficiales para este cierre son:

- Premier League
- LaLiga
- Serie A
- Bundesliga
- Ligue 1

La medición de cierre F2 se hace exclusivamente sobre este universo.

### 3. Contrato operativo F2

#### 3.1 Whitelist core inicial de familias

- `FT_1X2` (obligatoria)
- `OU_GOALS_2_5`
- `BTTS`
- `DOUBLE_CHANCE`

#### 3.2 Requisito mínimo de soporte para elegibilidad base

- `FT_1X2` obligatorio
- más una familia core adicional

#### 3.3 Reglas de `ds_input`

`ds_input` exige únicamente lo necesario para soportar:

- elegibilidad,
- auditoría,
- y señal base.

No todo lo que entra al snapshot se vuelve automáticamente obligatorio en builder.

### 4. Regla oficial refinada de elegibilidad

La verdad oficial sigue gobernada por filtro duro y exige:

- fixture válido,
- odds válidas,
- mínimo 2 familias de mercado,
- ausencia de faltantes críticos de `ds_input`.

### 5. Modo relajado de observabilidad

Se mantiene una versión relajada solo para diagnóstico:

- mínimo 1 familia,
- nunca usada como KPI oficial,
- siempre reportada aparte frente a la oficial.

### 6. Tier Base / Tier A

#### Tier Base

- `raw` deseable
- lineup deseable

#### Tier A

- `raw` obligatorio
- lineup obligatorio solo cuando la cobertura real de la liga lo soporte de forma estable

### 7. Tratamiento de `lineups` y `available: false`

- un evento sin lineup puede seguir siendo elegible en Tier Base si cumple la regla oficial,
- `available: false` no excluye automáticamente,
- si afecta bloque opcional, degrada,
- si afecta bloque obligatorio del tier, excluye,
- si cae en causal oficial, excluye por esa causal.

La auditoría debe distinguir entre:

- dato ausente temporalmente,
- dato no soportado por la fuente,
- dato no propagado o no normalizado internamente,
- bloque no requerido para ese tier.

### 8. KPI oficial de cierre F2

#### 8.1 Definición

`pool_eligibility_rate_official = eligible_events_count / candidate_events_count`

#### 8.2 Ventana oficial de validación

- 30 días
- lectura agregada
- lectura por liga
- lectura sobre días operativos con picks reales

#### 8.3 Métricas secundarias obligatorias

- breakdown de causas de descarte
- cobertura por familias core
- cobertura de `raw`
- cobertura de `lineups.available`
- comparación oficial vs relajado

### 9. Resultado observado

#### 9.1 Lectura agregada

> Completar con evidencia real.

#### 9.2 Lectura por liga

- Premier League: `<completar>`
- LaLiga: `<completar>`
- Serie A: `<completar>`
- Bundesliga: `<completar>`
- Ligue 1: `<completar>`

#### 9.3 Oficial vs relajado

> Completar con evidencia real.

#### 9.4 Causa dominante de descarte

> Completar con evidencia real. Debe indicarse explícitamente si `INSUFFICIENT_MARKET_FAMILIES` sigue o no siendo una causa dominante estructural.

### 10. Resolución final de cierre F2

F2 se considerará realmente cerrado dentro de S6.3 únicamente si:

- el KPI oficial agregado alcanza al menos 60%,
- ninguna liga objetivo queda por debajo de 40%,
- y `INSUFFICIENT_MARKET_FAMILIES` deja de ser una causa dominante estructural.

La resolución documentada debe ser exactamente una de estas dos:

- **F2 cerrado realmente dentro de S6.3**
- **F2 implementado/documentado, pero no cerrado operativamente dentro de S6.3**
```

---

# 6. Resumen ejecutivo de aplicación

## Qué sí reemplazar completo

- `DECISIONES_CIERRE_S6_3.md`
- `US_CIERRE_S6_3.md`
- `TASKS_CIERRE_S6_3.md`
- `HANDOFF_CIERRE_S6_3.md`

## Qué insertar, no reemplazar completo

- bloque nuevo en `EJECUCION.md`

## Qué cambia materialmente en el sprint

- F2 deja de ser “mínimo paralelo” y pasa a “cierre extendido completo dentro de S6.3”.
- El backlog cambia de una sola US-BE-055 corta a tres frentes:
  - contrato operativo F2,
  - regla oficial refinada + causalidad,
  - medición oficial + resolución de cierre.
- El handoff deja instrucción nueva explícita para el dev sobre qué ejecutar ahora.
- La evidencia de cierre ya no puede basarse en un corte exploratorio corto; debe medirse en 5 ligas / 30 días / oficial vs relajado.

## Qué no cambia

- no se abre S6.4,
- no se abre F3 / F4 / F5,
- no se abre snapshot/frescura,
- no se abre UX nueva,
- no se abre mix avanzado de señal.

