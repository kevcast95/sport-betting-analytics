A. Norte y prioridad
¿Cuál es el resultado de negocio #1 del S6? (una frase: p. ej. “bóveda con texto modelo auditable”, “ingesta sin humano”, “mercados que no rompan settle”, etc.)
Resp: EL modelo debe responder con criterio y justficando la seleccion, y el mercado (Esto es 1x2, doble oprtunidad, drawm, BTTS, over/under). Revisar documentacion de v1 solo para consultar como define los contratos de entrada y salida a Deepseek
¿Hay fecha o hito externo (demo, piloto, partner) que condicione qué entra sí o sí en S6?
Resp: BAsicamente es integrar DeepSeek, y tener una respuesta concreta del modelo por cada pick, el modelo debe sugerir los 15 picks del dia, debe especificamente tener 5 para cada franja horaria, debe tener la capacidad de definir los 2 picks premium de alto valor, y los 3 libres con menor valor, aunque deben ser de alta calidad estadistica, debe haber un insentido vreal para el usuario el querer desbloquear.
¿Qué estarías dispuesto a dejar fuera del S6 si el tiempo aprieta? (orden de prioridad: DSR / cron / enum mercados / analytics / DX)
Resp: Ninguna, tenemos tiempo suficiente. Lo vamos a lograr.
B. DSR + CDM (modelo sobre candidatos)
¿Qué es “DSR” para vos en este producto? (API DeepSeek, otro modelo, reglas + LLM solo para copy, etc.)
Resp: DSR -- deep-seek-reasoner (api), es al que le paso un rubro de opciones de candidatos, y me devuelve opciones claras sobre cual es el mercado mas probable para un evento.
¿El modelo elige entre candidatos ya generados o también propone mercados/selecciones que hoy no pasan por build_candidates?
Anti-fuga (D-06-002): ¿Quién valida con vos el protocolo “qué puede ver el modelo” en producción diaria vs evaluación offline? (rol: vos, BE, DS externo)
Resp: no entiendo la preg
¿Necesitáis persistir salida DSR (JSON, tablas, pipeline_version, hash del input) para auditoría regulatoria / interna o alcanza con logs?
Resp: Los picks deben persistir para poder evaluar la eficiencia del modelo.
¿La “narrativa” en bóveda debe ser 100 % derivada del BE o puede haber plantillas FE con datos estructurados del API?
Resp: hibrida, puedes tambn consultar como v1 construye esa vista http://localhost:5173/runs/30/picks o http://localhost:5173/picks/311
C. Ingesta y operación (fetch_upcoming, cron)
¿Dónde debe correr el job en el primer entorno “serio”? (máquina única, k8s CronJob, GitHub Actions, otro)
Resp: DE momento maquina unica, esta.
Ventana horaria y TZ: ¿a qué hora se considera “día CDM” respecto al día operativo BT2?
Resp: NNo estoy seguro de entender bn la pregunta
¿Qué pasa si el job falla o devuelve 0 fixtures? (bloquear bóveda, usar snapshot anterior, alerta a Slack/email, umbral mínimo)
REsp: Debe haber un component visual tipo o estilo 404, o vista de 'no hay pick ahora, revise mas tarde'
¿Quién es dueño del runbook (on-call, nombre de canal, severidad)?
Resp: No entinedo la preg
D. Mercados canónicos (D-04-002 / D-06-003)
¿Alcance deportivo del enum en S6? ¿Solo fútbol, o multi-deporte desde el día 1?
DEsde el dia 1, multi, pero priorizando futbol por ahoira
¿Migración: ¿hay que backfill picks históricos o basta con solo hacia adelante desde una fecha?
Resp: Idealmente tenemos pensado hacer backtesting ciego
¿El settle actual debe seguir aceptando strings legacy un tiempo (modo dual) o corte duro en una fecha?
Resp: No entiendo
¿Quién define el mapa Sportmonks (o fuente) → canónico: solo BE, o BA + hoja compartida?
Resp: BE
E. Analytics MVP (D-06-004)
¿Para quién es el MVP? (operador, PO, growth, cumplimiento)
REsp: OPerador y PO
Lista 3–5 métricas que sí o sí querés ver en V2 en S6 (aunque sea una tabla fea).
Ver picks totalmente generados por DSR
¿Necesitáis series temporales (por operating_day_key) o alcanza con snapshot del día actual + ayer?
REsp: No entiendo la preg
¿Export / CSV es requisito en S6 o explícitamente no?
REsp: No de momento
F. Contratos y FE (US-DX-002, US-FE-052…054)
¿Bump de contractVersion: ¿un solo hito al cerrar S6 o uno por entrega (DSR, mercados, analytics)?
Resp: Por entrega
¿Compatibilidad: ¿el FE debe soportar API vieja y nueva un tiempo (feature flag) o deploy coordinado único?
Resp: define api vieja. Te refieres a V1? pq esa esta correidno en rutas distintas.
¿Qué pantallas tocan sí o sí con mercado canónico: bóveda, settlement, ledger, todas?
Resp: Todas las que involucren. Es decir en la vista de boveda lo importante respecto a dsr, es que teenga el el detalle especifico generado por el modelo, el resto son derivados estadisticos segun entiendo, pero corrigeme si me equivoco.
G. Límites con Sprint 07 y riesgos
Parlays, D-04-001 (COP sesión), diagnóstico longitudinal: confirmá que no entran en S6 salvo decisión explícita.
¿Principal riesgo que querés que el alcance mitigue (coste API, latencia, datos incorrectos, compliance)?
Resp: Compliance creo, pero no estoy seguro
¿Criterio de “S6 terminado”? (p. ej. “cron 7 días seguidos OK”, “0 picks con mercado no mapeado en prod”, “PO firmó checklist”, etc.)
Resp: LAs 3 qeu sugieres y puedes sugerir otros puntos especificos.
H. Metadatos del documento (para cuando me lo pases)

