# CIERRE_RESTANTE_S6_3.md

## Propósito

Este documento define **qué falta exactamente para cerrar S6.3 de forma real**, sin reabrir fases futuras ni mezclar pendientes operativos con nuevas iniciativas.

S6.3 ya cerró gran parte del marco de Fase 0 y del slice principal de Fase 1, pero todavía no debe darse por completamente cerrado mientras falte evidencia operativa con picks reales y mientras no se valide el mínimo paralelo de F2 en datos reales.

---

## 1. Qué ya quedó cerrado dentro de S6.3

### 1.1 Fase 0 — cerrada
Ya quedó aprobado el marco base de verdad del sistema:

- el éxito del modelo se mide contra **resultado oficial**, no contra liquidación del usuario en app,
- la unidad base de evaluación v0 es el **pick sugerido**,
- la métrica operativa de datos base es **`pool_eligibility_rate`**,
- y la regla mínima de elegibilidad v0 exige:
  - fixture válido,
  - cuotas válidas,
  - al menos 2 familias de mercado,
  - y ausencia de faltantes críticos en `ds_input`.

Por tanto, Fase 0 no requiere nuevo backlog de definición profunda dentro de S6.3.

### 1.2 Fase 1 — slice principal implementado
En S6.3 ya quedaron bajados a código, contratos y UI estos componentes:

- evaluación oficial por pick,
- job de cierre de loop,
- elegibilidad v1 del pool,
- auditoría persistida,
- summary admin,
- vista FE mínima de Fase 1,
- acta T-244 aprobada,
- y evidencia de tests/build satisfactorios.

Esto significa que el **núcleo técnico del slice principal de Fase 1 ya existe**.

---

## 2. Qué NO está completamente cerrado todavía

Aunque el slice de Fase 1 ya fue implementado, todavía no debe considerarse cerrado del todo mientras falte:

1. **evidencia operativa real del loop con picks reales**
2. **evidencia operativa real de elegibilidad/auditoría sobre eventos reales**
3. **confirmación del comportamiento esperado de la vista admin con datos no vacíos**
4. **validación mínima del frente F2 dentro de S6.3**, sin abrir todavía una nueva fase completa

---

## 3. Pendiente principal de S6.3

### 3.1 Evidencia de cierre de loop para picks reales

Este es el pendiente más importante que sigue abierto.

No basta con que existan:

- tabla/modelo,
- job,
- endpoint,
- vista,
- tests,
- y build.

Para declarar cerrado este frente hace falta demostrar en un entorno real que:

- picks existentes en `bt2_daily_picks`
- reciben fila en `bt2_pick_official_evaluation`
- y quedan al menos como `pending_result`, o ya evaluados si existe resultado oficial.

#### Qué debe verse como evidencia mínima
- subconjunto real de picks identificado por `operating_day_key`
- filas reales en `bt2_pick_official_evaluation`
- estados visibles (`pending_result`, `evaluated_hit`, `evaluated_miss`, etc.)
- SQL o salida de job documentada
- y, idealmente, reflejo visible en la vista admin

### 3.2 Evidencia de elegibilidad / auditoría real

El summary de Fase 1 no puede quedar útil si los eventos candidatos aparecen mayoritariamente como:

- `(sin auditoría reciente)`

Eso indica que la capa nueva de elegibilidad no se ha ejecutado o no se ha poblado para el entorno/día observado.

#### Qué debe verse como evidencia mínima
- eventos reales del día con filas en `bt2_pool_eligibility_audit`
- `is_eligible` o `primary_discard_reason` poblados
- coverage real distinta de cero cuando aplique
- desaparición del patrón dominante “sin auditoría reciente” como explicación principal

### 3.3 Evidencia funcional de la vista admin

La vista `/v2/admin/fase1-operational` ya existe y su estructura es correcta, pero para declarar realmente cerrado S6.3 se requiere verla con datos operativos consistentes, no solo con estructura vacía.

#### Resultado esperado mínimo
- candidatos > 0
- con auditoría reciente > 0
- con fila evaluación oficial > 0
- picks reales al menos en `pending_result`
- hit/miss cuando ya haya verdad oficial disponible

