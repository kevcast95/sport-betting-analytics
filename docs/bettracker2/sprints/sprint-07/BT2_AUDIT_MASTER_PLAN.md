# BT2 Audit Master Plan

## Objetivo de la auditoría

Antes de cambiar predictor, entrenar un modelo nuevo o pagar más feeds, responder con evidencia estas preguntas:

1. **¿BT2 está midiendo mal o realmente no tiene edge?**
2. **¿El drift nace en el proveedor/raw, en `bt2_events`, en odds/materialización, en evaluation o en replay?**
3. **¿Qué parte del problema es reciente, qué parte es histórica y qué parte es solo de lente/ventana?**
4. **¿Existe un subconjunto ex-ante donde BT2 sí tenga señal utilizable para política de liberación selectiva?**

---

## Principio rector

No asumir primero que:
- “el modelo es malo”
- “SM es el culpable”
- “faltan odds”
- “SFS resuelve todo”
- “necesitamos comprar más feeds ya”

Primero:
1. auditar
2. separar origen del drift
3. decidir gasto
4. recién después optimizar liberación o modelo

---

## Qué queremos saber exactamente

### A. Proveedor / raw
- ¿Existe el raw para los eventos relevantes?
- ¿Existe latest raw?
- ¿El latest raw ya trae score/estado y BT2 no lo materializa?
- ¿El raw también viene incompleto?

### B. CDM / `bt2_events`
- ¿Los fixtures se materializan bien?
- ¿Hay `scheduled` stale?
- ¿Hay `finished` sin score?
- ¿Hay drift entre raw latest y `bt2_events`?

### C. Picks / operating day
- ¿El `operating_day_key` está alineado con el kickoff local del evento?
- ¿Estamos comparando ventanas con lentes distintos?

### D. Official evaluation
- ¿Cada pick tuvo fila oficial?
- ¿Se evaluó con sentido respecto al estado real del evento/raw?
- ¿Hay picks scored aunque el evento siga unresolved en CDM?
- ¿Hay pending/no_evaluable aunque el raw parezca tener score?

### E. Odds
- ¿Faltan provider odds raw?
- ¿Faltan odds consolidadas?
- ¿Hay provider raw sin snapshot consolidado?
- ¿Hay snapshot consolidado sin staging raw?

### F. SFS / experimento
- ¿SFS realmente aporta trazabilidad o es ruido?
- ¿Hay join matched?
- ¿Hay `ds_input_shadow` útil?
- ¿Sirve como apoyo, reconciliación o no está aportando nada?

### G. Política de liberación
- Una vez que los datos sean confiables:
  - ¿qué subconjuntos ex-ante rinden mejor?
  - ¿mercados?
  - ¿ligas?
  - ¿bandas de cuota?
  - ¿tiers?
  - ¿completitud de datos?
  - ¿agreement entre fuentes?

---

## Fases de auditoría

## Fase 0 — cobertura real de la DB
Objetivo:
- saber qué periodos existen realmente en la DB
- no seguir corriendo ventanas vacías “a ciegas”

Entregables mínimos:
- cobertura por `bt2_events.kickoff_utc` (día local)
- cobertura por `bt2_daily_picks.operating_day_key`

Decisión:
- si una ventana está vacía en `bt2_events`, no usarla para diagnosticar lineage de eventos
- si hay picks por operating day pero no eventos en ese lente, no concluir nada sin reconciliar ambos

---

## Fase 1 — auditoría del universo reciente
Script:
- `scripts/bt2_phase1_data_audit.py`

Objetivo:
- auditar síntomas visibles del circuito reciente:
  - cierre
  - pending lag
  - finished without score
  - official evaluation
  - no_evaluable
  - market/tier quality
  - raw SM coverage
  - provider odds coverage
  - SFS join
  - ds_input shadow
  - bt2_odds_snapshot completeness

Qué decide:
- si la medición oficial reciente parece sana o no
- si la capa de odds consolidada reciente parece sana o no
- si el problema visible reciente está más en `bt2_events` que en evaluation/odds

---

## Fase 2 — auditoría de linaje y drift
Script:
- `scripts/bt2_phase2_lineage_audit.py`

Objetivo:
- ubicar dónde nace el drift real:
  - raw latest
  - `bt2_events`
  - operating day
  - evaluation
  - provider raw odds
  - consolidated odds
  - soporte SFS/shadow

Qué audita:
1. cobertura del rango en ambos lentes
2. universo de lineage
3. raw latest freshness
4. raw latest vs `bt2_events`
5. `operating_day_key` vs kickoff local
6. evaluation vs estado real del lineage
7. provider raw odds vs consolidated odds
8. soporte SFS/shadow

Qué decide:
- si el problema es proveedor
- si el problema es materialización
- si el problema es lente/ventana
- si el problema es evaluation timing/state
- si vale la pena pagar feed nuevo ya o no

---

