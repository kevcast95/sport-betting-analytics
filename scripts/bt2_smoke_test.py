"""
Smoke test de integración dual — Sportmonks + The-Odds-API
Ejecutar desde la raíz del repo: python scripts/bt2_smoke_test.py

Ejecuta exactamente 4 requests (2 por proveedor) para validar
que las API keys funcionan y que la estructura de respuesta es
compatible con el CDM antes del Atraco Masivo.
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

# Cargar .env desde la raíz del repo
_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

SPORTMONKS_KEY = os.getenv("SPORTMONKS_API_KEY", "")
THEODDSAPI_KEY = os.getenv("THEODDSAPI_KEY", "")

RECON_DIR = _repo_root / "docs" / "bettracker2" / "recon_results"
RECON_DIR.mkdir(parents=True, exist_ok=True)

# IDs de ligas prioritarias
TARGET_LEAGUES = {8: "Premier League", 564: "La Liga", 2: "Champions League"}


def _ts() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def check_sportmonks() -> dict:
    """Ejecuta 2 requests a Sportmonks y retorna el resultado del smoke test."""
    result = {
        "leagues_total": None,
        "premier_league_found": False,
        "la_liga_found": False,
        "champions_found": False,
        "odds_field_present": False,
        "odds_structure": None,
        "credits_remaining": None,
        "errors": [],
    }

    base_url = "https://api.sportmonks.com/v3"
    headers = {"Accept": "application/json"}
    params_base = {"api_token": SPORTMONKS_KEY}

    with httpx.Client(timeout=20) as client:
        # --- Request 1: Ligas ---
        print(f"[{_ts()}] [SMOKE][SM] Request 1/2 — GET /football/leagues")
        try:
            r = client.get(
                f"{base_url}/football/leagues",
                headers=headers,
                params=params_base,
            )
            result["credits_remaining"] = r.headers.get("X-RateLimit-Remaining")
            if r.status_code == 200:
                data = r.json()
                leagues = data.get("data", [])
                result["leagues_total"] = len(leagues)
                league_ids = {lg.get("id") for lg in leagues}
                result["premier_league_found"] = 8 in league_ids
                result["la_liga_found"] = 564 in league_ids
                result["champions_found"] = 2 in league_ids
                print(f"[{_ts()}] [SMOKE][SM]   ✅ Ligas totales: {result['leagues_total']}")
            else:
                msg = f"HTTP {r.status_code} — {r.text[:200]}"
                result["errors"].append(f"leagues: {msg}")
                print(f"[{_ts()}] [SMOKE][SM]   ❌ {msg}")
        except Exception as exc:
            result["errors"].append(f"leagues: {exc}")
            print(f"[{_ts()}] [SMOKE][SM]   ❌ Excepción: {exc}")

        # --- Request 2: Fixtures de hoy (o ayer si no hay) ---
        for delta in (0, -1):
            target_date = (date.today() + timedelta(days=delta)).isoformat()
            print(f"[{_ts()}] [SMOKE][SM] Request 2/2 — GET /football/fixtures/date/{target_date}")
            try:
                r2 = client.get(
                    f"{base_url}/football/fixtures/date/{target_date}",
                    headers=headers,
                    params={**params_base, "include": "participants;odds"},
                )
                if r2.headers.get("X-RateLimit-Remaining"):
                    result["credits_remaining"] = r2.headers.get("X-RateLimit-Remaining")
                if r2.status_code == 200:
                    fixtures = r2.json().get("data", [])
                    if fixtures:
                        first = fixtures[0]
                        odds = first.get("odds", [])
                        result["odds_field_present"] = True
                        if odds:
                            sample = odds[0] if isinstance(odds, list) else odds
                            result["odds_structure"] = {
                                k: type(v).__name__ for k, v in sample.items()
                            } if isinstance(sample, dict) else str(type(sample))
                        else:
                            result["odds_structure"] = "campo odds presente pero vacío"
                        print(f"[{_ts()}] [SMOKE][SM]   ✅ Fixtures ({target_date}): {len(fixtures)}, odds field present: {result['odds_field_present']}")
                        break
                    else:
                        print(f"[{_ts()}] [SMOKE][SM]   ⚠️  Sin fixtures para {target_date}, probando ayer...")
                else:
                    msg = f"HTTP {r2.status_code} — {r2.text[:200]}"
                    result["errors"].append(f"fixtures: {msg}")
                    print(f"[{_ts()}] [SMOKE][SM]   ❌ {msg}")
                    break
            except Exception as exc:
                result["errors"].append(f"fixtures: {exc}")
                print(f"[{_ts()}] [SMOKE][SM]   ❌ Excepción: {exc}")
                break

    return result


def check_theoddsapi() -> dict:
    """Ejecuta 2 requests a The-Odds-API y retorna el resultado del smoke test."""
    result = {
        "soccer_epl_available": False,
        "bookmakers_count": None,
        "outcomes_structure": None,
        "requests_used": None,
        "requests_remaining": None,
        "errors": [],
    }

    base_url = "https://api.the-odds-api.com/v4"

    with httpx.Client(timeout=20) as client:
        # --- Request 1: Lista de deportes ---
        print(f"[{_ts()}] [SMOKE][ODDS] Request 1/2 — GET /v4/sports")
        try:
            r = client.get(
                f"{base_url}/sports",
                params={"apiKey": THEODDSAPI_KEY},
            )
            result["requests_remaining"] = r.headers.get("x-requests-remaining")
            result["requests_used"] = r.headers.get("x-requests-used")
            if r.status_code == 200:
                sports = r.json()
                keys = {s.get("key") for s in sports}
                result["soccer_epl_available"] = "soccer_epl" in keys
                print(f"[{_ts()}] [SMOKE][ODDS]   ✅ Deportes disponibles: {len(sports)}, soccer_epl: {result['soccer_epl_available']}")
            else:
                msg = f"HTTP {r.status_code} — {r.text[:200]}"
                result["errors"].append(f"sports: {msg}")
                print(f"[{_ts()}] [SMOKE][ODDS]   ❌ {msg}")
        except Exception as exc:
            result["errors"].append(f"sports: {exc}")
            print(f"[{_ts()}] [SMOKE][ODDS]   ❌ Excepción: {exc}")

        # --- Request 2: Odds soccer_epl ---
        print(f"[{_ts()}] [SMOKE][ODDS] Request 2/2 — GET /v4/odds (soccer_epl, h2h, eu)")
        try:
            r2 = client.get(
                f"{base_url}/odds",
                params={
                    "apiKey": THEODDSAPI_KEY,
                    "sport": "soccer_epl",
                    "regions": "eu",
                    "markets": "h2h",
                    "dateFormat": "iso",
                },
            )
            result["requests_remaining"] = r2.headers.get("x-requests-remaining")
            result["requests_used"] = r2.headers.get("x-requests-used")
            if r2.status_code == 200:
                events = r2.json()
                if events:
                    first_event = events[0]
                    bookmakers = first_event.get("bookmakers", [])
                    result["bookmakers_count"] = len(bookmakers)
                    if bookmakers:
                        first_bm = bookmakers[0]
                        markets = first_bm.get("markets", [])
                        if markets:
                            outcomes = markets[0].get("outcomes", [])
                            if outcomes:
                                sample = outcomes[0]
                                result["outcomes_structure"] = {
                                    k: type(v).__name__ for k, v in sample.items()
                                }
                    print(f"[{_ts()}] [SMOKE][ODDS]   ✅ Eventos: {len(events)}, bookmakers (1er evento): {result['bookmakers_count']}")
                else:
                    result["bookmakers_count"] = 0
                    print(f"[{_ts()}] [SMOKE][ODDS]   ⚠️  Sin eventos activos en soccer_epl")
            else:
                msg = f"HTTP {r2.status_code} — {r2.text[:200]}"
                result["errors"].append(f"odds: {msg}")
                print(f"[{_ts()}] [SMOKE][ODDS]   ❌ {msg}")
        except Exception as exc:
            result["errors"].append(f"odds: {exc}")
            print(f"[{_ts()}] [SMOKE][ODDS]   ❌ Excepción: {exc}")

    return result


def generate_report(sm: dict, odds: dict) -> Path:
    """Genera el reporte markdown en docs/bettracker2/recon_results/."""
    today = date.today().isoformat()

    def check(val: bool) -> str:
        return "✅" if val else "❌"

    sm_ok = (
        sm["leagues_total"] is not None
        and sm["premier_league_found"]
        and not [e for e in sm["errors"] if "leagues" in e]
    )
    odds_ok = (
        odds["soccer_epl_available"]
        and not [e for e in odds["errors"] if "sports" in e]
    )
    proceed = sm_ok and odds_ok

    sm_credits = sm.get("credits_remaining") or "n/d"
    odds_remaining = odds.get("requests_remaining") or "n/d"
    odds_used = odds.get("requests_used") or "n/d"

    odds_structure_str = (
        json.dumps(odds["outcomes_structure"], ensure_ascii=False)
        if odds["outcomes_structure"]
        else "no disponible"
    )
    sm_odds_structure_str = (
        json.dumps(sm["odds_structure"], ensure_ascii=False)
        if sm["odds_structure"]
        else "no disponible"
    )

    sm_errors_str = "; ".join(sm["errors"]) if sm["errors"] else "ninguno"
    odds_errors_str = "; ".join(odds["errors"]) if odds["errors"] else "ninguno"

    report = f"""# Smoke Test — {today}

