"""
Degradación de `include` ante 403 de SportMonks (plan / trial).

Los bloques DSR ya tratan los nodos del JSON como opcionales. Aquí se aplica el
mismo criterio a la **petición**: se intenta la lista «deseada» y, si SM
devuelve 403 por un include no contratado, se quita ese segmento (o se cae al
núcleo) y se reintenta — la ingesta no debe fallar en bloque por extras.
"""

from __future__ import annotations

import json
import re
from typing import Any


def bt2_sm_normalize_include_string(include_str: str) -> str:
    parts = [p.strip() for p in (include_str or "").split(";") if p.strip()]
    return ";".join(parts)


def bt2_sm_strip_include_root(include_str: str, root: str) -> str:
    root = (root or "").strip()
    if not root:
        return include_str
    parts = [p.strip() for p in include_str.split(";") if p.strip()]
    prefix = root + "."
    filtered = [p for p in parts if p != root and not p.startswith(prefix)]
    return ";".join(filtered)


def bt2_sm_parse_forbidden_include_from_sm_403(body: Any) -> str | None:
    text = ""
    if isinstance(body, dict):
        for k in ("message", "error", "detail"):
            v = body.get(k)
            if isinstance(v, str) and v.strip():
                text = v
                break
        if not text:
            try:
                text = json.dumps(body)
            except (TypeError, ValueError):
                text = str(body)
    else:
        text = str(body)
    m = re.search(r"access to the ['\"]([^'\"]+)['\"] include", text, re.I)
    if m:
        return m.group(1).strip() or None
    m2 = re.search(r"include ['\"]([^'\"]+)['\"]", text, re.I)
    if m2:
        return m2.group(1).strip() or None
    return None


def bt2_sm_next_include_on_forbidden(
    current_include: str,
    *,
    core: str,
    response_body: Any,
) -> str | None:
    """
    Siguiente valor de `include` a probar tras un 403.

    - Si ya estamos en el núcleo normalizado → None (no hay más degradación).
    - Si el cuerpo indica un include prohibido y está en la cadena → cadena sin ese
      segmento (y sin anidados `root.*`).
    - Si no se puede parsear o el nombre no aparece → núcleo.
    """
    cur_n = bt2_sm_normalize_include_string(current_include)
    core_n = bt2_sm_normalize_include_string(core)
    if cur_n == core_n:
        return None
    bad = bt2_sm_parse_forbidden_include_from_sm_403(response_body)
    if bad:
        stripped = bt2_sm_normalize_include_string(bt2_sm_strip_include_root(current_include, bad))
        if stripped and stripped != cur_n:
            return stripped
    return core_n
