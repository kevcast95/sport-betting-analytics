#!/usr/bin/env python3
"""
Sonda de caja negra — request real a DSR (carril shadow-native v6), sin replay masivo.

Reconstruye exactamente el mismo batch + mensajes que
`deepseek_suggest_batch_shadow_native_v6_with_trace` (system v6, user modular v6,
json.dumps(batch), modelo deepseek-v4-pro, response_format json_object).

Entrada: muestra de auditoría `dsr_native_full_replay_v6_sample_audit.json` (ds_input_blind por caso).

No escribe en tablas de producción; solo HTTP al endpoint configurado en settings (clave desde env/settings).

Uso:
  PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --all
  PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --source-shadow-pick-id 149
  PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --pick-ids 149,157,165
  PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --dry-run --all
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_admin_backtest_replay import BLIND_LOT_OPERATING_DAY_KEY  # noqa: E402
from apps.api.bt2_dsr_contract import (  # noqa: E402
    PIPELINE_VERSION_DEFAULT,
    assert_no_forbidden_ds_keys,
    validate_ds_batch_envelope,
)
from apps.api.bt2_dsr_deepseek import (  # noqa: E402
    _default_http_post,
    _extract_content_from_chat_response,
    _http_post,
    _parse_json_object,
)
from apps.api.bt2_dsr_shadow_native_deepseek_v6 import (  # noqa: E402
    _parse_picks_by_event_v6,
)
from apps.api.bt2_dsr_shadow_native_prompt_v6 import (  # noqa: E402
    SYSTEM_PROMPT_SHADOW_NATIVE_V6,
    build_user_prompt_shadow_native_v6,
)
from apps.api.bt2_settings import bt2_settings  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
DEFAULT_AUDIT = OUT_DIR / "dsr_native_full_replay_v6_sample_audit.json"
OUT_REQUESTS = OUT_DIR / "dsr_v6_request_probe_requests.json"
OUT_RESPONSES = OUT_DIR / "dsr_v6_request_probe_responses.json"
OUT_SUMMARY = OUT_DIR / "dsr_v6_request_probe_summary.json"

MODEL = "deepseek-v4-pro"
TEMPERATURE = 0.2


def _redact_headers(h: dict[str, str]) -> dict[str, str]:
    out = dict(h)
    if "Authorization" in out:
        out["Authorization"] = "Bearer <redacted>"
    return out


def _build_batch_one(ds_input_item: dict[str, Any]) -> dict[str, Any]:
    batch_obj: dict[str, Any] = {
        "operating_day_key": BLIND_LOT_OPERATING_DAY_KEY,
        "pipeline_version": PIPELINE_VERSION_DEFAULT,
        "sport": "football",
        "ds_input": [ds_input_item],
    }
    validate_ds_batch_envelope(batch_obj)
    assert_no_forbidden_ds_keys(batch_obj)
    return batch_obj


def _build_chat_body(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
    }


def _max_tokens_for_batch(n_events: int) -> int:
    return min(16384, 1400 + 420 * int(n_events))


def _row_for_event(parsed: dict[str, Any], event_id: int) -> Optional[dict[str, Any]]:
    raw = parsed.get("picks_by_event")
    if not isinstance(raw, list):
        return None
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get("event_id")) == int(event_id):
                return row
        except (TypeError, ValueError):
            continue
    return None


def _final_pick_fields_from_row(row: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "selection_canonical": row.get("selection_canonical"),
        "selected_team": row.get("selected_team"),
        "confidence_label": row.get("confidence_label"),
        "rationale_short_es": row.get("rationale_short_es"),
        "no_pick_reason": row.get("no_pick_reason"),
    }


def _load_audit_cases(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        root = json.load(f)
    cases = root.get("cases")
    if not isinstance(cases, list):
        raise SystemExit(f"audit sin cases[]: {path}")
    return [c for c in cases if isinstance(c, dict)]


def _filter_cases(
    cases: list[dict[str, Any]],
    *,
    all_flag: bool,
    source_shadow_pick_id: Optional[int],
    bt2_event_id: Optional[int],
    pick_ids: Optional[list[int]],
) -> list[dict[str, Any]]:
    if pick_ids:
        want = set(pick_ids)
        out = []
        for c in cases:
            sid = c.get("source_shadow_pick_id")
            try:
                if sid is not None and int(sid) in want:
                    out.append(c)
            except (TypeError, ValueError):
                continue
        return out
    if source_shadow_pick_id is not None:
        for c in cases:
            try:
                if int(c.get("source_shadow_pick_id")) == int(source_shadow_pick_id):
                    return [c]
            except (TypeError, ValueError):
                continue
        return []
    if bt2_event_id is not None:
        for c in cases:
            try:
                if int(c.get("bt2_event_id")) == int(bt2_event_id):
                    return [c]
            except (TypeError, ValueError):
                continue
        return []
    if all_flag:
        return list(cases)
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description="Sonda request DSR shadow-native v6 (muestra auditoría)")
    ap.add_argument(
        "--audit-json",
        type=Path,
        default=DEFAULT_AUDIT,
        help="Ruta al JSON de auditoría v6 sample",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="Procesar todos los casos del archivo (sin esto, usa --pick-ids / --source-shadow-pick-id / --bt2-event-id)",
    )
    ap.add_argument("--source-shadow-pick-id", type=int, default=None, help="Filtrar por source_shadow_pick_id (= event_id en ds_input)")
    ap.add_argument("--bt2-event-id", type=int, default=None, help="Filtrar por bt2_event_id")
    ap.add_argument(
        "--pick-ids",
        type=str,
        default=None,
        help="Lista separada por comas de source_shadow_pick_id",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Armar requests y artefactos sin llamar HTTP",
    )
    args = ap.parse_args()

    if not args.audit_json.is_file():
        raise SystemExit(f"No existe audit: {args.audit_json}")

    cases_all = _load_audit_cases(args.audit_json)
    pick_ids: Optional[list[int]] = None
    if args.pick_ids:
        pick_ids = []
        for part in args.pick_ids.split(","):
            part = part.strip()
            if part.isdigit():
                pick_ids.append(int(part))

    if (
        not args.all
        and args.source_shadow_pick_id is None
        and args.bt2_event_id is None
        and not pick_ids
    ):
        raise SystemExit(
            "Indica qué casos ejecutar: --all, --source-shadow-pick-id, --bt2-event-id o --pick-ids."
        )

    filtered = _filter_cases(
        cases_all,
        all_flag=args.all,
        source_shadow_pick_id=args.source_shadow_pick_id,
        bt2_event_id=args.bt2_event_id,
        pick_ids=pick_ids,
    )

    if not filtered:
        raise SystemExit(
            "Ningún caso seleccionado. Usa --all, --source-shadow-pick-id, --bt2-event-id o --pick-ids."
        )

    dkey = (bt2_settings.deepseek_api_key or "").strip()
    if not dkey and not args.dry_run:
        raise SystemExit("Falta deepseek_api_key (settings/env) o usa --dry-run.")

    base_url = str(bt2_settings.bt2_dsr_deepseek_base_url).rstrip("/") + "/"
    chat_url = base_url.rstrip("/") + "/" + "chat/completions"
    timeout_sec = float(bt2_settings.bt2_dsr_timeout_sec)

    poster = _http_post or _default_http_post

    requests_out: list[dict[str, Any]] = []
    responses_out: list[dict[str, Any]] = []
    summary_cases: list[dict[str, Any]] = []

    system_prompt = SYSTEM_PROMPT_SHADOW_NATIVE_V6

    for case in filtered:
        blind = case.get("ds_input_blind")
        if not isinstance(blind, dict):
            raise SystemExit("caso sin ds_input_blind válido")

        event_id_ds = blind.get("event_id")
        try:
            eid_int = int(event_id_ds)
        except (TypeError, ValueError):
            raise SystemExit(f"ds_input_blind.event_id inválido: {event_id_ds!r}")

        batch_json_exact = _build_batch_one(blind)
        user_prompt_full = build_user_prompt_shadow_native_v6(
            operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
            batch=batch_json_exact,
        )
        max_tokens = _max_tokens_for_batch(1)
        request_body_final = _build_chat_body(
            system_prompt=system_prompt,
            user_prompt=user_prompt_full,
            max_tokens=max_tokens,
        )
        raw_body = json.dumps(request_body_final).encode("utf-8")
        headers_send = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {dkey}",
        }

        req_record = {
            "event_id": eid_int,
            "bt2_event_id": case.get("bt2_event_id"),
            "source_shadow_pick_id": case.get("source_shadow_pick_id"),
            "league": case.get("league_name"),
            "home_team": case.get("home_team"),
            "away_team": case.get("away_team"),
            "system_prompt_full": system_prompt,
            "user_prompt_full": user_prompt_full,
            "batch_json_exact": batch_json_exact,
            "request_body_final": request_body_final,
            "meta": {
                "model": MODEL,
                "max_tokens": max_tokens,
                "temperature": TEMPERATURE,
                "response_format": {"type": "json_object"},
                "endpoint_chat_completions": chat_url,
                "headers_for_audit_redacted": _redact_headers(headers_send),
                "operating_day_key": BLIND_LOT_OPERATING_DAY_KEY,
                "pipeline_version": PIPELINE_VERSION_DEFAULT,
            },
        }
        requests_out.append(req_record)

        # Consola: verificación rápida de integridad (sin secretos)
        batch_dump = json.dumps(batch_json_exact, ensure_ascii=False)
        emb_ok = batch_dump in user_prompt_full
        print(
            f"\n=== event_id(ds_input)={eid_int} | {case.get('home_team')} vs {case.get('away_team')} ==="
        )
        print(f"len(system_prompt)={len(system_prompt)} len(user_prompt)={len(user_prompt_full)}")
        print(f"user_prompt contiene JSON del batch completo (substring): {emb_ok}")
        print(f"max_tokens={max_tokens} model={MODEL} temperature={TEMPERATURE}")

        raw_response_full: Optional[str] = None
        extracted_content: Optional[str] = None
        parsed_json: Optional[dict[str, Any]] = None
        parse_status = "skipped_dry_run"
        parsed_row: Optional[dict[str, Any]] = None
        pipeline_tuple: Optional[Any] = None
        parse_err_detail = ""

        if not args.dry_run:
            try:
                raw_bytes = poster(chat_url, headers_send, raw_body, timeout_sec)
                raw_response_full = raw_bytes.decode("utf-8", errors="replace")
                resp = json.loads(raw_response_full)
                extracted_content = _extract_content_from_chat_response(resp)
                parsed_json = _parse_json_object(extracted_content)
                if not parsed_json:
                    parse_status = "parse_json_fail"
                    parse_err_detail = "contenido no es JSON objeto tras strip/markdown"
                    if extracted_content:
                        parse_err_detail += (
                            f" | excerpt_tail={(extracted_content or '')[-1200:]!r}"
                        )
                else:
                    parsed_row = _row_for_event(parsed_json, eid_int)
                    pipeline_map = _parse_picks_by_event_v6(parsed_json, [eid_int])
                    pipeline_tuple = pipeline_map.get(eid_int)
                    if pipeline_tuple is None:
                        parse_status = "parse_row_missing"
                    else:
                        parse_status = "ok"
            except urllib.error.HTTPError as e:
                parse_status = f"http_{e.code}"
                try:
                    raw_response_full = e.read().decode("utf-8", errors="replace")
                except Exception:
                    raw_response_full = str(e)
                parse_err_detail = raw_response_full[:4000]
            except Exception as e:
                parse_status = f"error_{type(e).__name__}"
                parse_err_detail = str(e)

        resp_record = {
            "event_id": eid_int,
            "bt2_event_id": case.get("bt2_event_id"),
            "source_shadow_pick_id": case.get("source_shadow_pick_id"),
            "raw_response_full": raw_response_full,
            "extracted_content": extracted_content,
            "parsed_json": parsed_json,
            "parsed_row": parsed_row,
            "parse_status": parse_status,
            "parse_pipeline_tuple": (
                list(pipeline_tuple) if pipeline_tuple is not None else None
            ),
            "final_pick_fields": _final_pick_fields_from_row(parsed_row),
            "failure_detail": parse_err_detail or None,
        }
        responses_out.append(resp_record)

        summary_cases.append(
            {
                "event_id": eid_int,
                "source_shadow_pick_id": case.get("source_shadow_pick_id"),
                "parse_status": parse_status,
                "user_prompt_has_batch_json_substring": emb_ok,
            }
        )

    meta_root = {
        "audit_source": str(args.audit_json),
        "dry_run": args.dry_run,
        "model": MODEL,
        "cases_run": len(filtered),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_REQUESTS.open("w", encoding="utf-8") as f:
        json.dump({"meta": meta_root, "cases": requests_out}, f, ensure_ascii=False, indent=2)
    with OUT_RESPONSES.open("w", encoding="utf-8") as f:
        json.dump({"meta": meta_root, "cases": responses_out}, f, ensure_ascii=False, indent=2)
    with OUT_SUMMARY.open("w", encoding="utf-8") as f:
        json.dump({"meta": meta_root, "cases": summary_cases}, f, ensure_ascii=False, indent=2)

    print(f"\nArtefactos:\n  {OUT_REQUESTS}\n  {OUT_RESPONSES}\n  {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
