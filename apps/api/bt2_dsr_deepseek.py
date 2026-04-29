"""
T-170 / D-06-019 — DeepSeek por **lotes v1-equivalentes** (`ds_input` + `picks_by_event`).

Una petición HTTP por lote (no por evento). Degradación por lote o por evento según parser.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urljoin

from apps.api.bt2_dsr_contract import (
    PIPELINE_VERSION_DEFAULT,
    assert_no_forbidden_ds_keys,
    validate_ds_batch_envelope,
)
from apps.api.bt2_market_canonical import normalized_pick_to_canonical

logger = logging.getLogger(__name__)

# Tests: parchear (url, headers, body, timeout) -> raw bytes UTF-8
_http_post: Callable[[str, dict[str, str], bytes, float], bytes] | None = None


def _default_http_post(url: str, headers: dict[str, str], body: bytes, timeout_sec: float) -> bytes:
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return resp.read()


def _extract_content_from_chat_response(resp: dict[str, Any]) -> str:
    choices = resp.get("choices") or []
    if not choices:
        raise ValueError("deepseek_no_choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for c in content:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                parts.append(c["text"])
        if parts:
            return "\n".join(parts).strip()
    raise ValueError("deepseek_no_content")


def _parse_json_object(text: str) -> Optional[dict[str, Any]]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _confianza_to_label(conf: str) -> str:
    c = conf.strip().lower()
    if "alta" in c and "media" not in c:
        return "high"
    if "media" in c:
        return "medium"
    return "low"


@dataclass(frozen=True)
class DsrBatchCandidate:
    event_id: int
    tournament: str
    home_team: str
    away_team: str
    odds_home: float | None
    odds_draw: float | None
    odds_away: float | None
    odds_over25: float | None
    odds_under25: float | None


_SYSTEM_BATCH = (
    "Responde SOLO con un objeto JSON válido. "
    "No escribas texto libre, no markdown, no prefacios, no explicaciones. "
    "Devuelve exactamente 1 objeto por cada event_id de ds_input en picks_by_event. "
    "Campos obligatorios por evento: event_id, market_canonical, selection_canonical, "
    "selected_team, no_pick_reason. "
    "Mercado permitido: FT_1X2 o UNKNOWN. "
    "Selección permitida: home, draw, away o unknown_side. "
    "Si no hay pick: market_canonical=UNKNOWN, selection_canonical=unknown_side y no_pick_reason no vacío. "
    "Política de abstención: con FT_1X2 disponible, por defecto debes elegir home/draw/away. "
    "Usa UNKNOWN solo en abstención legítima (datos críticos faltantes o contradicción fuerte que impide preferencia razonable). "
    "No uses UNKNOWN por duda normal o por falta de certeza perfecta (eso es abstención excesiva). "
    "No uses datos fuera de ds_input."
)


def _user_prompt_batch(*, operating_day_key: str, batch: dict[str, Any]) -> str:
    return (
        f"operating_day_key={operating_day_key}\n"
        "OUTPUT: SOLO JSON.\n"
        "SCHEMA OBLIGATORIO:\n"
        "{\n"
        '  "picks_by_event": [\n'
        "    {\n"
        '      "event_id": <int>,\n'
        '      "market_canonical": "FT_1X2" | "UNKNOWN",\n'
        '      "selection_canonical": "home" | "draw" | "away" | "unknown_side",\n'
        '      "selected_team": "<string o vacío>",\n'
        '      "no_pick_reason": "<vacío si hay pick; obligatorio si UNKNOWN>"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "REGLAS:\n"
        "- Debe haber exactamente 1 objeto por cada event_id de ds_input.\n"
        "- Sin texto fuera del JSON.\n"
        "- Solo mercado objetivo FT_1X2 (o UNKNOWN sin pick).\n"
        "- Política de abstención explícita:\n"
        "  * Abstención legítima: falta de datos críticos (p.ej. market coverage insuficiente) o contradicción severa que impide preferencia razonable.\n"
        "  * Abstención excesiva: incertidumbre normal, señal débil pero direccional, o falta de edge perfecto.\n"
        "- Si FT_1X2 está disponible y no hay abstención legítima, DEBES elegir home/draw/away.\n"
        "- UNKNOWN/unknown_side solo con no_pick_reason concreto y verificable en el lote.\n"
        "- No devuelvas claves extra.\n\n"
        "BATCH:\n"
        f"{json.dumps(batch, ensure_ascii=False)}\n"
    )


def _parse_picks_by_event(
    parsed: dict[str, Any],
    expected_ids: list[int],
) -> dict[int, Optional[tuple[str, str, str, str, Optional[float]]]]:
    """
    Por event_id: (narrative_es, confidence_label, market_canonical, selection_canonical, model_odds) o None.
    None = degradar ese evento a rules_fallback.
    """
    raw = parsed.get("picks_by_event")
    if not isinstance(raw, list):
        return {eid: None for eid in expected_ids}  # type: ignore[return-value]

    by_eid: dict[int, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            eid = int(row.get("event_id"))
        except (TypeError, ValueError):
            continue
        by_eid[eid] = row

    out: dict[int, Optional[tuple[str, str, str, str, Optional[float]]]] = {}
    for eid in expected_ids:
        row = by_eid.get(eid)
        if not row:
            out[eid] = None
            continue
        motivo = str(
            row.get("no_pick_reason")
            or row.get("motivo_sin_pick")
            or row.get("no_pick")
            or ""
        ).strip()
        # v2 preferido: campos canónicos por evento.
        mmc_raw = str(
            row.get("market_canonical")
            or row.get("market")
            or row.get("marketCode")
            or ""
        ).strip()
        msc_raw = str(
            row.get("selection_canonical")
            or row.get("selection")
            or row.get("side")
            or row.get("pick")
            or ""
        ).strip()
        if not mmc_raw and not msc_raw:
            out[eid] = None
            continue
        mmc, msc = normalized_pick_to_canonical(mmc_raw, msc_raw)
        selected_team = str(row.get("selected_team") or row.get("team") or "").strip()
        # Marcadores explícitos para autopsia/normalización mínima en carril shadow.
        narr = (
            f"[selected_team]{selected_team}[/selected_team]"
            f"[no_pick_reason]{motivo}[/no_pick_reason]"
        )
        conf = "low"
        mod_o: Optional[float] = None
        try:
            if row.get("odds") is not None:
                mod_o = float(row.get("odds"))
        except (TypeError, ValueError):
            mod_o = None
        out[eid] = (narr[:4000], conf, mmc, msc, mod_o)
    return out


@dataclass
class DeepseekBatchTrace:
    """Metadatos de una llamada batch a DeepSeek (DSR API)."""

    response_id: Optional[str] = None
    model: Optional[str] = None
    usage: dict[str, Any] = field(default_factory=dict)
    last_error: str = ""
    parse_success: bool = False
    attempts_used: int = 0
    raw_content_excerpt: str = ""
    raw_content_full: str = ""


def deepseek_suggest_batch_with_trace(
    ds_input_items: list[dict[str, Any]],
    *,
    operating_day_key: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout_sec: int,
    max_retries: int,
) -> tuple[dict[int, Optional[tuple[str, str, str, str, Optional[float]]]], DeepseekBatchTrace]:
    """
    Igual que `deepseek_suggest_batch`, pero devuelve traza (id respuesta, usage, errores).
    """
    trace = DeepseekBatchTrace(model=model)
    if not ds_input_items:
        return {}, trace

    expected_ids = [int(x["event_id"]) for x in ds_input_items]
    batch_obj: dict[str, Any] = {
        "operating_day_key": operating_day_key,
        "pipeline_version": PIPELINE_VERSION_DEFAULT,
        "sport": "football",
        "ds_input": ds_input_items,
    }
    validate_ds_batch_envelope(batch_obj)
    assert_no_forbidden_ds_keys(batch_obj)

    user_prompt = _user_prompt_batch(operating_day_key=operating_day_key, batch=batch_obj)
    max_tokens = min(8000, 900 + 220 * len(ds_input_items))

    url = urljoin(base_url.rstrip("/") + "/", "chat/completions")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_BATCH},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    raw_body = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    poster = _http_post or _default_http_post
    attempts = max(0, int(max_retries)) + 1
    last_err = ""

    for attempt in range(attempts):
        trace.attempts_used = attempt + 1
        try:
            raw = poster(url, headers, raw_body, float(timeout_sec))
            resp = json.loads(raw.decode("utf-8"))
            if isinstance(resp.get("id"), str):
                trace.response_id = resp["id"]
            mu = resp.get("usage")
            if isinstance(mu, dict):
                trace.usage = mu
            if isinstance(resp.get("model"), str):
                trace.model = resp["model"]
            content = _extract_content_from_chat_response(resp)
            trace.raw_content_excerpt = content[:1200]
            parsed = _parse_json_object(content)
            if not parsed:
                last_err = "parse_json"
                trace.last_error = last_err
                logger.warning(
                    "bt2_dsr_batch_bad_json batch_size=%s attempt=%s",
                    len(ds_input_items),
                    attempt,
                )
                continue
            trace.parse_success = True
            trace.last_error = ""
            out = _parse_picks_by_event(parsed, expected_ids)
            return out, trace
        except urllib.error.HTTPError as e:
            last_err = f"http_{e.code}"
            trace.last_error = last_err
            logger.warning(
                "bt2_dsr_batch_http code=%s batch_size=%s attempt=%s",
                getattr(e, "code", "?"),
                len(ds_input_items),
                attempt,
            )
            if e.code and int(e.code) < 500:
                break
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as e:
            last_err = type(e).__name__
            trace.last_error = last_err
            logger.warning(
                "bt2_dsr_batch_error err=%s batch_size=%s attempt=%s",
                last_err,
                len(ds_input_items),
                attempt,
            )

    degraded = {eid: None for eid in expected_ids}
    trace.last_error = last_err or trace.last_error or "unknown"
    logger.warning(
        "bt2_dsr_batch_degraded batch_size=%s last_err=%s",
        len(ds_input_items),
        trace.last_error,
    )
    return degraded, trace


def deepseek_suggest_batch(
    ds_input_items: list[dict[str, Any]],
    *,
    operating_day_key: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout_sec: int,
    max_retries: int,
) -> dict[int, Optional[tuple[str, str, str, str, Optional[float]]]]:
    """
    Una llamada HTTP para todo el lote. `ds_input_items` ya validados (whitelist T-171).
    Retorna mapa event_id → tupla (incl. odds declaradas modelo) o None (degradar a reglas).
    """
    out, _trace = deepseek_suggest_batch_with_trace(
        ds_input_items,
        operating_day_key=operating_day_key,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
    )
    return out