- Fecha y versión: **08-abril-2026 v1** + bloque **v1.1** (tabla siguiente).
- Participantes que validaron respuestas: *(completar: vos, BE, FE, PO).*

---

## v1.1 — Cierre de gaps (respuestas PO)

| Tema | Respuesta PO | Nota técnica (equipo) |
|------|----------------|------------------------|
| **Anti-fuga / backtest** | Para backtest, datos **≥ 24 h anteriores** al día que se evalúa en la corrida. | Regla mínima en **D-06-002** (enmienda). BE define ancla de “día” (UTC vs inicio día en TZ usuario). |
| **Input DSR** | **Prefiltro + candidatos en backend** → único input a DSR. Objetivo **15 picks** para franjas; si el modelo dice **sin valor**, no forzar. | Salida = elección **dentro del set** (validar esquema; no mercados fuera). Ver **D-06-008** / **D-06-013**. |
| **Calidad vs 15** | Duda: muchas ligas con valor → ¿cuándo un evento es candidato? | **Candidato** = CDM + umbral estadístico (doc.). Pool **M ≫ 15**; DSR ordena. **Sin relleno basura** → menos de 15 + UI honesta (**D-06-009**). |
| **Reloj / TZ** | **Hora del usuario** para día operativo y franjas. | `userTimeZone` BT2; job puede ser UTC; **etiquetado** día/franja en TZ usuario (**D-06-012**). |
| **Mercados / origen pick** | **Corte duro**: sugerencias publicadas en bóveda **solo** vía pipeline **DSR** (no regla legacy para armar el día). | **Liquidación** del pick = **determinística** (resultado), no LLM. Canónico en picks nuevos (**D-06-003** enmienda). |
| **Runbook** | “¿Qué sugieres?” | **Propuesta:** dueño **BE lead** (o rotación); alerta **email/Slack** (canal tipo `#bt2-ops`); severidad **P2** si falla un día; **US-OPS-001** con comando retry + ruta de logs. PO pone nombre/canal final. |
| **Compliance** | “Explicame mejor” | **D-06-014**: qué suele implicar (proveedor IA, PII, retención) y preguntas para legal. |

---

## Dudas abiertas (v1.2 / BE)

1. Umbral numérico “evento candidato” por deporte.
2. Canal/on-call **real** (sustituir placeholder).
3. Legal: jurisdicción usuarios + acuerdo con proveedor del modelo.

---

## v1.2 — Precisiones PO (métrica DSR + admin)

1. **“Se cumplió como predijo el modelo”:** al liquidar, contar cuántos picks **acertaron** según lo que DSR sugirió (p. ej. mercado 1X2 y ganó **home** si eso dijo el modelo; **over 2.5** si el resultado deportivo lo cumple; etc.). Detalle en **D-06-015** §3.
2. **Denominador:** meta **15** picks/día; si hay **N < 15** publicados, la métrica es **aciertos / N** (no forzar 15). **D-06-015** §4.
3. **Admin:** ahora acceso admin “abierto” por implementación; **TODO:** restringir por **rol de usuario** en iteración siguiente. **D-06-015** §5.

---

## Integración en repo

Volcado a **[`DECISIONES.md`](./DECISIONES.md)** — **D-06-015** (§3–§6) actualizado con v1.2; además **D-06-002** … **D-06-014** y v1.1.