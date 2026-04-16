# Informe: cobertura de cuotas SofaScore (V1) y criterio “>1 mercado” en `odds_all`

**Audiencia:** BA, arquitectura técnica  
**Contexto:** evaluación de **SofaScore (SFS)** como **fallback** u origen secundario de cuotas frente a otros proveedores.  
**Alcance:** pipeline V1 (ingesta diaria, SQLite), **solo fútbol**, salvo donde se indique lo contrario.

---

## 1. Duda de negocio / producto

¿Si usamos SofaScore como proveedor (o fallback) de odds, podemos asumir que **la ingesta diaria** nos deja, de forma consistente, **suficientes mercados por partido** en lo que hoy persistimos de la API?

En concreto se analizó la pregunta operativa:

- En el rango **2026-03-23 → 2026-04-18**, ¿en **cada día** de ingesta de fútbol hay **>80 % de partidos** con **más de un mercado** en lo guardado del endpoint **`/odds/1/all`** (persistido como `dataset = odds_all`, estructura `extended_markets`)?

---

## 2. Qué es exactamente lo que mide la base de datos (importante para no confundir al BA)

### 2.1. No se guarda el JSON crudo completo de `/odds/1/all`

En V1, `event_snapshots.payload_raw` para `odds_all` **no** es la lista completa de mercados de SofaScore. Es la salida **ya procesada** por `odds_all_processor.py`: un subconjunto fijo de mercados mapeados desde nombres canónicos de la API (`Double chance`, `Draw no bet`, `Both teams to score`, etc.).

### 2.2. Los “6 bloques” de `extended_markets`

Son **seis grupos** anidados bajo `extended_markets`:

| Bloque (agrupación lógica) | Mercados persistidos |
|----------------------------|----------------------|
| `safety` | `double_chance`, `draw_no_bet` |
| `goals_depth` | `btts`, `over_under_2.5` |
| `discipline_and_set_pieces` | `total_cards_3.5`, `total_corners_9.5` |

**Criterio usado en el análisis:** por cada partido del día, se cuenta cuántos de esos **seis** sub-mercados tienen **al menos una cuota numérica no nula**.  
“**Más de un mercado**” = **estrictamente más de uno** de esos seis con datos (≥2 bloques con al menos una cuota).

### 2.3. El 1X2 (resultado a tiempo completo) **no** entra en esos 6 bloques

El **mercado 1X2** (local / empate / visitante) **no** forma parte de `extended_markets` en `odds_all`.

- Se obtiene de otro endpoint: **`/odds/1/featured`**, persistido como `dataset = odds_featured`, bajo `market_snapshot.full_time_1x2` (y además `asian_handicap` en el mismo snapshot).
- Por tanto, frente a los “6 bloques”, el 1X2 **no** es un séptimo bloque *dentro del mismo JSON* de `odds_all`: es **otra consulta**, **otro dataset** en la misma ingesta de bundle.

En lenguaje de producto: si el BA cuenta “mercados que tenemos de SofaScore en un día”, debe separar:

1. **Mercados “all” procesados** → como máximo la lógica de esos **6** sub-mercados en `extended_markets`.  
2. **Mercados “featured”** → al menos **1X2** y **hándicap asiático** en `market_snapshot`, cuando la respuesta y el processor lo permiten.

---

## 3. Respuesta a la pregunta del umbral 80 % (solo `odds_all` / `extended_markets`)

**No:** con la definición anterior (**>1 de los 6 bloques con cuota** por partido), **ningún día** del rango analizado alcanza **80 %** de partidos.

- El **máximo** observado en ese ronda ronda **~56 %** de partidos cumpliendo la condición (ejemplo trabajado: **2026-04-16**, **30 de 53** partidos ≈ **56,6 %**).

### 3.1. Lectura práctica del porcentaje (para evitar malentendidos)

- El **% es sobre partidos (eventos)**, no sobre “el 56 % del volumen de mercados del día repartido entre BTTS y goles”.
- **~56 %** significa, en redondeo: **de cada 10 partidos, unos 5–6** tienen datos en **2 o más** de los seis sub-mercados canónicos en `extended_markets`; el resto **no** cumple (típicamente **0 o 1** bloque con cuotas persistidas).

