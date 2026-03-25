#!/usr/bin/env python3
"""
event_bundle_scraper.py

Pipeline unificado por eventId:
- Descarga payloads crudos de SofaScore (event, lineups, statistics, h2h, team-streaks,
  odds/all, odds/featured, y estadísticas de temporada local/visitante en la misma liga)
- Tenis (sport=tennis): además rankings por jugador, team-statistics/seasons, catálogo
  categories/all + default-unique-tournaments (cache por proceso), y resumen statistics tenis.
- Aplica processors puros
- Entrega un JSON limpio y estable para consumo por agentes/LLMs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

from processors.h2h_processor import process_h2h
from processors.lineups_processor import process_lineups
from processors.odds_all_processor import process_odds_all
from processors.odds_feature_processor import process_odds_feature
from processors.statistics_processor import process_statistics
from processors.team_season_stats_processor import process_team_season_stats
from processors.team_streaks_processor import process_team_streaks
from processors.tennis_odds_processor import process_tennis_odds_all
from processors.tennis_rankings_processor import process_team_rankings
from processors.tennis_registry_processor import (
    summarize_default_unique_tournaments,
    summarize_tennis_categories,
)
from processors.tennis_statistics_processor import process_tennis_event_statistics
from processors.tennis_team_seasons_discovery_processor import process_team_statistics_seasons

# Catálogo global (categories + default tournaments): 1 fetch por proceso salvo ALTEA_TENNIS_REGISTRY_CACHE=0
_TENNIS_GLOBAL_REGISTRY: Optional[Dict[str, Any]] = None


async def _ensure_tennis_global_registry(context: Any, base: str) -> None:
    global _TENNIS_GLOBAL_REGISTRY
    if _TENNIS_GLOBAL_REGISTRY is not None:
        return
    country = (os.environ.get("ALTEA_TENNIS_PRIORITY_COUNTRY") or "CO").strip().upper() or "CO"
    raw_c = await _fetch_json(context, f"{base}/sport/tennis/categories/all")
    raw_d = await _fetch_json(context, f"{base}/config/default-unique-tournaments/{country}/tennis")
    _TENNIS_GLOBAL_REGISTRY = {
        "categories_raw": raw_c,
        "default_unique_tournaments_raw": raw_d,
        "priority_country": country,
    }


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
    season_obj = event.get("season") or {}
    ut_obj = tournament.get("uniqueTournament") if isinstance(tournament.get("uniqueTournament"), dict) else {}
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
    out: Dict[str, Any] = {
        "event_id": event.get("id"),
        "sport": (event.get("sport") or {}).get("name") if isinstance(event.get("sport"), dict) else event.get("sport"),
        "sport_slug": (event.get("sport") or {}).get("slug")
        if isinstance(event.get("sport"), dict)
        else None,
        "tournament": tournament.get("name"),
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "home_team_id": _to_int(home.get("id")),
        "away_team_id": _to_int(away.get("id")),
        "unique_tournament_id": _to_int(ut_obj.get("id")),
        "season_id": _to_int(season_obj.get("id")),
        "season_name": season_obj.get("name"),
        "start_timestamp": event.get("startTimestamp"),
        "status": status.get("description") or status.get("type") or status.get("code"),
        "match_state": match_state,
        "home_score": home_score,
        "away_score": away_score,
        # Veredicto 1X2 derivado del marcador final (solo cuando hay scores).
        "result_1x2": derived_1x2,
    }
    if event.get("groundType") is not None:
        out["ground_type"] = event.get("groundType")
    ri = event.get("roundInfo")
    if isinstance(ri, dict):
        out["round_name"] = ri.get("name") or ri.get("round")
        out["round_slug"] = ri.get("slug")
    ef = event.get("eventFilters")
    if isinstance(ef, dict):
        out["event_filters"] = {
            "category": ef.get("category"),
            "level": ef.get("level"),
            "gender": ef.get("gender"),
        }
    return out


# Cabeceras tipo navegador: SofaScore suele devolver 403 en /statistics y /lineups
# si el fetch no lleva Referer/Origin (en el browser al pegar la URL sí aplica contexto de sitio).
_FETCH_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}


def _resolve_playwright_chrome_executable() -> Optional[str]:
    """
    Resuelve el binario compatible con la arquitectura presente bajo PLAYWRIGHT_BROWSERS_PATH.
    Prioriza el Chromium completo (más estable en algunos entornos) y si no, usa el chrome-headless-shell.
    """
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not base or not os.path.isdir(base):
        return None

    try:
        entries = os.listdir(base)
    except Exception:
        return None

    # 1) Chromium completo (ej. chromium-<rev>/chrome-mac-arm64/Google Chrome for Testing.app/...)
    for entry in entries:
        if not entry.startswith("chromium-"):
            continue
        rev_root = os.path.join(base, entry)
        for arch_dir in ("chrome-mac-arm64", "chrome-mac-x64"):
            candidate = os.path.join(
                rev_root,
                arch_dir,
                "Google Chrome for Testing.app",
                "Contents",
                "MacOS",
                "Google Chrome for Testing",
            )
            if os.path.exists(candidate):
                return candidate

    # 2) Headless shell (fallback)
    for entry in entries:
        if not entry.startswith("chromium_headless_shell-"):
            continue
        rev_root = os.path.join(base, entry)
        for arch_dir in ("chrome-headless-shell-mac-arm64", "chrome-headless-shell-mac-x64"):
            candidate = os.path.join(rev_root, arch_dir, "chrome-headless-shell")
            if os.path.exists(candidate):
                return candidate

    return None


def _season_stats_urls(
    base: str,
    *,
    home_team_id: int,
    away_team_id: int,
    unique_tournament_id: int,
    season_id: int,
) -> Dict[str, str]:
    path = f"unique-tournament/{unique_tournament_id}/season/{season_id}/statistics/overall"
    return {
        "team_season_home": f"{base}/team/{home_team_id}/{path}",
        "team_season_away": f"{base}/team/{away_team_id}/{path}",
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


async def fetch_event_bundle(event_id: int, *, sport: str = "football") -> Dict[str, Any]:
    global _TENNIS_GLOBAL_REGISTRY
    if os.environ.get("ALTEA_TENNIS_REGISTRY_CACHE", "1").lower() in ("0", "false", "no"):
        _TENNIS_GLOBAL_REGISTRY = None

    sport_l = (sport or "football").strip().lower()
    base = "https://www.sofascore.com/api/v1"
    urls = {
        "event": f"{base}/event/{event_id}",
        "lineups": f"{base}/event/{event_id}/lineups",
        "statistics": f"{base}/event/{event_id}/statistics",
        "h2h": f"{base}/event/{event_id}/h2h",
        "team_streaks": f"{base}/event/{event_id}/team-streaks",
        "odds_all": f"{base}/event/{event_id}/odds/1/all",
        "odds_featured": f"{base}/event/{event_id}/odds/1/featured",
    }

    raw_team_season_home: Dict[str, Any] = {}
    raw_team_season_away: Dict[str, Any] = {}
    raw_rank_home: Dict[str, Any] = {}
    raw_rank_away: Dict[str, Any] = {}
    raw_tss_home: Dict[str, Any] = {}
    raw_tss_away: Dict[str, Any] = {}

    async with async_playwright() as p:
        executable_path = _resolve_playwright_chrome_executable()
        if executable_path:
            browser = await p.chromium.launch(headless=True, executable_path=executable_path)
        else:
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
        raw_h2h = await _fetch_json(context, urls["h2h"])
        raw_team_streaks = await _fetch_json(context, urls["team_streaks"])
        raw_odds_all = await _fetch_json(context, urls["odds_all"])
        raw_odds_featured = await _fetch_json(context, urls["odds_featured"])

        ev_for_ids = raw_event.get("event") if isinstance(raw_event.get("event"), dict) else raw_event
        if isinstance(ev_for_ids, dict):
            home_t = ev_for_ids.get("homeTeam") or {}
            away_t = ev_for_ids.get("awayTeam") or {}
            tourn = ev_for_ids.get("tournament") or {}
            seas = ev_for_ids.get("season") or {}
            ut = tourn.get("uniqueTournament") if isinstance(tourn.get("uniqueTournament"), dict) else {}
            try:
                hid = int(home_t.get("id"))
                aid = int(away_t.get("id"))
                utid = int(ut.get("id"))
                sid = int(seas.get("id"))
                ss_urls = _season_stats_urls(base, home_team_id=hid, away_team_id=aid, unique_tournament_id=utid, season_id=sid)
                raw_team_season_home = await _fetch_json(context, ss_urls["team_season_home"])
                raw_team_season_away = await _fetch_json(context, ss_urls["team_season_away"])
                if sport_l == "tennis":
                    await _ensure_tennis_global_registry(context, base)
                    raw_rank_home = await _fetch_json(context, f"{base}/team/{hid}/rankings")
                    raw_rank_away = await _fetch_json(context, f"{base}/team/{aid}/rankings")
                    raw_tss_home = await _fetch_json(
                        context, f"{base}/team/{hid}/team-statistics/seasons"
                    )
                    raw_tss_away = await _fetch_json(
                        context, f"{base}/team/{aid}/team-statistics/seasons"
                    )
            except (TypeError, ValueError):
                raw_team_season_home = {"_error": True, "_status": 0, "_statusText": "missing_ids_for_season_stats", "_url": ""}
                raw_team_season_away = {"_error": True, "_status": 0, "_statusText": "missing_ids_for_season_stats", "_url": ""}

        await browser.close()

    raw_h2h_d = raw_h2h if isinstance(raw_h2h, dict) else {}
    raw_streaks_d = raw_team_streaks if isinstance(raw_team_streaks, dict) else {}

    proc_h2h = process_h2h(raw_h2h_d)
    proc_streaks = process_team_streaks(raw_streaks_d)

    r_tsh = raw_team_season_home if isinstance(raw_team_season_home, dict) else {}
    r_tsa = raw_team_season_away if isinstance(raw_team_season_away, dict) else {}
    proc_tsh = process_team_season_stats(r_tsh, side="home")
    proc_tsa = process_team_season_stats(r_tsa, side="away")

    processed: Dict[str, Any] = {
        "lineups": process_lineups(raw_lineups if isinstance(raw_lineups, dict) else {}),
        "statistics": process_statistics(raw_statistics if isinstance(raw_statistics, dict) else {}),
        "h2h": proc_h2h,
        "team_streaks": proc_streaks,
        "team_season_stats": {
            "home": proc_tsh,
            "away": proc_tsa,
        },
        "odds_all": process_odds_all(raw_odds_all if isinstance(raw_odds_all, dict) else {}),
        "odds_featured": process_odds_feature(raw_odds_featured if isinstance(raw_odds_featured, dict) else {}),
    }
    if sport_l == "tennis":
        processed["tennis_odds"] = process_tennis_odds_all(
            raw_odds_all if isinstance(raw_odds_all, dict) else {}
        )
        processed["tennis_statistics"] = process_tennis_event_statistics(
            raw_statistics if isinstance(raw_statistics, dict) else {}
        )
        rh = raw_rank_home if isinstance(raw_rank_home, dict) else {}
        ra = raw_rank_away if isinstance(raw_rank_away, dict) else {}
        processed["tennis_rankings"] = {
            "home": process_team_rankings(rh),
            "away": process_team_rankings(ra),
        }
        tsh = raw_tss_home if isinstance(raw_tss_home, dict) else {}
        tsa = raw_tss_away if isinstance(raw_tss_away, dict) else {}
        processed["tennis_team_statistics_seasons"] = {
            "home": process_team_statistics_seasons(tsh),
            "away": process_team_statistics_seasons(tsa),
        }
        if _TENNIS_GLOBAL_REGISTRY is not None:
            gr = _TENNIS_GLOBAL_REGISTRY
            processed["tennis_registry"] = {
                "categories": summarize_tennis_categories(gr.get("categories_raw") or {}),
                "default_unique_tournaments": summarize_default_unique_tournaments(
                    gr.get("default_unique_tournaments_raw") or {}
                ),
                "priority_country": gr.get("priority_country"),
            }

    h2h_ok = (not bool(raw_h2h_d.get("_error"))) and bool(proc_h2h.get("ok"))
    team_streaks_ok = (not bool(raw_streaks_d.get("_error"))) and bool(proc_streaks.get("ok"))
    team_season_home_ok = (not bool(r_tsh.get("_error"))) and bool(proc_tsh.get("ok"))
    team_season_away_ok = (not bool(r_tsa.get("_error"))) and bool(proc_tsa.get("ok"))
    team_season_stats_ok = team_season_home_ok and team_season_away_ok

    odds_all_ok = not bool(raw_odds_all.get("_error")) if isinstance(raw_odds_all, dict) else False
    odds_featured_ok = not bool(raw_odds_featured.get("_error")) if isinstance(raw_odds_featured, dict) else False
    if sport_l == "tennis":
        t_odds = processed.get("tennis_odds") if isinstance(processed.get("tennis_odds"), dict) else {}
        if t_odds.get("has_any_odds"):
            odds_all_ok = True

    tr_home_ok = False
    tr_away_ok = False
    ts_tennis_ok = False
    tss_h_ok = tss_a_ok = False
    cat_ok = def_ut_ok = False
    if sport_l == "tennis":
        tr = processed.get("tennis_rankings") if isinstance(processed.get("tennis_rankings"), dict) else {}
        tr_home_ok = bool((tr.get("home") or {}).get("ok"))
        tr_away_ok = bool((tr.get("away") or {}).get("ok"))
        ts_tennis_ok = bool((processed.get("tennis_statistics") or {}).get("ok"))
        tss = processed.get("tennis_team_statistics_seasons") or {}
        tss_h_ok = bool((tss.get("home") or {}).get("ok"))
        tss_a_ok = bool((tss.get("away") or {}).get("ok"))
        reg = processed.get("tennis_registry") or {}
        cat_ok = bool((reg.get("categories") or {}).get("ok"))
        def_ut_ok = bool((reg.get("default_unique_tournaments") or {}).get("ok"))

    diagnostics = {
        "event_ok": not bool(raw_event.get("_error")) if isinstance(raw_event, dict) else False,
        "lineups_ok": not bool(raw_lineups.get("_error")) if isinstance(raw_lineups, dict) else False,
        "statistics_ok": not bool(raw_statistics.get("_error")) if isinstance(raw_statistics, dict) else False,
        "h2h_ok": h2h_ok,
        "team_streaks_ok": team_streaks_ok,
        "team_season_stats_ok": team_season_stats_ok,
        "team_season_stats_home_ok": team_season_home_ok,
        "team_season_stats_away_ok": team_season_away_ok,
        "odds_all_ok": odds_all_ok,
        "odds_featured_ok": odds_featured_ok,
        "tennis_rankings_home_ok": tr_home_ok,
        "tennis_rankings_away_ok": tr_away_ok,
        "tennis_event_statistics_ok": ts_tennis_ok,
        "tennis_team_statistics_seasons_home_ok": tss_h_ok,
        "tennis_team_statistics_seasons_away_ok": tss_a_ok,
        "tennis_categories_catalog_ok": cat_ok,
        "tennis_default_unique_tournaments_ok": def_ut_ok,
        # Solo entradas con fallo real (evita ruido en JSON)
        "fetch_errors": {
            k: v
            for k, v in (
                ("event", _fetch_failure_detail(raw_event if isinstance(raw_event, dict) else {})),
                ("lineups", _fetch_failure_detail(raw_lineups if isinstance(raw_lineups, dict) else {})),
                ("statistics", _fetch_failure_detail(raw_statistics if isinstance(raw_statistics, dict) else {})),
                ("h2h", _fetch_failure_detail(raw_h2h_d)),
                ("team_streaks", _fetch_failure_detail(raw_streaks_d)),
                ("team_season_home", _fetch_failure_detail(r_tsh)),
                ("team_season_away", _fetch_failure_detail(r_tsa)),
                ("odds_all", _fetch_failure_detail(raw_odds_all if isinstance(raw_odds_all, dict) else {})),
                ("odds_featured", _fetch_failure_detail(raw_odds_featured if isinstance(raw_odds_featured, dict) else {})),
                (
                    "team_rankings_home",
                    _fetch_failure_detail(raw_rank_home if isinstance(raw_rank_home, dict) else {}),
                ),
                (
                    "team_rankings_away",
                    _fetch_failure_detail(raw_rank_away if isinstance(raw_rank_away, dict) else {}),
                ),
                (
                    "team_statistics_seasons_home",
                    _fetch_failure_detail(raw_tss_home if isinstance(raw_tss_home, dict) else {}),
                ),
                (
                    "team_statistics_seasons_away",
                    _fetch_failure_detail(raw_tss_away if isinstance(raw_tss_away, dict) else {}),
                ),
                (
                    "tennis_categories_all",
                    _fetch_failure_detail(
                        (_TENNIS_GLOBAL_REGISTRY or {}).get("categories_raw")
                        if isinstance(_TENNIS_GLOBAL_REGISTRY, dict)
                        else {}
                    ),
                ),
                (
                    "tennis_default_unique_tournaments",
                    _fetch_failure_detail(
                        (_TENNIS_GLOBAL_REGISTRY or {}).get("default_unique_tournaments_raw")
                        if isinstance(_TENNIS_GLOBAL_REGISTRY, dict)
                        else {}
                    ),
                ),
            )
            if v
        },
    }

    return {
        "bundle_meta": {
            "generated_at_utc": _utc_now_iso(),
            "source": "sofascore",
            "event_id": event_id,
            "ingest_sport": sport_l,
        },
        "event_context": _safe_event_meta(raw_event if isinstance(raw_event, dict) else {}),
        "diagnostics": diagnostics,
        "processed": processed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline unificado por eventId (Copa Foxkids / juapi-tartara).")
    parser.add_argument("--event-id", "-e", type=int, required=True, help="ID del evento en SofaScore.")
    parser.add_argument(
        "--sport",
        default="football",
        help="Slug API SofaScore (football, tennis, …). Afecta diagnósticos/tennis_odds.",
    )
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON con indentación.")
    return parser.parse_args()


async def _cli_main(args: argparse.Namespace) -> None:
    bundle = await fetch_event_bundle(args.event_id, sport=args.sport)
    if args.pretty:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(bundle, ensure_ascii=False))


if __name__ == "__main__":
    cli_args = parse_args()
    asyncio.run(_cli_main(cli_args))

