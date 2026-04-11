1. S6.1 y “replicar v1” — qué significa en docs
En DSR_V1_FLUJO.md v1 no es “siempre el favorito del 1X2”. Es: candidatos + ds_input rico (contexto, processed, cuotas, etc.) → modelo devuelve picks_by_event con mercado, selección, cuota, edge_pct, confianza, razon → post-proceso en el job v1.

La §8 del mismo doc deja explícito que en BT2 el ds_input sigue siendo más pobre que v1 hasta que el builder (S6.1) lo acerque. Es decir: la esencia de v1 no es solo el prompt, es insumo + reglas servidor + post-proceso. Si el insumo es mínimo, el comportamiento no puede ser “tal cual v1” aunque el JSON de salida se parezca

RESPUESTA:
Lo que debe estar caro es que ds_input debe ser siempre de calidad optima y mucho mayor a la de v1, ya que contamos condatos veridicos. No entendi bien l flujo del builder, pero repito, la core de v1 esta funcionando muy bien, el problema de v1 es la ingesta poco confiable de los dattos al venir de un scrapper. BT2 debe ser y tener el mismo rigor de pasos y proceso que V1, y debe ser mucho mejor pq los datos son certificados.


----------------------------------------------------------

2. ¿Por qué DSR puede sugerir el 1 con menor probabilidad implícita (cuota más alta)?
En código, el sistema no está instruido a “elegir la línea con mayor probabilidad implícita del 1X2”.

En bt2_dsr_deepseek.py el system prompt dice literalmente que el modelo debe elegir el mercado con “mejor relación valor/datos” entre los presentes en consensus, no “el más probable”:


bt2_dsr_deepseek.py
Lines 104-110
_SYSTEM_BATCH = (
    "Eres analista de apuestas deportivas (fútbol, solo pre-partido). "
    ...
    "Elegí el mercado con mejor relación valor/datos entre los presentes en consensus. "
    ...
)
En apuestas de valor, es normal que la selección tenga cuota más alta (menor implícita “cruda”) que otra opción del mismo mercado: el modelo (o la lógica) está diciendo “esta cuota está mal cotizada respecto a mi lectura”.
Tu captura de bwin (1 @ 3.10, X @ 2.80, 2 @ 2.63) solo prueba que en esa casa el 1 es el menos probable si asumís mercado eficiente y sin vig; no contradice por sí sola al DSR si el producto busca valor y/o el consensus que ve el modelo no es exactamente esa pantalla.

Conclusión: que sugiera Platense (1) con cuota más alta no es, por definición, un bug de implementación; puede ser intención del prompt (valor) o ruido si el modelo no tiene “datos” suficientes para sostenerlo (véase §3).

Respuesta: 
La premisa de que enciuentre mercado no es una via libre de seleccion del mercado que sea respecto a la cuoita. 
Lo que el PO quiso decir es que, si en un evento hay 3 mercados posibles, 1x2, BTTS, over/under, el modelo debe tomar en consideracion cual es el evento de esos mercados mas probables y que mejor relacion con lacuoita (o sea la probabilidad implicita tengan).
Por ejemplo: Si en el caso del Platense vs Corinthians tenmos como mercado 1x2: 1@3.5 y 2@1.5, eso nos dice implicitamente qu ela probabilidad de exito es de 2, osea del corinthians, ademas de eso DS en su input deberia tener las stats de los h2h y demas datos que ayuden a validar ese mercado. SI las stats o parametros no son suficientes, entonces pasa al under/over, doonde a aprtior de la cuita se puede inferir algo, pero se apiya en el historial de esos equipos, los cuales ya tenemos en dbs. La exleccion del mercado es: CUAL DE LOS MERCADOS DISPONIBLES PARA ESTE PARTIDO SEGUN EL ANALISIS DEL MODELO BASADO EN LA ESTADISTICA HISTORICA Y LOS PARAMETROS DEL INPUT (QUE ESTAN EN: /Users/kevcast/Projects/scrapper/docs/bettracker2/DSR_V1_FLUJO.md) ES EL QUE MAYOR VALOR O SEA PROBABILIDAD MAS ALTA DE EXITO ENTRE ELLOS. 
NO es una decision de que este mercado puede dar mas dinero, sino cual es el mas probable.

----------------------------------------------------------------

