# CIERRE_FASE_0_MODELO_Y_METRICA_DATOS.md

## Propósito

Este documento cierra oficialmente la **Fase 0** descrita en `ROADMAP_PO_NORTE_Y_FASES.md`.

La Fase 0 no busca construir nuevas features, sino reducir ambigüedad y dejar definido el marco mínimo para poder ejecutar la Fase 1 con rigor.

En esta fase deben quedar cerradas dos cosas:

1. **Qué significa éxito del modelo**
2. **Qué significa dato suficiente para entrar al pool analizable**

---

## 1. Contrato mental v0

BetTracker 2.0 busca que el usuario convierta análisis en decisiones de apuesta con mejor resultado esperado a lo largo del tiempo, con rigor estadístico y sin vender dinero fácil.

La capa conductual sigue siendo un cinturón de seguridad, pero el motor del producto es:

**calidad de dato + señal defendible**

Por tanto, antes de seguir agregando lógica, features o más complejidad, el proyecto necesita una definición explícita de:

- cómo se evaluará el modelo,
- con qué verdad se medirá,
- y cuál es la base mínima de datos para considerar un evento analizable.

---

## 2. Definición oficial de éxito del modelo v0

### Definición

**El modelo es exitoso cuando, sobre un universo elegible con datos suficientes y trazables, emite picks que muestran una precisión consistente y defendible por mercado y nivel de confianza, comparados contra resultado oficial, sin depender de que el usuario liquide en la app.**

---

## 3. Aclaraciones operativas sobre esta definición

### 3.1 Unidad base de evaluación
La unidad base de evaluación en v0 será el **pick sugerido**.

A partir de allí se podrán construir agregaciones por:

- evento,
- slate o bóveda,
- día,
- semana,
- mes,
- mercado,
- liga,
- nivel de confianza.

### 3.2 Qué no significa esta definición
No significa que el éxito del sistema sea “10 de 10” de manera absoluta o diaria.

Ese es un ideal aspiracional, no una definición operativa.

La definición operativa de éxito en v0 exige:

- dato suficiente,
- criterio trazable,
- consistencia del rendimiento,
- y lectura defendible del sistema contra resultado oficial.

### 3.3 Qué no se medirá todavía como condición para cerrar Fase 0
Para cerrar Fase 0 no es necesario definir todavía en detalle:

- PnL final del usuario,
- CLV,
- edge temporal,
- cuota exacta al instante,
- stake óptimo,
- ni rentabilidad comercial definitiva.

Eso podrá venir después.
La Fase 0 solo debe cerrar el marco base de verdad y elegibilidad.

---

## 4. Principio complementario: éxito no es solo hit rate bruto

El éxito del modelo no debe medirse únicamente por cuántos picks se cumplen.

También importa:

- la calidad del insumo,
- la trazabilidad del criterio,
- el desempeño por familia de mercado,
- la calibración de la confianza,
- la diversidad controlada del set,
- y, en una fase posterior, el comportamiento económico agregado.

En consecuencia:

**el hit rate es una métrica importante, pero no suficiente por sí sola para declarar éxito del sistema.**

---

## 5. Métrica operativa de datos v0

### Definición oficial

La métrica operativa de datos v0 será:

**`pool_eligibility_rate`**

### Significado

**Porcentaje de eventos candidatos que cumplen el mínimo de completitud requerido para entrar al pool analizable, medido de forma reproducible y sin LLM.**

---

## 6. Regla mínima v0 de elegibilidad

Un evento se considerará **elegible** para análisis si cumple, como mínimo, con estas condiciones:

1. Fixture consistente y utilizable
2. Cuotas válidas para análisis
3. Al menos **2 familias de mercado** disponibles para consenso o análisis equivalente
4. Ausencia de faltantes críticos en el `ds_input`

Esta regla es v0 y podrá refinarse en fases posteriores, pero queda aprobada como base inicial para cerrar Fase 0.

---

## 7. Fórmula conceptual

### Métrica principal

`pool_eligibility_rate = eventos_elegibles / eventos_candidatos`

---

## 8. Métricas secundarias derivadas

Estas métricas acompañan la lectura de la métrica operativa principal, pero no la reemplazan:

- % de eventos descartados por faltantes críticos
- cobertura por liga
- cobertura por mercado
- % de eventos con >= 2 familias de mercado
- sesgo 1X2 del pool elegible

Estas métricas serán útiles para Fase 1 y Fase 2, especialmente para los frentes de:

- verdad y cierre de loop,
- uso real de SportMonks,
- y mejora del builder / ds_input.

---

## 9. Resolución oficial de Fase 0

Se considera oficialmente cerrada la **Fase 0** cuando el proyecto adopta como base estas dos decisiones:

### Decisión 1
El éxito del modelo se evaluará contra **resultado oficial**, sobre un universo elegible con datos suficientes, sin depender de la liquidación del usuario dentro de la app.

### Decisión 2
La métrica operativa de datos base será el **porcentaje de eventos elegibles del pool** bajo una regla mínima de completitud medible sin LLM.

---

## 10. Qué habilita este cierre

El cierre de Fase 0 habilita ejecutar la **Fase 1**, que ya es una fase más operativa y orientada a ejecución.

En particular, habilita:

- construir una vista admin o reporte alineado con esta verdad,
- definir y materializar el cierre de loop contra resultado oficial,
- y fijar con más precisión la regla de “no entra al pool si no cumple completitud mínima”.

---

## 11. Interpretación PO

La Fase 0 no resuelve todavía todo el sistema.
No responde aún todas las preguntas de:

- rentabilidad final,
- edge temporal,
- stake,
- protocolo económico,
- o variedad ideal de mercados.

Lo que sí hace es dejar el proyecto con una base mental y operativa mucho más sana:

- qué es éxito,
- con qué verdad se mide,
- y qué significa que un evento esté suficientemente bien armado para analizarse.

Ese era el objetivo real de esta fase.

---

## 12. Siguiente paso natural

A partir de este cierre, el sprint puede bajar estas definiciones a:

1. **Decisiones**
2. **User Stories**
3. **Tasks**

Orden sugerido:

- primero decisiones de Fase 1,
- luego US del admin / medición / elegibilidad,
- y luego tasks técnicas y funcionales para implementarlo.

---

## 13. Resumen ejecutivo

La Fase 0 queda cerrada con esta postura:

- El sistema se mide contra resultado oficial, no contra liquidación del usuario.
- La unidad base de evaluación v0 es el pick sugerido.
- El éxito no es hit rate bruto aislado, sino consistencia defendible sobre universo elegible.
- La métrica operativa de datos base será `pool_eligibility_rate`.
- La regla mínima de elegibilidad v0 exige fixture válido, cuotas válidas, al menos 2 familias de mercado y ausencia de faltantes críticos en `ds_input`.

Con esto, el proyecto ya puede pasar a Fase 1 con un criterio común y ejecutable.
