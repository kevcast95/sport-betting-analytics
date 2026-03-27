"""HTTP mínimo contra la API pública de SofaScore (mismos headers que ingesta diaria)."""

from __future__ import annotations

import json
import urllib.request
from typing import Any


def sofascore_request_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "User-Agent": "Mozilla/5.0",
    }


def sofascore_get_json(url: str, *, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers=sofascore_request_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
