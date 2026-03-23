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
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DeepSeek batch analysis -> telegram_payload parts")
    p.add_argument("--input-glob", required=True, help="Glob de batches; ej. out/batches/candidates_2026-03-22_exec_08h_batch*.json")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (para header/date del payload)")
    p.add_argument("--exec-id", required=True, help="exec_08h o exec_16h (solo para naming de salida)")
    p.add_argument("--title", default="Copa Foxkids", help="header.title del payload")
    p.add_argument("--model", default="deepseek-chat", help="deepseek-chat o deepseek-reasoner")
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--max-tokens", type=int, default=1200)
    p.add_argument("--timeout-sec", type=int, default=180)
    p.add_argument("--max-retries", type=int, default=1)
    p.add_argument("--base-url", default="https://api.deepseek.com", help="DeepSeek base_url (OpenAI-compatible)")
    p.add_argument("--api-key-env", default="DEEPSEEK_API_KEY", help="Env var con la API key")
    p.add_argument("--output-dir", default="out", help="Directorio de salida (default: out)")
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
    if mk == "1X2":
        if sel == "1":
            return f"1 ({home})"
        if sel == "X":
            return "X (Empate)"
        if sel == "2":
            return f"2 ({away})"
        return sel
    return sel


def _build_system_prompt() -> str:
    return (
        "Eres un analista de fútbol para apuestas. "
        "Debes producir SOLO JSON válido (sin markdown, sin texto adicional). "
        "El JSON debe seguir el esquema pedido por el usuario. "
        "No inventes cuotas: usa las odds desde el campo `processed` del evento."
    )


def _build_user_prompt(batch: Dict[str, Any], *, date_str: str) -> str:
    # Nota: pedimos picks por evento; el runner completa label/league/local_time y la selección de 1X2 con paréntesis.
    return (
        f"Fecha de referencia: {date_str}.\n"
        "Tarea: con el lote `batch` (campo ds_input), elige picks para cada evento.\n\n"
        "Reglas de salida:\n"
        "- Devuelve SOLO un objeto JSON con esta forma:\n"
        "{\n"
        '  "picks_by_event": [\n'
        "    {\n"
        '      "event_id": 123,\n'
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
        "- Para 1X2: usa selection exactamente '1','X','2' (el runner convertirá a '1 (HomeTeam)' etc.).\n"
        "- Máximo 2 picks por evento. Si no hay odds relevantes, puede dejar picks=[] para ese evento.\n"
        "- Cálculo de EDGE:\n"
        "  p_imp_pct = round(100 / odds, 2)\n"
        "  elige p_real_pct (0-100) de forma razonada (probabilidad subjetiva en %)\n"
        "  edge_pct = round(p_real_pct - p_imp_pct, 2)\n"
        "- Confianza basada en edge_pct:\n"
        "  edge_pct >= 5 => Alta\n"
        "  edge_pct >= 3 => Media-Alta\n"
        "  edge_pct >= 1.5 => Media\n"
        "  else => Baja\n"
        "- 'razon' debe ser 1 frase basada en lineups/h2h/streaks y/o odds trend (Tier A vs Tier B).\n\n"
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


def _extract_text_content(resp: Dict[str, Any]) -> str:
    # OpenAI chat format: choices[0].message.content
    choices = resp.get("choices") or []
    if not choices:
        raise ValueError("DeepSeek response sin choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise ValueError("DeepSeek response sin message.content str")
    return content


def _parse_model_output(content: str) -> Dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Salida no es JSON válido: {e}") from e
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
    header = {"title": title, "date": date_str, "daily_run_id": daily_run_id, "pick_count": 0}

    # Map event_id -> picks list
    picks_map: Dict[int, List[Dict[str, Any]]] = {}
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
            continue
        picks_map[eid_i] = picks

    events: List[Dict[str, Any]] = []
    pick_count = 0
    for ev in ds_input:
        eid = int(ev.get("event_id"))
        ec = ev.get("event_context") or {}
        schedule_display = ev.get("schedule_display") or {}
        picks_raw = picks_map.get(eid) or []

        picks_payload: List[Dict[str, Any]] = []
        for p in picks_raw:
            if not isinstance(p, dict):
                continue
            market = p.get("market")
            selection_code = p.get("selection")
            odds = p.get("odds")
            edge_pct = p.get("edge_pct")
            confianza = p.get("confianza")
            razon = p.get("razon")
            if market is None or selection_code is None:
                continue

            # Render expects selection string.
            selection_display = _selection_display(str(market), str(selection_code), ec)

            picks_payload.append(
                {
                    "market": str(market),
                    "selection": selection_display,
                    "odds": odds if isinstance(odds, (int, float)) else None,
                    "edge_pct": edge_pct if isinstance(edge_pct, (int, float)) else None,
                    "confianza": confianza if confianza is not None else "",
                    "razon": razon if razon is not None else "",
                }
            )
        pick_count += len(picks_payload)

        events.append(
            {
                "label": _label_from_event_context(ec),
                "league": _league_from_event_context(ec),
                "local_time_short": _local_time_short_from_schedule_display(schedule_display),
                "event_id": eid,
                "picks": picks_payload,
            }
        )

    header["pick_count"] = pick_count
    return {"header": header, "events": events}


def main() -> None:
    args = parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"Error: falta env var {args.api_key_env}", file=sys.stderr)
        sys.exit(2)

    system_prompt = _build_system_prompt()
    files = sorted(glob.glob(args.input_glob))
    if not files:
        print(f"Error: no se encontraron batches con glob: {args.input_glob}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    part_files: List[str] = []
    for idx, path in enumerate(files, start=1):
        with open(path, "r", encoding="utf-8") as f:
            batch = json.load(f)

        user_prompt = _build_user_prompt(batch, date_str=args.date)
        retries = 0
        last_err: Optional[Exception] = None

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
                content = _extract_text_content(resp)
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

