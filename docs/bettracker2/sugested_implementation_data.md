# 🏛️ MASTER CONTEXT: Arquitectura y Directrices de BetTracker 2.0

## 1. Identidad del Producto y Filosofía UX/UI
BetTracker 2.0 **no** es un agregador de pronósticos de casino. Es un **Protocolo de Gestión Conductual y Riesgo Financiero**.
* **Misión:** Proteger al usuario de la varianza estadística y del "tilt" emocional. El sistema audita el bankroll, aplica bloqueos y premia la disciplina.
* **Estética Visual (UI):** Prohibidos los colores neón, alto contraste o estéticas de "cabina de avión/videojuego". La UI debe ser pacífica, limpia y transmitir "gestión profesional y confianza tranquila" (tonos pastel, grises claros, diseño modular).
* **Traducción Humana (UX Copywriting):** El frontend tiene PROHIBIDO mostrar estadísticas frías sin contexto. Todo dato debe traducirse:
  * *Malo:* `<StatCard title="ROI" value={5} />`
  * *Obligatorio:* `<BehavioralCard status="positive" text="Retorno Sostenible: Tu sistema genera 5 COP de ganancia limpia por cada 100 COP." />`

## 2. La Arquitectura Híbrida (Capa Anticorrupción - ACL)
Se deprecia el web scraping. Adoptamos un modelo **API-First** de doble capa con una estricta **Capa Anticorrupción**.
* **Regla de Agnosticismo:** El Frontend en React y el motor de IA (DeepSeek) **JAMÁS** deben conocer los DTOs crudos de los proveedores. El backend transforma todo y escupe un Modelo Canónico universal. Esto garantiza que el sistema sea *Plug-and-Play* (si mañana añadimos NBA o Tenis, el frontend no cambia).

## 3. Infraestructura de Datos y Proveedores
Explotamos las fortalezas de dos líderes para garantizar backtesting sin sesgos (*look-ahead bias*):
* **Motor Táctico (Sportmonks V3):** Provee la telemetría pesada (Goles Esperados xG, eventos, ausencias). Usaremos el parámetro pseudo-GraphQL `include` para evitar consultas N+1.
* **Motor Financiero (The-Odds-API):** Nuestra máquina del tiempo. Provee capturas (*snapshots*) históricas de líneas de cierre exactas para múltiples mercados (H2H, Spreads, Totals).

## 4. Resolución de Identidades (Identity Mapping)
El mayor reto del backend es cruzar el ID de Sportmonks con el Hash de The-Odds-API. Se usará el ID oficial de la Casa de Apuestas (ej. Bet365) como pivote criptográfico:
* *Desde Sportmonks:* `GET /odds/bookmakers/fixtures/{id}/mapping`
* *Desde The-Odds:* Consultar con el parámetro `includeSids=true`.

## 5. El Modelo de Datos Canónico (CDM) - Contrato JSON
El Frontend consumirá esta estructura exacta. (Nota: el array `markets` es dinámico para soportar expansión).
```json
{
  "id": "bt_evt_987654321",
  "status": "PRE_MATCH",
  "metadata": { "competition_name": "Premier League", "sport": "FOOTBALL" },
  "participants": [
    { "role": "HOME", "name": "Arsenal", "provider_mappings": { "sportmonks_id": 8, "odds_api_name": "Arsenal" } }
  ],
  "tactical_context": { "home_expected_goals_avg": 2.1, "key_absences": ["Saka (ARS)"] },
  "financial_matrix": {
    "markets": [
      { "type": "match_winner", "options": [ { "label": "HOME", "price": 2.10 } ] },
      { "type": "totals", "line": 2.5, "options": [ { "label": "OVER", "price": 1.85 } ] }
    ]
  },
  "ai_audit": {
    "recommended_action": "VALUE_FOUND_OVER_2_5",
    "human_translation": "El modelo detecta ineficiencia en goles totales. Ausencia de defensores clave eleva probabilidad de un partido abierto."
  }
}
6. Estrategia de Ingesta Histórica (El "Atraco Maestro")
Para el entrenamiento masivo de IA (~35 GB de datos / 120 ligas / 5 años), el backend ejecutará una operación crítica:

Workers Resilientes: Para Sportmonks (límite de 3k req/hora), usar colas de tareas (BullMQ/Celery). Si da error 429, el worker se pausa 60 minutos y retoma.

Caché Persistente Financiero: Las consultas históricas a The-Odds-API cuestan x10 créditos. El backend debe guardar cada snapshot en PostgreSQL y marcar el ID como inmutable. Prohibido volver a gastar créditos en un ID ya procesado.

Up-Scaling Temporal: Se usará un plan gigante en The-Odds ($119/mes) por 1 mes para descargar la historia, y luego se hará downgrade al plan base ($30/mes) para la operativa diaria en vivo.

7. Rol y Directrices para el Agente/Cursor
Tu misión principal al leer este documento es:

Validar la viabilidad de implementar estos componentes en nuestra base de código actual (React/Node o Python).

Priorizar la construcción de un estado global robusto para la lógica conductual en el frontend.

Tipar estrictamente el Modelo Canónico usando TypeScript.

NO iterar a ciegas: Si una propuesta de refactorización rompe el principio de Capa Anticorrupción o sugiere colores estridentes para la UI, debes detenerte y levantar una alerta arquitectónica.