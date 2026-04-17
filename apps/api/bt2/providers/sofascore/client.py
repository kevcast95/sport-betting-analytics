"""Cliente HTTP SofaScore con throttle (sync)."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from apps.api.bt2.providers.sofascore.http_headers import sfs_request_headers

DEFAULT_BASE = "https://www.sofascore.com/api/v1"


class SfsHttpClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE,
        max_rps: float = 4.0,
        timeout_sec: int = 25,
    ) -> None:
        self._base = (base_url or DEFAULT_BASE).rstrip("/")
        self._max_rps = max(0.1, float(max_rps))
        self._timeout = int(timeout_sec)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
            self._next_allowed = time.monotonic() + (1.0 / self._max_rps)

    def get_json(self, path: str) -> dict[str, Any]:
        """path ej. '/event/123/odds/1/featured' o URL absoluta."""
        self._throttle()
        url = path if path.startswith("http") else f"{self._base}{path}"
        req = urllib.request.Request(url, headers=sfs_request_headers())
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                return data if isinstance(data, dict) else {"_error": True, "_body": data}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:2000]
            return {"_error": True, "_http_status": e.code, "_http_body": body, "_url": url}
        except Exception as e:
            return {"_error": True, "_exception": str(e), "_url": url}

    def fetch_odds_featured(self, sofascore_event_id: int) -> dict[str, Any]:
        return self.get_json(f"/event/{int(sofascore_event_id)}/odds/1/featured")

    def fetch_odds_all(self, sofascore_event_id: int) -> dict[str, Any]:
        return self.get_json(f"/event/{int(sofascore_event_id)}/odds/1/all")

    def fetch_scheduled_football_day(self, yyyymmdd: str) -> dict[str, Any]:
        return self.get_json(f"/sport/football/scheduled-events/{yyyymmdd}")


def sfs_client_from_settings() -> SfsHttpClient:
    from apps.api.bt2_settings import bt2_settings

    return SfsHttpClient(
        base_url=getattr(bt2_settings, "bt2_sfs_base_url", DEFAULT_BASE) or DEFAULT_BASE,
        max_rps=float(getattr(bt2_settings, "bt2_sfs_http_max_rps", 4.0) or 4.0),
        timeout_sec=int(getattr(bt2_settings, "bt2_sfs_http_timeout_sec", 25) or 25),
    )
