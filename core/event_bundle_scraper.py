#!/usr/bin/env python3
"""
event_bundle_scraper.py

Pipeline unificado por eventId:
- Descarga payloads crudos de SofaScore (event, lineups, statistics, odds/all, odds/featured)
- Aplica processors puros
- Entrega un JSON limpio y estable para consumo por agentes/LLMs
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict

from playwright.async_api import async_playwright

from processors.lineups_processor import process_lineups
from processors.odds_all_processor import process_odds_all
from processors.odds_feature_processor import process_odds_feature
from processors.statistics_processor import process_statistics


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_failure_detail(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Si _fetch_json devolvió error, exponer HTTP status para depuración (p. ej. 403)."""
    if not isinstance(raw, dict) or not raw.get("_error"):
        return {}
    return {
        "http_status": raw.get("_status"),
        "message": raw.get("_statusText"),
        "url": raw.get("_url"),
    }


def _safe_event_meta(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    event = raw_event.get("event") if isinstance(raw_event.get("event"), dict) else raw_event
    if not isinstance(event, dict):
        return {}
    home = event.get("homeTeam") or {}
    away = event.get("awayTeam") or {}
    tournament = event.get("tournament") or {}
    status = event.get("status") or {}

    from typing import Optional

    def _to_int(x: Any) -> Optional[int]:
        if x is None:
            return None
        if isinstance(x, int):
            return x
        try:
            # Evita casos tipo "1" o "1.0"
            s = str(x).strip()
            if not s:
                return None
            return int(float(s.replace(",", ".")))
        except Exception:
            return None

    def _extract_score(score_obj: Any) -> Optional[int]:
        # Normalmente viene como int, pero a veces como dict (current/value/etc.)
        if isinstance(score_obj, dict):
            for k in ("current", "value", "display", "total"):
                if k in score_obj:
                    return _to_int(score_obj.get(k))
            return _to_int(score_obj.get("current"))
        return _to_int(score_obj)

    status_desc = str(status.get("description") or "").lower()
    status_type = str(status.get("type") or "").lower()
    status_code = status.get("code")
    is_finished = (
        ("finished" in status_desc)
        or ("ft" in status_desc)
        or (status_code == 100)
        or (status_type == "finished")
    )
    match_state = "finished" if is_finished else ("live" if "live" in status_desc or status_code in (0, 31, 32, 33, 34, 61, 71) else "not started")

    home_score = _extract_score(event.get("homeScore"))
    away_score = _extract_score(event.get("awayScore"))

    derived_1x2: Optional[str] = None
    if home_score is not None and away_score is not None:
        if home_score > away_score:
            derived_1x2 = "1"
        elif home_score < away_score:
            derived_1x2 = "2"
        else:
            derived_1x2 = "X"
    return {
        "event_id": event.get("id"),
        "sport": (event.get("sport") or {}).get("name") if isinstance(event.get("sport"), dict) else event.get("sport"),
        "tournament": tournament.get("name"),
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "start_timestamp": event.get("startTimestamp"),
        "status": status.get("description") or status.get("type") or status.get("code"),
        "match_state": match_state,
        "home_score": home_score,
        "away_score": away_score,
        # Veredicto 1X2 derivado del marcador final (solo cuando hay scores).
        "result_1x2": derived_1x2,
    }


# Cabeceras tipo navegador: SofaScore suele devolver 403 en /statistics y /lineups
# si el fetch no lleva Referer/Origin (en el browser al pegar la URL sí aplica contexto de sitio).
_FETCH_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}


async def _fetch_json(context, url: str) -> Dict[str, Any]:
    """
    Usa APIRequestContext del mismo BrowserContext (cookies + TLS coherentes).
    Más fiable que page.evaluate(fetch(...)) ante anti-bot en sub-rutas de API.
    """
    try:
        resp = await context.request.get(url, headers=_FETCH_HEADERS)
        if not resp.ok:
            return {
                "_error": True,
                "_status": resp.status,
                "_statusText": resp.status_text or "",
                "_url": url,
            }
        data = await resp.json()
        return data if isinstance(data, dict) else {"_error": True, "_status": -2, "_statusText": "json_not_object", "_url": url}
    except Exception as e:
        return {
            "_error": True,
            "_status": -1,
            "_statusText": str(e),
            "_url": url,
        }