### 3.2. Ejemplo concreto: **2026-04-16** (fútbol, `odds_all`)

**53** partidos con snapshot `odds_all` en esa corrida.

| Cantidad de bloques (de 6) con ≥1 cuota numérica | Partidos | % del día |
|--------------------------------------------------|----------|-----------|
| 0 | 23 | 43,4 % |
| 2 | 1 | 1,9 % |
| 4 | 15 | 28,3 % |
| 5 | 12 | 22,6 % |
| 6 | 2 | 3,8 % |

**Partidos con “más de un mercado” (≥2 bloques):** **30 / 53 ≈ 56,6 %**.

Observación: ese día casi no hay partidos en la franja intermedia “exactamente 1 bloque”; la distribución muestra muchos partidos con **ninguno** de los seis rellenado en lo persistido y otro grupo con **varios** bloques (4–6), lo que refuerza que el cuello no es solo “un mercado menos”, sino la **combinación** de qué expone SofaScore y qué **elige persistir** el processor.

### 3.3. Motivo habitual (técnico / producto)

Los bloques de **tarjetas** y **córners** suelen ir **vacíos** con frecuencia (no ofrecidos, no encontrados por nombre, o sin cuota útil). Muchos partidos solo “suman” en **safety** y/o **goals_depth**. Por eso el umbral “>1 bloque” puede ser exigente **en la forma en que hoy modelamos `odds_all`**, aunque en la app de SofaScore el usuario vea más mercados en la respuesta cruda.

---

## 4. Contraste breve con `odds_featured` (1X2 + asiático)

Si la pregunta de negocio fuera “¿tenemos **1X2 y asiático** en una proporción alta de partidos?” (dos mercados del **featured**, no de los seis del **all**), el patrón **sí** es distinto: en muchos días del mismo rango la proporción de partidos con ambos bloques con datos **sí supera 80 %** (alineado con `diagnostics.odds_all_ok` y `odds_featured_ok` en el bundle).

Eso **no contradice** el hallazgo sobre `extended_markets`: son **capas distintas** de la misma ingesta.

---

## 5. Implicación para la decisión “SFS como fallback de odds”

1. **Si el fallback debe cubrir “muchos mercados por partido” solo con lo que hoy persiste de `/odds/1/all`**, el modelo actual (**6 sub-mercados**) y el processor **no** reflejan la riqueza completa de SofaScore y **no** pasan un umbral tipo **80 %** de partidos con **>1** de esos bloques.
2. **Si el fallback prioriza 1X2 (y línea asiática)**, esa señal vive principalmente en **`odds_featured`**, no en los seis bloques de `extended_markets`.
3. Para comparar proveedores con paridad, habría que acordar **KPI explícito**: p. ej. “% partidos con 1X2 decimal”, “% con N mercados del catálogo X”, o “persistir raw / conteo de `markets[]`” — hoy la DB V1 **no** guarda el array completo de mercados del `all` para fútbol.

---

## 6. Limitaciones del informe

- Análisis acotado a **una base SQLite** y al **rango de fechas** indicado; no es una garantía estadística global de SofaScore.
- Días **sin** `daily_run` de fútbol o con estado **failed** en el rango quedan **fuera** de una lectura “todos los días OK” (ya comentado en conversación técnica previa).
- **Tenis** tiene otro modelo (`tennis_odds`, etc.); este informe se centra en el razonamiento que pidió el equipo para **fútbol** y la confusión 1X2 vs `extended_markets`.

---

## 7. Conclusión en una frase (para slide / acta)

**Los seis bloques de `extended_markets` no incluyen el 1X2; el 1X2 va por `odds_featured`. Con la métrica “más de un mercado = más de uno de esos seis bloques con cuota”, ningún día del rango llega al 80 % de partidos; el techo observado fue ~56 %. Por tanto, para evaluar SFS como fallback hay que separar explícitamente “cobertura 1X2/featured” de “cobertura mercados secundarios en `odds_all` procesado”.**