3. ¿Qué está “mal” entonces? (coherencia que sí importa)
Lo grave en tu ejemplo BT2 anterior no es la cuota en sí, sino:

Selección mostrada (Victoria Platense) vs texto del razonador que hablaba de empate → eso es incoherencia del JSON del modelo (selection vs razon) o mezcla de campos en UI, pero en el parser actual razon se toma del pick tal cual:

bt2_dsr_deepseek.py
Lines 192-197
        razon = str(pick.get("razon") or "").strip()
        ...
        narr = razon or motivo or "Señal modelo."
Si el LLM escribe una cosa en razon y otra en selection, el pipeline hoy te lo sirve crudo hasta que Post-DSR (S6.1 / T-181) lo detecte y degrade u omita (lo que ya empezaste a cerrar en DECISIONES / US-BE-034).

Eso es distinto de “el modelo eligió el underdog”: ahí el fallo es calidad/coherencia de salida, no la regla “debe ser el favorito”.

RESPUESTA: totalmente de acuerdo, v1 sigue siendo superior en ese aspecto, y no entiendo poq 
Aqui un ejemplo de como se muestra un pick en v1:
"
Vitória vs Juazeirense
Copa do Nordeste

Inicio del partido: 17:00 · hora Colombia

Es el horario que traía SofaScore cuando se guardó el run. Reprogramaciones posteriores no se actualizan solas; compara con SofaScore si el partido se movió.

Día del análisis (run): 8 de abr de 2026

pick #333 · event 15871853
SofaScore ↗

Has ganado este pick

Usamos el resultado que marcaste tú en «Tu seguimiento».

Marcador 4 — 1

Qué estás apostando (web)

Over/Under 2.5

Apuestas a que habrá más o menos goles (u otra cifra) que el número que marca la casa.

Código en el boletín: Over 2.5

Resumen: Apuestas a que habrá más goles (o más de esa cifra) de lo que indica la línea: Over 2.5.

Cuota (pago si aciertas): 1.95

Confianza del modelo: Media-Alta
Ventaja que ve el modelo: 3%
Por qué lo sugiere el modelo: El historial directo indica más de 2.5 goles en 4 de los últimos 5 encuentros entre estos equipos.
"


--------------------------------------------------------------------------
4. ¿Quién “comete el error”?
Fenómeno	Causa más plausible
Pick con menor implícita del 1X2	No es error automático: el prompt pide valor/datos, no máxima implícita.
Razonamiento que contradice la selección	Principalmente el modelo (salida inconsistente); producto si no hay Post-DSR que lo corrija u omita.
Sensación de “justificación floja”	Falta de paridad de ds_input con v1 (poco contexto vs SofaScore/processors) → el modelo inventa o generaliza mal; eso es lo que S6.1 ataca con builder + reglas.
Discrepancia con la img de bwin	Posible fuente distinta (p. ej. consensus CDM vs captura de una casa); habría que comparar la misma línea que recibe el modelo.

RESPUESTA: Estoy deacuerdo con cada item, BT2 debe ser una version mejorada de V1, no la sombra.

--------------------------------------------------------------------------
5. Si el producto sí debe evitar “valor en underdog” salvo criterio fuerte
Eso no está hoy como regla dura en el prompt citado; sería decisión de producto nueva (p. ej. “no 1X2 underdog salvo edge mínimo X y datos completos Tier A”) y viviría en DECISIONES + T-177/T-181, no solo en “replicar v1”
RESPUESTA: La premisa no es underdog, solo decidir la cuota implicita menos probable, sino que el criterio del modelo basado en los datos valide si tiene o no sentido, por ejemplo en el dia 2 o 3 de v1 estar corriendo, lanzo el siguiente pick home vs away:
away tenia mas propabilidad implicita, es decir pagaba menos, pq era un equipo fuerte, pero en los lineups se especificaba que el away tenia 3 bajas importntes, y aunque away era favorito, por ser histricamente mejor, el pick sugiro apostar a favor de home, basado en el contexto y apoyado en el lineup, y ¿que crees? se cumplio el pick que DSR dio.

Entonces es importante aclarar que no entiendo ahora mismo pq ds_input de bt2 es mas pobre que v1, no me lo expico ya que tenemos mejores datos, mas y mas confiables que en v1, v1 era un scrapper, ahora tenemos una api paga, y un background de datos que podemos consultar, es inadmisible que BT2 sea inferior a v1.