---

## 4. Qué parte mínima de F2 todavía entra dentro de S6.3

S6.3 no debe intentar cerrar todo F2.
Pero sí debe cerrar el **mínimo paralelo** que el roadmap exige junto a Fase 1:

### 4.1 Validar la regla mínima real de elegibilidad
Confirmar si la regla actual de elegibilidad v0/v1:
- sirve con datos reales,
- no está descartando demasiado,
- y puede sostenerse como regla mínima del corte actual.

### 4.2 Medir coverage real por liga / mercado
No como diseño final de tiers ni como política definitiva global, sino como validación mínima para responder:

- ¿la regla mínima actual produce un pool razonable?
- ¿hay ligas o mercados piloto donde el comportamiento es demasiado restrictivo?
- ¿hace falta una única decisión corta de ajuste para completar S6.3?

### 4.3 Qué NO entra todavía
No entra todavía:
- rediseño completo de completitud por liga,
- sistema avanzado de tiers,
- re-arquitectura grande de `ds_input`,
- política completa de snapshot/frescura,
- ni expansión fuerte de mercados.

Eso corresponde a fases posteriores.

---

## 5. Definition of Done real para cerrar S6.3

S6.3 se considerará realmente cerrado solo cuando se cumplan estos puntos:

### DoD-S6.3-1
Existe evidencia de loop oficial para un subconjunto real de picks.

### DoD-S6.3-2
Existe evidencia de auditoría de elegibilidad para eventos reales del día o ventana analizada.

### DoD-S6.3-3
La vista admin de Fase 1 muestra datos operativos no vacíos y consistentes con BD.

### DoD-S6.3-4
La regla mínima de elegibilidad fue validada con datos reales y, si hizo falta, se emitió una decisión mínima adicional para sostenerla en este corte.

### DoD-S6.3-5
`EJECUCION.md` y `TASKS.md` reflejan el cierre real del pendiente restante.

---

## 6. Backlog final recomendado para cerrar S6.3

### Bloque A — operación real del loop
- validar migraciones en el entorno real
- correr backfill / official evaluation job
- confirmar filas en `bt2_pick_official_evaluation`
- documentar evidencia

### Bloque B — operación real de elegibilidad
- correr auditoría de elegibilidad sobre eventos reales
- confirmar filas en `bt2_pool_eligibility_audit`
- documentar coverage real y motivos de descarte

### Bloque C — evidencia admin
- validar endpoint summary con datos reales
- validar vista `/v2/admin/fase1-operational`
- adjuntar evidencia funcional

### Bloque D — cierre mínimo de F2 dentro de S6.3
- medir coverage real por liga/mercado
- validar si la regla mínima actual sirve
- emitir, solo si es necesario, una decisión corta adicional

### Bloque E — cierre documental
- actualizar `EJECUCION.md`
- marcar pendiente final en `TASKS.md`
- dejar S6.3 listo para cierre formal

---

## 7. Qué NO debe pasar ahora

Para cerrar S6.3 no se debe:

- abrir ya Fase 2 como foco principal,
- reabrir Fase 0,
- convertir este cierre en megaproyecto de completitud,
- ni intentar resolver snapshot, costo, CLV y UX avanzada al mismo tiempo.

El objetivo es **cerrar honestamente S6.3**, no diluirlo.

---

## 8. Resolución operativa

La resolución correcta para este punto del proyecto es:

- **Fase 0: cerrada**
- **Fase 1: implementada, pero pendiente de evidencia operativa real**
- **F2: solo mínimo paralelo dentro de S6.3**
- **S6.3 no debe crecer a cubrir fases futuras**
- **Una vez se cumpla el DoD real, se cierra S6.3 y el siguiente frente va a sprint nuevo**

---

## 9. Resumen ejecutivo

S6.3 ya resolvió definición y gran parte del slice técnico de verdad/evaluación.

Lo que falta no es rediseñar producto desde cero, sino:

- operar la capacidad ya construida,
- evidenciarla con picks reales,
- validar la elegibilidad mínima con datos reales,
- y cerrar documentalmente el pendiente final.

Ese es el trabajo restante correcto para terminar S6.3.
