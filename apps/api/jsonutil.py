from __future__ import annotations

import json
from typing import Any


def parse_json_field(raw: str | None) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": raw[:500]}
