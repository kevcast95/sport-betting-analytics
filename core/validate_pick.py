#!/usr/bin/env python3
"""
Valida un pick (cualquier mercado soportado) contra GET /event/{id} de SofaScore.
Reutiliza el fetch con Playwright de validate_1x2 y aplica processors.pick_settlement.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

from processors.pick_settlement import settle_pick

from core.validate_1x2 import (  # noqa: WPS433 (reuso intencional)
    _extract_score,
    _fetch_event,
    _resolve_playwright_chrome_executable,
)


def _finished_and_state(status: Dict[str, Any]) -> str:
    status_desc = str(status.get("description") or "").lower()
    status_type = str(status.get("type") or "").lower()
    status_code = status.get("code")
    is_finished = (
        ("finished" in status_desc)
        or ("ft" in status_desc)
        or (status_code == 100)
        or (status_type == "finished")
    )
    if is_finished:
        return "finished"
    if "live" in status_desc or status_code in (0, 31, 32, 33, 34, 61, 71):
        return "live"
    return "not started"


def parse_sofascore_event_for_settlement(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza el JSON de evento (envuelto o no) a snapshot para pick_settlement."""
    event = raw_event.get("event") if isinstance(raw_event.get("event"), dict) else raw_event
    if not isinstance(event, dict):
        return {"_error": True, "_statusText": "no_event_object"}

    status = event.get("status") or {}
    match_state = _finished_and_state(status if isinstance(status, dict) else {})

    hs_raw = event.get("homeScore")
    aw_raw = event.get("awayScore")
    home_score = _extract_score(hs_raw)
    away_score = _extract_score(aw_raw)

    p1h: Optional[int] = None
    p1a: Optional[int] = None
    if isinstance(hs_raw, dict) and isinstance(aw_raw, dict):
        for key in ("period1", "p1", "first"):
            if key in hs_raw and key in aw_raw:
                p1h = _extract_score(hs_raw.get(key))
                p1a = _extract_score(aw_raw.get(key))
                break

    return {
        "match_state": match_state,
        "home_score": home_score,
        "away_score": away_score,
        "period1_home": p1h,
        "period1_away": p1a,
    }


async def validate_pick(
    event_id: int,
    market: str,
    selection: str,
    picked_value: Optional[float] = None,
) -> Dict[str, Any]:
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
        raw = await _fetch_event(context, event_id)
        await browser.close()

    if isinstance(raw, dict) and raw.get("_error"):
        settled = settle_pick(
            market=market,
            selection=selection,
            picked_value=picked_value,
            snapshot=raw,
        )
        return {
            "outcome": settled["outcome"],
            "result_1x2": settled.get("result_1x2"),
            "score": settled.get("score") or {"home": None, "away": None},
            "settlement": settled,
            "fetch_error": raw,
        }

    snap = parse_sofascore_event_for_settlement(raw if isinstance(raw, dict) else {})
    settled = settle_pick(
        market=market,
        selection=selection,
        picked_value=picked_value,
        snapshot=snap,
    )

    out: Dict[str, Any] = {
        "outcome": settled["outcome"],
        "result_1x2": settled.get("result_1x2"),
        "score": settled.get("score") or {"home": snap.get("home_score"), "away": snap.get("away_score")},
        "settlement": settled,
        "snapshot": snap,
    }
    return out