## Sportmonks

- Ligas totales: {sm["leagues_total"] or "n/d"}
- Premier League (ID 8): {check(sm["premier_league_found"])}
- La Liga (ID 564): {check(sm["la_liga_found"])}
- Champions (ID 2): {check(sm["champions_found"])}
- Campo odds en fixture: {check(sm["odds_field_present"])}
- Estructura odds: {sm_odds_structure_str}
- Créditos restantes: {sm_credits} / 3000
- Errores: {sm_errors_str}

## The-Odds-API

- soccer_epl disponible: {check(odds["soccer_epl_available"])}
- Bookmakers retornados: {odds["bookmakers_count"] if odds["bookmakers_count"] is not None else "n/d"}
- Estructura outcomes: {odds_structure_str}
- Requests usados: {odds_used}
- Requests restantes: {odds_remaining}
- Errores: {odds_errors_str}

## Decisión: {"✅ Proceder con Atraco" if proceed else "❌ Revisar antes de continuar"}
"""

    output_path = RECON_DIR / f"smoke_test_{today}.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"\n[SMOKE] Reporte generado: {output_path}")
    return output_path


if __name__ == "__main__":
    print(f"[{_ts()}] [SMOKE] Iniciando smoke test dual — {date.today().isoformat()}")
    print(f"[{_ts()}] [SMOKE] SPORTMONKS_KEY presente: {'✅' if SPORTMONKS_KEY else '❌'}")
    print(f"[{_ts()}] [SMOKE] THEODDSAPI_KEY presente:  {'✅' if THEODDSAPI_KEY else '❌'}")
    print()

    sm_result = check_sportmonks()
    print()
    odds_result = check_theoddsapi()
    print()

    report_path = generate_report(sm_result, odds_result)
    print(f"[{_ts()}] [SMOKE] Finalizado. Revisar: {report_path}")
    sys.exit(0)
