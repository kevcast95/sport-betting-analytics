# Smoke Test — 2026-04-05

## Sportmonks

- Ligas totales (pág 1, default): 25 — con per_page=50: **50 ligas**
- Premier League (ID 8): ✅
- La Liga (ID 564): ✅ *(aparece en posición 50 — fuera del default de 25)*
- Champions (ID 2): ❌ — no está en las primeras 50 ligas del plan
- Campo odds en fixture: ✅
- Estructura odds: {"id": "int", "fixture_id": "int", "market_id": "int", "bookmaker_id": "int", "label": "str", "value": "str", "name": "str", "sort_order": "int", "market_description": "str", "probability": "str", "dp3": "str", "fractional": "str", "american": "str", "winning": "bool", "stopped": "bool", "total": "NoneType", "handicap": "str", "participants": "NoneType", "created_at": "str", "original_label": "str", "latest_bookmaker_update": "str"}
- Créditos restantes: 2998 / 3000 *(3 requests ejecutados: 2 smoke + 1 recon ligas)*
- Errores: ninguno

## The-Odds-API

- soccer_epl disponible: ✅
- Bookmakers retornados: n/d
- Estructura outcomes: no disponible
- Requests usados: n/d
- Requests restantes: n/d
- Errores: odds: HTTP 404 — <!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try agai

## Decisión: ✅ Proceder con Atraco

---

## Ligas disponibles en el plan (lista completa)

Request: `GET /v3/football/leagues?per_page=50` — 50 ligas retornadas, créditos tras esta request: 2,998/3,000.

> **Nota:** La API pagina por defecto a 25 por página. Con `per_page=50` se obtienen las primeras 50 ligas del plan. La Liga (ID 564) aparece en posición 50. Champions League (ID 2) **no** está en esta página — puede requerir paginación adicional o no estar incluido en el plan activo.

| ID | Nombre | País |
|----|--------|------|
| 8 | Premier League | England |
| 9 | Championship | England |
| 12 | League One | England |
| 14 | League Two | England |
| 17 | Enterprise National League | England |
| 23 | Community Shield | England |
| 24 | FA Cup | England |
| 27 | Carabao Cup | England |
| 45 | Women's Super League | England |
| 72 | Eredivisie | Netherlands |
| 74 | Eerste Divisie | Netherlands |
| 78 | KNVB Beker | Netherlands |
| 82 | Bundesliga | Germany |
| 85 | 2. Bundesliga | Germany |
| 88 | 3. Liga | Germany |
| 109 | DFB Pokal | Germany |
| 181 | Admiral Bundesliga | Austria |
| 208 | Pro League | Belgium |
| 211 | Challenger Pro League | Belgium |
| 229 | First League | Bulgaria |
| 244 | 1. HNL | Croatia |
| 262 | Chance Liga | Czech Republic |
| 271 | Superliga | Denmark |
| 274 | First Division | Denmark |
| 292 | Veikkausliiga | Finland |
| 301 | Ligue 1 | France |
| 304 | Ligue 2 | France |
| 307 | Coupe de France | France |
| 310 | Coupe de la Ligue | France |
| 325 | Super League | Greece |
| 334 | NB I | Hungary |
| 360 | Premier Division | Ireland |
| 372 | Ligat ha'Al | Israel |
| 384 | Serie A | Italy |
| 387 | Serie B | Italy |
| 390 | Coppa Italia | Italy |
| 444 | Eliteserien | Norway |
| 453 | Ekstraklasa | Poland |
| 462 | Liga Portugal | Portugal |
| 465 | Liga Portugal 2 | Portugal |
| 468 | Taça De Portugal | Portugal |
| 474 | Superliga | Romania |
| 486 | Premier League | Russia |
| 489 | FNL | Russia |
| 492 | Russian Cup | Russia |
| 501 | Premiership | Scotland |
| 513 | Premiership Play-Offs | Scotland |
| 531 | Super Liga | Serbia |
| 540 | Niké Liga | Slovakia |
| 564 | La Liga | Spain |

**Ligas prioritarias del Atraco confirmadas en el plan:**

| Liga | ID | Estado |
|------|----|--------|
| Premier League | 8 | ✅ |
| La Liga | 564 | ✅ |
| Bundesliga | 82 | ✅ |
| Serie A | 384 | ✅ |
| Champions League | 2 | ❌ — no aparece en primeras 50 |
| Ligue 1 | 301 | ✅ (bonus — está disponible) |
