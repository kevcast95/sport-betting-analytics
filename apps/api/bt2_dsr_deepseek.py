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
from dataclasses import dataclass
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
    rc = msg.get("reasoning_content")
    if isinstance(rc, str) and rc.strip():
        return rc.strip()
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
        m = re.search(r"\{[\s\S]*\}\s*$", t)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None
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
    "Eres analista de apuestas deportivas (fútbol, solo pre-partido). "
    "Recibes un lote con varios eventos (`ds_input`): forma whitelist con "
    "`processed.odds_featured` (consensus y, si viene, `ingest_meta` de frescura de cuotas), "
    "bloques opcionales `h2h`, `statistics` (forma reciente codificada), `team_streaks`, `lineups` "
    "cuando `available: true`, y `event_context`. No conoces resultados del partido objetivo. "
    "Entre mercados presentes en `consensus`, elegí el que tenga **mejor soporte en los datos "
    "del propio lote** (histórico/forma/rachas/alineaciones resumidas y coherencia con las cuotas "
    "mostradas). **No** uses como regla principal “buscar la cuota más alta” ni maximizar payout; "
    "la lectura debe poder defenderse con lo enviado. Si varios mercados tienen soporte similar "
    "en los datos de ese evento, **no** elijas siempre 1X2 por costumbre: considerá O/U goles, BTTS "
    "o doble oportunidad cuando el input los respalde. **No inventes** estadísticas ni histórico: "
    "solo usa lo explícito en cada ítem. "
    "Respondé SOLO con JSON válido (sin markdown) según el esquema que pide el usuario."
)


def _user_prompt_batch(*, operating_day_key: str, batch: dict[str, Any]) -> str:
    return (
        f"Día operativo (referencia): {operating_day_key}.\n"
        "Tarea: con el lote `batch` (campo `ds_input`), una lectura por evento; compará eventos "
        "del mismo lote como en pipeline v1. Fundamentá la elección de mercado y lado usando "
        "**solo** `consensus` y los bloques `processed.*` con `available: true` de ese evento; "
        "si un bloque no está disponible, no lo cites como si existiera.\n\n"
        "Reglas de salida:\n"
        "- Devolvé SOLO un objeto JSON con esta forma:\n"
        "{\n"
        '  "picks_by_event": [\n'
        "    {\n"
        '      "event_id": <int>,\n'
        '      "motivo_sin_pick": "<string en español; vacío si hay picks>",\n'
        '      "picks": [\n'
        "        {\n"
        '          "market": "OU_GOALS_2_5"|"BTTS"|"FT_1X2",\n'
        '          "selection": "over_2_5"|"yes"|"home",\n'
        '          "odds": <number>,\n'
        '          "edge_pct": <number>,\n'
        '          "confianza": "Baja"|"Media"|"Media-Alta"|"Alta",\n'
        '          "razon": "<una frase en español>"\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "- Debe haber exactamente un elemento en picks_by_event por cada evento de ds_input "
        "(mismo event_id).\n"
        "- Máximo 2 picks por evento; si no hay valor, picks=[] y motivo_sin_pick obligatorio.\n"
        "- `market`: texto o código canónico (FT_1X2, OU_GOALS_2_5, BTTS, DOUBLE_CHANCE_1X, …).\n"
        "- `selection`: para FT_1X2 usá home|draw|away (o 1|X|2); O/U over_2_5|under_2_5; BTTS yes|no; "
        "doble oportunidad yes.\n"
        "- No inventes cuotas: el campo `odds` debe coincidir con consensus del evento.\n\n"
        "Datos del lote (JSON):\n"
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
        picks = row.get("picks")
        motivo = str(row.get("motivo_sin_pick") or "").strip()
        if not isinstance(picks, list):
            out[eid] = None
            continue
        if len(picks) == 0:
            narr = motivo or "Sin pick explícito para este evento."
            out[eid] = (narr[:4000], "low", "UNKNOWN", "unknown_side", None)
            continue
        pick = picks[0]
        if not isinstance(pick, dict):
            out[eid] = None
            continue
        market = str(pick.get("market") or "")
        selection = str(pick.get("selection") or "")
        mmc, msc = normalized_pick_to_canonical(market, selection)
        razon = str(pick.get("razon") or "").strip()
        conf = _confianza_to_label(str(pick.get("confianza") or ""))
        narr = razon or motivo or "Señal modelo."
        mod_o: Optional[float] = None
        try:
            if pick.get("odds") is not None:
                mod_o = float(pick.get("odds"))
        except (TypeError, ValueError):
            mod_o = None
        out[eid] = (narr[:4000], conf, mmc, msc, mod_o)
    return out


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
    if not ds_input_items:
        return {}

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
        try:
            raw = poster(url, headers, raw_body, float(timeout_sec))
            resp = json.loads(raw.decode("utf-8"))
            content = _extract_content_from_chat_response(resp)
            parsed = _parse_json_object(content)
            if not parsed:
                last_err = "parse_json"
                logger.warning(
                    "bt2_dsr_batch_bad_json batch_size=%s attempt=%s",
                    len(ds_input_items),
                    attempt,
                )
                continue
            return _parse_picks_by_event(parsed, expected_ids)
        except urllib.error.HTTPError as e:
            last_err = f"http_{e.code}"
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
            logger.warning(
                "bt2_dsr_batch_error err=%s batch_size=%s attempt=%s",
                last_err,
                len(ds_input_items),
                attempt,
            )

    logger.warning(
        "bt2_dsr_batch_degraded batch_size=%s last_err=%s",
        len(ds_input_items),
        last_err or "unknown",
    )
    return {eid: None for eid in expected_ids}

