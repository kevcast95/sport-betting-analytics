"""
Cliente HTTP DeepSeek para prompt **shadow-native v6** — aislado de `deepseek_suggest_batch*` compartido.

Misma forma de retorno que `bt2_dsr_deepseek.deepseek_suggest_batch_with_trace` para reusar post-proceso.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Optional
from urllib.parse import urljoin

from apps.api.bt2_dsr_contract import PIPELINE_VERSION_DEFAULT, assert_no_forbidden_ds_keys, validate_ds_batch_envelope
from apps.api.bt2_dsr_deepseek import (
    DeepseekBatchTrace,
    _default_http_post,
    _extract_content_from_chat_response,
    _http_post,
    _parse_json_object,
)
from apps.api.bt2_market_canonical import normalized_pick_to_canonical
from apps.api.bt2_dsr_shadow_native_prompt_v6 import (
    DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
    SYSTEM_PROMPT_SHADOW_NATIVE_V6,
    build_user_prompt_shadow_native_v6,
)

logger = logging.getLogger(__name__)

_ALLOWED_ROW_KEYS = frozenset(
    {
        "event_id",
        "market_canonical",
        "selection_canonical",
        "selected_team",
        "confidence_label",
        "rationale_short_es",
        "no_pick_reason",
    }
)


def _norm_confidence_label(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("high", "medium", "low"):
        return s
    if "alta" in s and "media" not in s:
        return "high"
    if "media" in s:
        return "medium"
    if any(x in s for x in ("baja", "bajo", "low")):
        return "low"
    return "low"


def _parse_picks_by_event_v6(
    parsed: dict[str, Any],
    expected_ids: list[int],
) -> dict[int, Optional[tuple[str, str, str, str, Optional[float]]]]:
    """
    event_id → (narrative_es, confidence_label, market_canonical, selection_canonical, model_odds).

    `narrative_es` usa `rationale_short_es` para coherencia con `postprocess_dsr_pick`.
    `model_odds` siempre None (v6 no pide cuota inventada al modelo).
    """
    raw = parsed.get("picks_by_event")
    if not isinstance(raw, list):
        return {eid: None for eid in expected_ids}

    by_eid: dict[int, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        extras = set(row.keys()) - _ALLOWED_ROW_KEYS
        if extras:
            logger.info("bt2_dsr_v6_extra_keys dropped=%s", sorted(extras))
        row_slim = {k: row[k] for k in _ALLOWED_ROW_KEYS if k in row}
        try:
            eid = int(row_slim.get("event_id"))
        except (TypeError, ValueError):
            continue
        by_eid[eid] = row_slim

    out: dict[int, Optional[tuple[str, str, str, str, Optional[float]]]] = {}
    for eid in expected_ids:
        row = by_eid.get(eid)
        if not row:
            out[eid] = None
            continue
        motivo = str(row.get("no_pick_reason") or "").strip()
        rationale = str(row.get("rationale_short_es") or "").strip()
        mmc_raw = str(row.get("market_canonical") or "").strip()
        msc_raw = str(row.get("selection_canonical") or "").strip()
        selected_team = str(row.get("selected_team") or "").strip()
        conf = _norm_confidence_label(row.get("confidence_label"))

        if not mmc_raw and not msc_raw:
            out[eid] = None
            continue

        mmc, msc = normalized_pick_to_canonical(mmc_raw, msc_raw)

        narr = (
            f"[rationale_short_es]{rationale}[/rationale_short_es]"
            f"[selected_team]{selected_team}[/selected_team]"
            f"[no_pick_reason]{motivo}[/no_pick_reason]"
        )
        out[eid] = (narr[:4000], conf, mmc, msc, None)

    return out


def deepseek_suggest_batch_shadow_native_v6_with_trace(
    ds_input_items: list[dict[str, Any]],
    *,
    operating_day_key: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout_sec: int,
    max_retries: int,
) -> tuple[dict[int, Optional[tuple[str, str, str, str, Optional[float]]]], DeepseekBatchTrace]:
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

    user_prompt = build_user_prompt_shadow_native_v6(operating_day_key=operating_day_key, batch=batch_obj)
    # v6 añade rationale + confidence por evento; un techo bajo trunca el JSON (json inválido).
    max_tokens = min(16384, 1400 + 420 * len(ds_input_items))

    url = urljoin(base_url.rstrip("/") + "/", "chat/completions")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_SHADOW_NATIVE_V6},
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

    poster: Callable[[str, dict[str, str], bytes, float], bytes] = _http_post or _default_http_post
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
            trace.raw_content_full = content
            parsed = _parse_json_object(content)
            if not parsed:
                last_err = "parse_json"
                trace.last_error = last_err
                logger.warning(
                    "bt2_dsr_v6_batch_bad_json batch_size=%s attempt=%s",
                    len(ds_input_items),
                    attempt,
                )
                continue
            trace.parse_success = True
            trace.last_error = ""
            out = _parse_picks_by_event_v6(parsed, expected_ids)
            return out, trace
        except urllib.error.HTTPError as e:
            last_err = f"http_{e.code}"
            trace.last_error = last_err
            logger.warning(
                "bt2_dsr_v6_batch_http code=%s batch_size=%s attempt=%s",
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
                "bt2_dsr_v6_batch_error err=%s batch_size=%s attempt=%s",
                last_err,
                len(ds_input_items),
                attempt,
            )

    degraded = {eid: None for eid in expected_ids}
    trace.last_error = last_err or trace.last_error or "unknown"
    logger.warning(
        "bt2_dsr_v6_batch_degraded batch_size=%s last_err=%s",
        len(ds_input_items),
        trace.last_error,
    )
    return degraded, trace


def narrative_extract_rationale_v6(narrative: str) -> str:
    """Extrae rationale para CSV / artefactos desde el envelope interno."""
    m = re.search(r"\[rationale_short_es\](.*?)\[/rationale_short_es\]", narrative or "", re.DOTALL)
    return (m.group(1) if m else "").strip()


# Re-export versión para imports únicos desde scripts
__all__ = [
    "DSR_PROMPT_VERSION_SHADOW_NATIVE_V6",
    "deepseek_suggest_batch_shadow_native_v6_with_trace",
    "narrative_extract_rationale_v6",
]