async def fetch_event_bundle(event_id: int) -> Dict[str, Any]:
    base = "https://www.sofascore.com/api/v1"
    urls = {
        "event": f"{base}/event/{event_id}",
        "lineups": f"{base}/event/{event_id}/lineups",
        "statistics": f"{base}/event/{event_id}/statistics",
        "odds_all": f"{base}/event/{event_id}/odds/1/all",
        "odds_featured": f"{base}/event/{event_id}/odds/1/featured",
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()
        await page.goto("https://www.sofascore.com/", wait_until="domcontentloaded")

        raw_event = await _fetch_json(context, urls["event"])
        raw_lineups = await _fetch_json(context, urls["lineups"])
        raw_statistics = await _fetch_json(context, urls["statistics"])
        raw_odds_all = await _fetch_json(context, urls["odds_all"])
        raw_odds_featured = await _fetch_json(context, urls["odds_featured"])

        await browser.close()

    processed = {
        "lineups": process_lineups(raw_lineups if isinstance(raw_lineups, dict) else {}),
        "statistics": process_statistics(raw_statistics if isinstance(raw_statistics, dict) else {}),
        "odds_all": process_odds_all(raw_odds_all if isinstance(raw_odds_all, dict) else {}),
        "odds_featured": process_odds_feature(raw_odds_featured if isinstance(raw_odds_featured, dict) else {}),
    }

    diagnostics = {
        "event_ok": not bool(raw_event.get("_error")) if isinstance(raw_event, dict) else False,
        "lineups_ok": not bool(raw_lineups.get("_error")) if isinstance(raw_lineups, dict) else False,
        "statistics_ok": not bool(raw_statistics.get("_error")) if isinstance(raw_statistics, dict) else False,
        "odds_all_ok": not bool(raw_odds_all.get("_error")) if isinstance(raw_odds_all, dict) else False,
        "odds_featured_ok": not bool(raw_odds_featured.get("_error")) if isinstance(raw_odds_featured, dict) else False,
        # Solo entradas con fallo real (evita ruido en JSON)
        "fetch_errors": {
            k: v
            for k, v in (
                ("event", _fetch_failure_detail(raw_event if isinstance(raw_event, dict) else {})),
                ("lineups", _fetch_failure_detail(raw_lineups if isinstance(raw_lineups, dict) else {})),
                ("statistics", _fetch_failure_detail(raw_statistics if isinstance(raw_statistics, dict) else {})),
                ("odds_all", _fetch_failure_detail(raw_odds_all if isinstance(raw_odds_all, dict) else {})),
                ("odds_featured", _fetch_failure_detail(raw_odds_featured if isinstance(raw_odds_featured, dict) else {})),
            )
            if v
        },
    }

    return {
        "bundle_meta": {
            "generated_at_utc": _utc_now_iso(),
            "source": "sofascore",
            "event_id": event_id,
        },
        "event_context": _safe_event_meta(raw_event if isinstance(raw_event, dict) else {}),
        "diagnostics": diagnostics,
        "processed": processed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline unificado por eventId para OpenClaw/DeepSeek.")
    parser.add_argument("--event-id", "-e", type=int, required=True, help="ID del evento en SofaScore.")
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON con indentación.")
    return parser.parse_args()


async def _cli_main(args: argparse.Namespace) -> None:
    bundle = await fetch_event_bundle(args.event_id)
    if args.pretty:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(bundle, ensure_ascii=False))


if __name__ == "__main__":
    cli_args = parse_args()
    asyncio.run(_cli_main(cli_args))