## Fase 3 — comparación histórica entre ventanas
Ventanas sugeridas:
- 1 reciente cerrada
- 2 históricas no vacías y comparables
- idealmente una cerca del periodo donde el replay dio el peor resultado

Objetivo:
- ver si el problema es:
  - reciente
  - histórico
  - estructural
  - o solo una ventana mala

Decisión:
- si el patrón se repite en varias ventanas, es problema estructural
- si aparece solo en ventanas recientes, revisar cambios de pipeline/feed
- si aparece solo en ciertas épocas, revisar coberturas y jobs de ese periodo

---

## Fase 4 — política de liberación selectiva
Solo después de confiar razonablemente en los datos.

Objetivo:
- no intentar que “todo el universo” sea bueno
- encontrar subconjuntos ex-ante con mejor señal

Qué se revisa:
- hit rate
- ROI
- break-even por cuota
- estabilidad entre ventanas
- degradación por mercado/liga/tier/completitud

Decisión:
- si el subconjunto fuerte se repite en varias ventanas, se convierte en política de liberación
- si no se repite, es espejismo y no debe usarse como regla

---

## Criterios de decisión operativa

## 1) Cuándo el problema es proveedor / raw
Indicadores:
- falta latest raw para eventos relevantes
- raw llega muy incompleto
- raw no trae score ni estado final
- el raw también está mal, no solo `bt2_events`

Conclusión:
- aquí sí tiene sentido revisar feed/proveedor

## 2) Cuándo el problema es CDM / materialización
Indicadores:
- raw latest sí existe
- raw latest parece traer score/estado
- `bt2_events` sigue unresolved o sin score
- hay provider raw pero no snapshot consolidado

Conclusión:
- aquí el dinero en más feeds no resuelve primero
- primero hay que arreglar materialización/update jobs

## 3) Cuándo el problema es el lente de fechas
Indicadores:
- ventana vacía en `bt2_events`
- pero con picks en `operating_day_key`
- o fuerte drift entre `operating_day_key` y kickoff local

Conclusión:
- no comparar replay/bóveda/ventanas sin alinear lente

## 4) Cuándo el problema es evaluation
Indicadores:
- picks evaluados mientras el evento sigue unresolved
- picks pending/no_evaluable aunque raw ya tiene score
- filas oficiales faltantes o inconsistentes

Conclusión:
- primero corregir timing/reglas de evaluation

## 5) Cuándo pagar SM
Tiene sentido priorizar SM si:
- el mayor dolor demostrado es fixture/truth/cierre/upstream
- el raw reciente/histórico es insuficiente o inconsistente
- BT2 ya está acoplado a esa identidad de fixture

## 6) Cuándo pagar otro feed de odds
Tiene sentido solo si la evidencia muestra:
- falta real de cobertura de odds que sí pega a replay/liberación
- o necesitas mercados/odds que SM no cubre bien
- y ya quedó demostrado que el cuello no es CDM/evaluation

## 7) Cuándo NO pagar ambas cosas a la vez
No hacerlo si:
- la auditoría todavía no separa el origen del drift
- el problema visible principal es materialización
- la evaluación reciente ya parece sana
- `bt2_odds_snapshot` reciente ya parece suficiente

---

## Orden recomendado de ejecución

1. **Fase 0**
   - identificar ventanas con datos reales

2. **Fase 1**
   - correr ventana reciente cerrada
   - revisar official evaluation + odds snapshot + closure

3. **Fase 2**
   - correr misma ventana reciente
   - ubicar dónde nace el drift de verdad

4. **Fase 3**
   - correr 2 ventanas históricas no vacías
   - comparar patrones

5. **Decisión**
   - proveedor
   - ingeniería de materialización
   - replay/evaluation
   - política de liberación selectiva

---

## Preguntas que sí debería poder responder la auditoría completa

- ¿SM está fallando o BT2 está materializando mal?
- ¿El replay está sub-midiendo por datos incompletos?
- ¿El problema es reciente o histórico?
- ¿Hay eventos donde raw latest y CDM no coinciden?
- ¿Hay picks bien evaluados aunque el evento esté sucio?
- ¿Estamos comparando ventanas con el lente correcto?
- ¿Tiene sentido gastar hoy en SM, odds, ambas o ninguna todavía?

---

## Preguntas que NO debería responder todavía por sí sola

- cuál será el ROI futuro
- cuál es el mejor modelo definitivo
- si una política de liberación selectiva ya quedó validada sin backtests comparables
- si un subconjunto “ganador” es real sin estabilidad entre ventanas

---

## Resultado esperado antes de gastar dinero nuevo

Antes de comprometer gasto estable en feeds, deberías salir con una tabla mental así:

- **origen principal del drift**
  - proveedor
  - CDM
  - evaluation
  - odds
  - lente/ventana

- **impacto real**
  - bajo
  - medio
  - alto

- **acción correcta**
  - pagar SM
  - pagar odds
  - arreglar pipeline
  - ajustar replay/evaluation
  - diseñar liberación selectiva
