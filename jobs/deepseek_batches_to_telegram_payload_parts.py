#!/usr/bin/env python3
"""
deepseek_batches_to_telegram_payload_parts.py

Genera parciales `telegram_payload` (formato que consume `jobs/render_telegram_payload.py`)
llamando a DeepSeek directamente desde Python.

Flujo esperado:
  1) `split_ds_batches.py` genera lotes de `ds_input` en `out/batches/..._batchNNofMM.json`
  2) Este job llama DeepSeek por cada lote y escribe:
       out/payload_{DATE}_{EXEC_ID}_part{XX}.json
  3) `merge_telegram_payload_parts.py` une esas partes y luego `render_telegram_payload.py`

No persiste picks en DB y no envía Telegram (eso es otro job).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.scraped_odds_anchor import (  # noqa: E402
    confianza_from_edge,
    recompute_edge_pct_at_new_odds,
    scraped_decimal_odds_for_pick,
)
from core.tennis_deepseek_contract import (  # noqa: E402
    TENNIS_SYSTEM_PROMPT,
    build_tennis_user_prompt_instructions,
    infer_sport_from_batch,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DeepSeek batch analysis -> telegram_payload parts")
    p.add_argument("--input-glob", required=True, help="Glob de batches; ej. out/batches/candidates_2026-03-22_exec_08h_batch*.json")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (para header/date del payload)")
    p.add_argument("--exec-id", required=True, help="exec_08h o exec_16h (solo para naming de salida)")
    p.add_argument("--title", default="Copa Foxkids", help="header.title del payload")
    p.add_argument("--model", default="deepseek-reasoner", help="deepseek-chat o deepseek-reasoner")
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--max-tokens", type=int, default=1200)
    p.add_argument("--timeout-sec", type=int, default=180)
    p.add_argument("--max-retries", type=int, default=1)
    p.add_argument("--base-url", default="https://api.deepseek.com", help="DeepSeek base_url (OpenAI-compatible)")
    p.add_argument("--api-key-env", default="DEEPSEEK_API_KEY", help="Env var con la API key")
    p.add_argument("--output-dir", default="out", help="Directorio de salida (default: out)")
    p.add_argument(
        "--chat-fallback-model",
        default=os.environ.get("DS_CHAT_MODEL", "deepseek-chat"),
        help="Modelo chat para convertir reasoning->JSON si reasoner devuelve content vacío.",
    )
    p.add_argument(
        "--disable-response-format",
        action="store_true",
        help="Desactiva response_format json_object (por compatibilidad).",
    )
    return p.parse_args()


def _local_time_short_from_schedule_display(schedule_display: Dict[str, Any]) -> str:
    # schedule_display.local_iso = "YYYY-MM-DD HH:MM ZZZ"
    local_iso = schedule_display.get("local_iso") or ""
    parts = local_iso.split()
    if len(parts) >= 2:
        return parts[1][:5]  # "HH:MM"
    return ""


def _label_from_event_context(ec: Dict[str, Any]) -> str:
    home = ec.get("home_team") or "?"
    away = ec.get("away_team") or "?"
    return f"{home} vs {away}"


def _league_from_event_context(ec: Dict[str, Any]) -> str:
    return ec.get("tournament") or ""


def _selection_display(market: str, selection: str, ec: Dict[str, Any]) -> str:
    # Render espera selección textual (incluyendo paréntesis para 1X2)
    home = ec.get("home_team") or "Home"
    away = ec.get("away_team") or "Away"
    mk = str(market)
    sel = str(selection)
    if mk in ("Match winner", "Winner", "To win match"):
        if sel == "1":
            return f"1 ({home})"
        if sel == "2":
            return f"2 ({away})"
        return sel
    if mk == "1X2":
        if sel == "1":
            return f"1 ({home})"
        if sel == "X":
            return "X (Empate)"
        if sel == "2":
            return f"2 ({away})"
        return sel
    return sel


def _build_system_prompt(*, sport: str) -> str:
    if sport == "tennis":
        return TENNIS_SYSTEM_PROMPT
    return (
        "Eres un analista de fútbol para apuestas. "
        "El campo `razon` (y cualquier explicación legible) debe estar en español. "
        "Debes producir SOLO JSON válido (sin markdown, sin texto adicional). "
        "El JSON debe seguir el esquema pedido por el usuario. "
        "No inventes cuotas: usa las odds desde el campo `processed` del evento."
    )


def _build_user_prompt(batch: Dict[str, Any], *, date_str: str, sport: str) -> str:
    if sport == "tennis":
        return (
            build_tennis_user_prompt_instructions(date_str=date_str)
            + f"{json.dumps(batch, ensure_ascii=False)}\n"
        )
    return (
        f"Fecha de referencia: {date_str}.\n"
        "Tarea: con el lote `batch` (campo ds_input), elige picks para cada evento.\n\n"
        "Reglas de salida:\n"
        "- Devuelve SOLO un objeto JSON con esta forma:\n"
        "{\n"
        '  "picks_by_event": [\n'
        "    {\n"
        '      "event_id": 123,\n'
        '      "motivo_sin_pick": string,\n'
        '      "picks": [\n'
        "        {\n"
        '          "market": "1X2"|"Over/Under 2.5"|"BTTS"|"Double Chance",\n'
        '          "selection": "1"|"X"|"2"|"Over 2.5"|"Under 2.5"|"Yes"|"No"|"1X"|"X2"|"12",\n'
        '          "odds": number,\n'
        '          "edge_pct": number,\n'
        '          "confianza": "Baja"|"Media"|"Media-Alta"|"Alta",\n'
        '          "razon": string\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "- Debe haber exactamente un elemento en picks_by_event por cada evento del array ds_input del lote (mismo event_id).\n"
        "- motivo_sin_pick: obligatorio en español. Si picks tiene 1–2 elementos, usa \"\" (vacío). "
        "Si picks=[], explica en 1–2 frases por qué no hay valor (datos, cuotas, incertidumbre, etc.).\n"
        "- Para 1X2: usa selection exactamente '1','X','2' (el runner convertirá a '1 (HomeTeam)' etc.).\n"
        "- Máximo 2 picks por evento. Si no hay odds relevantes, picks=[] y motivo_sin_pick detallado.\n"
        "- Cálculo de EDGE:\n"
        "  p_imp_pct = round(100 / odds, 2)\n"
        "  elige p_real_pct (0-100) de forma razonada (probabilidad subjetiva en %)\n"
        "  edge_pct = round(p_real_pct - p_imp_pct, 2)\n"
        "- Confianza basada en edge_pct:\n"
        "  edge_pct >= 5 => Alta\n"
        "  edge_pct >= 3 => Media-Alta\n"
        "  edge_pct >= 1.5 => Media\n"
        "  else => Baja\n"
        "- 'razon' debe ser 1 frase en español basada en lineups/h2h/streaks y/o odds trend (Tier A vs Tier B).\n\n"
        "Datos del lote (JSON):\n"
        f"{json.dumps(batch, ensure_ascii=False)}\n"
    )


def _call_deepseek_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
    disable_response_format: bool,
) -> Dict[str, Any]:
    # OpenAI-compatible endpoint.
    url = urljoin(base_url.rstrip("/") + "/", "chat/completions")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    # DeepSeek supports OpenAI-compatible response_format; opcional por compatibilidad.
    if not disable_response_format:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _extract_message_content(resp: Dict[str, Any]) -> Tuple[str, str]:
    # OpenAI chat format: choices[0].message.content
    choices = resp.get("choices") or []
    if not choices:
        raise ValueError("DeepSeek response sin choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        rc = msg.get("reasoning_content")
        return content, rc if isinstance(rc, str) else ""
    # Compat: algunas APIs devuelven lista de partes [{type,text}, ...]
    if isinstance(content, list):
        parts: List[str] = []
        for c in content:
            if isinstance(c, dict):
                t = c.get("text")
                if isinstance(t, str):
                    parts.append(t)
        if parts:
            rc = msg.get("reasoning_content")
            return "\n".join(parts), rc if isinstance(rc, str) else ""
    # fallback: reasoning_content
    rc = msg.get("reasoning_content")
    if isinstance(rc, str) and rc.strip():
        return "", rc
    raise ValueError("DeepSeek response sin contenido textual parseable")


def _force_json_from_reasoning(
    *,
    base_url: str,
    api_key: str,
    chat_model: str,
    reasoning_text: str,
    timeout_sec: int,
) -> str:
    prompt = (
        "Convierte el siguiente razonamiento en SOLO un objeto JSON válido con la forma "
        "{\"picks_by_event\":[{\"event_id\":123,\"motivo_sin_pick\":\"\","
        "\"picks\":[{\"market\":\"...\",\"selection\":\"...\","
        "\"odds\":1.23,\"edge_pct\":2.34,\"confianza\":\"Media\",\"razon\":\"...\"}]}]}. "
        "motivo_sin_pick debe ser \"\" si hay picks; si picks=[], una frase breve en español. "
        "Sin markdown, sin explicaciones.\n\nRazonamiento:\n"
        + reasoning_text
    )
    resp = _call_deepseek_chat(
        base_url=base_url,
        api_key=api_key,
        model=chat_model,
        system_prompt="Devuelve JSON estricto únicamente.",
        user_prompt=prompt,
        temperature=0.0,
        max_tokens=900,
        timeout_sec=timeout_sec,
        disable_response_format=False,
    )
    content, _ = _extract_message_content(resp)
    return content


def _extract_json_object(raw: str) -> str:
    s = raw.strip()
    # Caso común: bloque ```json ... ```
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1)
    # Caso: texto alrededor; tomar desde primer '{' hasta último '}'
    i = s.find("{")
    j = s.rfind("}")
    if i != -1 and j != -1 and j > i:
        return s[i : j + 1]
    return s


def _parse_model_output(content: str) -> Dict[str, Any]:
    payload = _extract_json_object(content)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        snippet = content[:500].replace("\n", "\\n")
        raise ValueError(f"Salida no es JSON válido: {e}; snippet={snippet}") from e
    if not isinstance(data, dict):
        raise ValueError("Salida JSON no es objeto")
    if "picks_by_event" not in data:
        raise ValueError("JSON no contiene 'picks_by_event'")
    if not isinstance(data["picks_by_event"], list):
        raise ValueError("'picks_by_event' no es array")
    return data


def _build_payload_from_batch(batch: Dict[str, Any], model_out: Dict[str, Any], *, date_str: str, exec_id: str, title: str) -> Dict[str, Any]:
    ds_input: List[Dict[str, Any]] = list(batch.get("ds_input") or [])
    daily_run_id = batch.get("daily_run_id")
    sport = infer_sport_from_batch(batch)
    tennis_require_scraped = os.environ.get(
        "ALTEA_TENNIS_REQUIRE_SCRAPED_ODDS", "1"
    ).lower() not in ("0", "false", "no")
    allowed_tennis_markets = {
        x.strip().lower()
        for x in os.environ.get(
            "ALTEA_TENNIS_ALLOWED_MARKETS",
            "Match winner,Winner,To win match",
        ).split(",")
        if x.strip()
    }
    raw_floor = os.environ.get("ALTEA_MIN_CANDIDATE_ODDS", "1.30").strip()
    try:
        min_candidate_odds = max(1.0, float(raw_floor))
    except ValueError:
        min_candidate_odds = 1.30
    header = {
        "title": title,
        "date": date_str,
        "daily_run_id": daily_run_id,
        "pick_count": 0,
        "min_candidate_odds": round(min_candidate_odds, 2),
    }

    # event_id -> fila del modelo (picks + motivo_sin_pick)
    model_rows: Dict[int, Dict[str, Any]] = {}
    for item in model_out.get("picks_by_event") or []:
        if not isinstance(item, dict):
            continue
        eid = item.get("event_id")
        try:
            eid_i = int(eid)
        except Exception:
            continue
        picks = item.get("picks") or []
        if not isinstance(picks, list):
            picks = []
        motivo_raw = item.get("motivo_sin_pick")
        motivo_s = str(motivo_raw).strip() if motivo_raw is not None else ""
        model_rows[eid_i] = {"picks": picks, "motivo_sin_pick": motivo_s}

    events: List[Dict[str, Any]] = []
    pick_count = 0
    tradable_pick_count = 0
    non_tradable_pick_count = 0
    for ev in ds_input:
        eid = int(ev.get("event_id"))
        ec = ev.get("event_context") or {}
        schedule_display = ev.get("schedule_display") or {}
        processed = ev.get("processed") or {}

        mrow = model_rows.get(eid)
        if mrow is None:
            picks_raw: List[Dict[str, Any]] = []
            model_motivo = ""
            model_missing = True
        else:
            picks_raw = list(mrow.get("picks") or [])
            model_motivo = str(mrow.get("motivo_sin_pick") or "").strip()
            model_missing = False

        picks_payload: List[Dict[str, Any]] = []
        pipeline_drop_reasons: List[str] = []
        for p in picks_raw:
            if not isinstance(p, dict):
                pipeline_drop_reasons.append(
                    "Propuesta del modelo con formato inválido (no es objeto JSON)."
                )
                continue
            market = p.get("market")
            selection_code = p.get("selection")
            odds = p.get("odds")
            edge_pct = p.get("edge_pct")
            confianza = p.get("confianza")
            razon = p.get("razon")
            if market is None or selection_code is None:
                pipeline_drop_reasons.append(
                    "Pick del modelo incompleto (falta mercado o selección)."
                )
                continue
            if sport == "tennis":
                mk_norm = str(market).strip().lower()
                if mk_norm not in allowed_tennis_markets:
                    pipeline_drop_reasons.append(
                        f"Mercado «{market}» no permitido para publicación (tenis)."
                    )
                    continue

            # Render expects selection string.
            selection_display = _selection_display(str(market), str(selection_code), ec)

            model_odds = odds if isinstance(odds, (int, float)) else None
            scraped_odds = scraped_decimal_odds_for_pick(
                processed,
                market=str(market),
                selection_code=str(selection_code),
            )
            if scraped_odds is not None:
                final_odds: Optional[float] = scraped_odds
                odds_source = "scraped_sofascore"
            elif model_odds is not None and model_odds > 1.0:
                final_odds = float(model_odds)
                odds_source = "model"
            else:
                final_odds = None
                odds_source = "model"

            # Blindaje operativo tenis: evita publicar picks sin ancla de cuota scrapeada.
            if sport == "tennis" and tennis_require_scraped and odds_source != "scraped_sofascore":
                pipeline_drop_reasons.append(
                    "Pick del modelo descartado: se exige cuota scrapeada SofaScore y no hubo ancla."
                )
                continue

            is_tradable = bool(
                final_odds is not None and float(final_odds) >= min_candidate_odds
            )
            if is_tradable:
                tradable_pick_count += 1
            else:
                non_tradable_pick_count += 1

            edge_pct_out: Optional[float] = (
                float(edge_pct) if isinstance(edge_pct, (int, float)) else None
            )
            confianza_out = str(confianza) if confianza is not None else ""
            if (
                odds_source == "scraped_sofascore"
                and final_odds is not None
                and isinstance(edge_pct, (int, float))
                and isinstance(model_odds, (int, float))
                and model_odds > 1.0
            ):
                rec = recompute_edge_pct_at_new_odds(
                    model_odds=float(model_odds),
                    edge_pct_model=float(edge_pct),
                    new_odds=float(final_odds),
                )
                if rec is not None:
                    edge_pct_out = rec
                    confianza_out = confianza_from_edge(rec)

            picks_payload.append(
                {
                    "market": str(market),
                    "selection": selection_display,
                    "odds": final_odds,
                    "edge_pct": edge_pct_out,
                    "confianza": confianza_out,
                    "razon": razon if razon is not None else "",
                    "odds_source": odds_source,
                    "model_odds": model_odds,
                    "scraped_odds": scraped_odds,
                    "tradable": is_tradable,
                    "tradable_min_odds": round(min_candidate_odds, 2),
                    "tradable_exclusion_reason": (
                        None if is_tradable else "below_min_odds"
                    ),
                }
            )
        pick_count += len(picks_payload)

        model_skip_reason_out: Optional[str] = None
        pipeline_skip_summary_out: Optional[str] = None
        if not picks_payload:
            if model_missing:
                model_skip_reason_out = (
                    "El modelo no incluyó este evento en picks_by_event."
                )
            elif not picks_raw:
                model_skip_reason_out = (
                    model_motivo
                    if model_motivo
                    else "Sin picks del modelo (motivo_sin_pick vacío o ausente)."
                )
            else:
                model_skip_reason_out = (
                    "El modelo propuso pick(s), pero ninguno pasó validación/publicación del pipeline."
                )
                if pipeline_drop_reasons:
                    pipeline_skip_summary_out = "; ".join(
                        dict.fromkeys(pipeline_drop_reasons)
                    )

        events.append(
            {
                "label": _label_from_event_context(ec),
                "league": _league_from_event_context(ec),
                "local_time_short": _local_time_short_from_schedule_display(schedule_display),
                "event_id": eid,
                "picks": picks_payload,
                "model_skip_reason": model_skip_reason_out,
                "pipeline_skip_summary": pipeline_skip_summary_out,
            }
        )

    header["pick_count"] = pick_count
    header["tradable_pick_count"] = tradable_pick_count
    header["non_tradable_pick_count"] = non_tradable_pick_count
    return {"header": header, "events": events}


def main() -> None:
    args = parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"Error: falta env var {args.api_key_env}", file=sys.stderr)
        sys.exit(2)

    files = sorted(glob.glob(args.input_glob))
    if not files:
        print(f"Error: no se encontraron batches con glob: {args.input_glob}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    part_files: List[str] = []
    for idx, path in enumerate(files, start=1):
        with open(path, "r", encoding="utf-8") as f:
            batch = json.load(f)

        sport = infer_sport_from_batch(batch)
        system_prompt = _build_system_prompt(sport=sport)
        user_prompt = _build_user_prompt(batch, date_str=args.date, sport=sport)
        retries = 0
        last_err: Optional[Exception] = None

        reasoner_hint = ""
        if "reasoner" in str(args.model).lower():
            reasoner_hint = " (reasoner: a menudo 3–10 min por lote)"
        print(
            f"⏳ DeepSeek lote {idx}/{len(files)} modelo={args.model!r} timeout={args.timeout_sec}s{reasoner_hint} — "
            "esperando respuesta…",
            file=sys.stderr,
            flush=True,
        )

        while retries <= args.max_retries:
            try:
                resp = _call_deepseek_chat(
                    base_url=args.base_url,
                    api_key=api_key,
                    model=args.model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    timeout_sec=args.timeout_sec,
                    disable_response_format=args.disable_response_format,
                )
                content, reasoning = _extract_message_content(resp)
                if not (content or "").strip() and reasoning.strip():
                    # Caso real visto con reasoner: content vacío, reasoning lleno.
                    content = _force_json_from_reasoning(
                        base_url=args.base_url,
                        api_key=api_key,
                        chat_model=args.chat_fallback_model,
                        reasoning_text=reasoning,
                        timeout_sec=args.timeout_sec,
                    )
                model_out = _parse_model_output(content)
                payload = _build_payload_from_batch(
                    batch, model_out, date_str=args.date, exec_id=args.exec_id, title=args.title
                )

                out_path = os.path.join(
                    args.output_dir,
                    f"payload_{args.date}_{args.exec_id}_part{idx:02d}.json",
                )
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                part_files.append(out_path)
                print(f"OK batch {idx}/{len(files)} -> {out_path}", file=sys.stderr)
                last_err = None
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                retries += 1
                print(f"Error batch {idx} (try {retries}/{args.max_retries+1}): {e}", file=sys.stderr)
                if retries > args.max_retries:
                    break
                time.sleep(1.0)

        if last_err is not None:
            print(f"Fallo batch {idx}: {last_err}", file=sys.stderr)
            sys.exit(1)

    print(json.dumps({"job": "deepseek_batches_to_telegram_payload_parts", "parts": part_files}, ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()

