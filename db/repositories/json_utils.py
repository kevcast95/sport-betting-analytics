import json
from typing import Any, Dict, Optional


def dumps_json_stable(payload: Any) -> str:
    """
    Serialización determinista (orden de claves + sin espacios).
    Útil para depuración y para que el JSON persista de forma estable.
    """
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def loads_json_safely(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if text is None:
        return None
    try:
        v = json.loads(text)
        if isinstance(v, dict):
            return v
    except Exception:
        pass
    return None