INSTRUCCION:
Valida como se construye ds_inputs para BT2, y compara con la forma de v1.
Es imperativo que antes de crearlo al seleccionar los candidatos se busque en nuestra DB todo lo relaciondo historicamente con los equipos que se enfrentan, incluyendo cual han sido la cuotas historicas si existen, con eso se construye el ds_input. Sino vcamos a seguir subutilizando datos.

---

## 6. Validación técnica (BA) — construcción `ds_input` v1 vs BT2 *(pendiente de validación PO antes de US/TASKS/DECISIONES)*

### 6.1 v1 (`jobs/select_candidates.py`)

Por cada `event_id` **seleccionado**, el ítem de `ds_input[]` se arma desde **`event_features.features_json`** (SQLite del run):

| Bloque | Origen |
|--------|--------|
| `event_context` | Completo tal como vino del bundle/scrape (torneo, equipos, `start_timestamp`, estado, etc.). |
| `processed` | **Todo** el dict `features.processed` (p. ej. `lineups`, `statistics`, `h2h`, `team_streaks`, `team_season_stats`, `odds_all`, `odds_featured`). |
| `diagnostics` | Flags reales del scrape (`*_ok`, `fetch_errors`). |
| `selection_tier` | A/B según contrato de calidad de datos. |

Referencia: construcción en `select_candidates.py` (aprox. líneas 549–563): copia `event_context`, `processed` y `diagnostics` **sin vaciar** bloques.

### 6.2 BT2 hoy (`apps/api/bt2_dsr_ds_input_builder.py` + `bt2_router._generate_daily_picks_snapshot`)

El snapshot diario llama a `build_ds_input_item_from_db(cur, event_id, …)`:

| Bloque | Qué hace hoy |
|--------|----------------|
| Metadatos evento | `bt2_events` + `bt2_leagues` + equipos (nombre, kickoff, status, liga, país, tier). |
| Cuotas | `bt2_odds_snapshot` → agregación `consensus` (+ opcional `by_bookmaker`) vía `aggregate_odds_for_event`. |
| `processed.odds_featured` | Sí (consensus + books). |
| `processed.lineups`, `h2h`, `statistics`, `team_streaks`, `team_season_stats` | **Placeholders fijos:** `{"available": False}` (líneas 75–79 del builder). |
| `diagnostics` | Incluye `market_coverage` y flags `*_ok: False` para esos bloques; `fetch_errors: []`. |

**Conclusión:** la API/CDM puede ser más fiable que el scraper v1, pero **el builder BT2 no está volcando aún** histórico H2H, estadísticas, alineaciones ni series en el `ds_input` que recibe DeepSeek: **no es que “Postgres no tenga mejor dato” en abstracto; es que esta capa aún no lo consulta ni lo rellena** (hueco de implementación / alcance parcial de US-BE-032 respecto a la intención PO).

### 6.3 Alineación con la instrucción PO (histórico + cuotas históricas)

- **Requisito PO:** al armar candidatos/`ds_input`, traer de la DB lo **histórico** relevante para el duelo (y cuotas históricas si existen).
- **Estado código:** el builder actual **no** implementa esas lecturas; solo evento + snapshots de cuotas del evento.
- **Próximo paso acordado:** mantener este §6 en **feedback** hasta validación PO; recién después bajar a **US de refinement** (referenciando **US-BE-032** / **T-174–T-176** cerrados o en curso), **TASKS** y, si hay trade-off durable, **DECISIONES**.

### 6.4 Coherencia con respuestas PO en §2 y §5

- La premisa PO (**elegir entre mercados disponibles la lectura con mayor probabilidad de acierto / mejor relación con la cuota según datos**, no “más dinero”) **contradice el texto actual** del `_SYSTEM_BATCH` en `bt2_dsr_deepseek.py` (“mejor relación **valor**/datos”), que en apuestas se interpreta como **edge / valor esperado**. Eso deberá unificarse por **DECISIONES + prompt** tras validar este doc.
- El ejemplo v1 (favorito con bajas → pick al home) **requiere** `ds_input` con **lineups/stats**; hoy BT2 **no** los envía al modelo en esos campos → el comportamiento PO esperado **no puede** reproducirse solo con el prompt.

*Documento vivo: no crear US/TASKS/DECISIONES nuevos hasta cierre explícito de este feedback por PO.*
