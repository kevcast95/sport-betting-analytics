"""Extracción de event_id desde respuestas tipo scheduled-events (fútbol, tenis legacy, etc.)."""

from __future__ import annotations

from typing import Any, List


def extract_event_ids_from_scheduled_payload(payload: Any) -> List[int]:
    if isinstance(payload, list):
        ids: List[int] = []
        for it in payload:
            if isinstance(it, dict) and "id" in it:
                try:
                    ids.append(int(it["id"]))
                except (TypeError, ValueError):
                    continue
            elif isinstance(it, int):
                ids.append(it)
        return ids

    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            return []
        for key in ("events", "scheduledEvents", "scheduled_events"):
            if key in payload and isinstance(payload[key], list):
                return extract_event_ids_from_scheduled_payload(payload[key])
        if "id" in payload:
            try:
                return [int(payload["id"])]
            except (TypeError, ValueError):
                return []
    return []
