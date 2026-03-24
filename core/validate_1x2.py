#!/usr/bin/env python3
"""
core/validate_1x2.py

Valida una selección 1X2 contra el marcador final de SofaScore.
Este módulo está pensado para ejecutarse en orquestación batch (p. ej. horas después del partido).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

from processors.validate_1x2_processor import process_validate_1x2


_FETCH_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}


def _resolve_playwright_chrome_executable() -> Optional[str]:
    """
    Resuelve el binario compatible con la arquitectura presente bajo PLAYWRIGHT_BROWSERS_PATH.
    Prioriza el Chromium completo (más estable) y si no, usa el chrome-headless-shell.
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


def _to_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, int):
        return x
    try:
        s = str(x).strip()
        if not s:
            return None
        return int(float(s.replace(",", ".")))
    except Exception:
        return None


def _extract_score(score_obj: Any) -> Optional[int]:
    if isinstance(score_obj, dict):
        for k in ("current", "value", "display", "total"):
            if k in score_obj:
                return _to_int(score_obj.get(k))
        return _to_int(score_obj.get("current"))
    return _to_int(score_obj)


async def _fetch_event(context, event_id: int) -> Dict[str, Any]:
    url = f"https://www.sofascore.com/api/v1/event/{event_id}"
    try:
        resp = await context.request.get(url, headers=_FETCH_HEADERS)
        if not resp.ok:
            return {"_error": True, "_status": resp.status, "_statusText": resp.status_text, "_url": url}
        data = await resp.json()
        return data if isinstance(data, dict) else {"_error": True, "_statusText": "json_not_object", "_url": url}
    except Exception as e:
        return {"_error": True, "_status": -1, "_statusText": str(e), "_url": url}


def _normalize_selection(sel: str) -> Optional[str]:
    s_raw = str(sel).strip()
    if not s_raw:
        return None
    s = s_raw.upper()
    if s in ("1", "X", "2"):
        return "1" if s == "1" else ("2" if s == "2" else "X")
    if s in ("HOME", "HOME_WIN", "H"):
        return "1"
    if s in ("AWAY", "AWAY_WIN", "A"):
        return "2"
    if s in ("DRAW", "D"):
        return "X"
    m = re.match(r"^([12xX])(\s|\(|$)", s_raw, flags=re.IGNORECASE)
    if m:
        ch = m.group(1).upper()
        return "X" if ch == "X" else ch
    return None


async def validate_1x2(event_id: int, selection: str) -> Dict[str, Any]:
    async with async_playwright() as p:
        executable_path = _resolve_playwright_chrome_executable()
        if executable_path:
            browser = await p.chromium.launch(headless=True, executable_path=executable_path)
        else:
            browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        raw = await _fetch_event(context, event_id)
        await browser.close()

    if isinstance(raw, dict) and isinstance(raw.get("event"), dict):
        raw = raw.get("event") or {}

    status = raw.get("status") or {}
    status_desc = str(status.get("description") or "").lower()
    status_type = str(status.get("type") or "").lower()
    status_code = status.get("code")

    is_finished = (
        ("finished" in status_desc)
        or ("ft" in status_desc)
        or (status_code == 100)
        or (status_type == "finished")
    )
    match_state = "finished" if is_finished else ("live" if "live" in status_desc else "not started")

    home_score = _extract_score(raw.get("homeScore"))
    away_score = _extract_score(raw.get("awayScore"))

    processed = process_validate_1x2(
        {
            "selection": _normalize_selection(selection),
            "match_state": match_state,
            "home_score": home_score,
            "away_score": away_score,
        }
    )
    return processed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida una selección 1X2 (win/loss/pending) contra el marcador final.")
    parser.add_argument("--event-id", "-e", type=int, required=True)
    parser.add_argument("--selection", "-s", type=str, required=True, help="1, X o 2 (home/draw/away).")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


async def _cli_main(args: argparse.Namespace) -> None:
    result = await validate_1x2(args.event_id, args.selection)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_cli_main(parse_args()))

