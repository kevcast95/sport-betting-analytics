import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.config import get_db_config  # noqa: E402
from db.db import connect, transaction  # noqa: E402
from db.init_db import init_db  # noqa: E402
from db.sqlite_migrate import apply_migrations  # noqa: E402
from db.repositories.picks_repo import (
    generate_idempotency_key,
    insert_picks,
    normalize_selection,
)  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Persistir picks en SQLite (idempotente).")
    p.add_argument(
        "--daily-run-id",
        type=int,
        default=None,
        help="FK daily_runs. Si omites con --telegram-payload, se usa header.daily_run_id.",
    )
    p.add_argument("--db", required=True)
    p.add_argument("--input-json", type=str, default=None, help="Ruta JSON. Si no, lee stdin.")
    p.add_argument(
        "--telegram-payload",
        type=str,
        default=None,
        help="JSON tipo merge_telegram_payload (events[].picks + header.daily_run_id).",
    )
    return p.parse_args()


def _read_input_json(path: Optional[str]) -> Any:
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def _normalize_picks_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "picks" in payload and isinstance(payload["picks"], list):
        return payload["picks"]
    raise ValueError("Input JSON debe ser una lista o {\"picks\": [...]} .")


def _coerce_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def rows_from_telegram_payload(payload: Dict[str, Any], *, daily_run_id: int) -> List[Dict[str, Any]]:
    """Aplana header+events del payload post-merge en filas para insert_picks."""
    rows: List[Dict[str, Any]] = []
    for ev in payload.get("events") or []:
        if not isinstance(ev, dict):
            continue
        eid = ev.get("event_id")
        if eid is None:
            continue
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        for p in ev.get("picks") or []:
            if not isinstance(p, dict):
                continue
            market = p.get("market")
            sel_display = p.get("selection")
            if market is None or sel_display is None:
                continue
            market_s = str(market)
            picked_value = _coerce_float(p.get("odds"))
            odds_reference: Dict[str, Any] = {
                "edge_pct": p.get("edge_pct"),
                "confianza": p.get("confianza"),
                "razon": p.get("razon"),
                "selection_display": str(sel_display),
            }
            for k in (
                "odds_source",
                "model_odds",
                "scraped_odds",
                "tradable",
                "tradable_min_odds",
                "tradable_exclusion_reason",
            ):
                if p.get(k) is not None:
                    odds_reference[k] = p[k]
            norm_sel = normalize_selection(sel_display, market=market_s)
            idempotency_key = generate_idempotency_key(
                daily_run_id=daily_run_id,
                event_id=eid_i,
                market=market_s,
                selection=str(sel_display),
                picked_value=picked_value,
            )
            rows.append(
                {
                    "event_id": eid_i,
                    "market": market_s,
                    "selection": norm_sel,
                    "picked_value": picked_value,
                    "odds_reference": odds_reference,
                    "idempotency_key": idempotency_key,
                }
            )
    return rows


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    args = parse_args()
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)
    apply_migrations(conn)
    conn.commit()

    daily_run_id = args.daily_run_id
    tdata: Optional[Dict[str, Any]] = None

    if args.telegram_payload and args.input_json is not None:
        raise SystemExit("Usa solo uno: --telegram-payload o --input-json (o stdin).")

    if args.telegram_payload:
        with open(args.telegram_payload, "r", encoding="utf-8") as f:
            tdata = json.load(f)
        if not isinstance(tdata, dict):
            raise SystemExit("--telegram-payload debe ser un objeto JSON")
        header = tdata.get("header") or {}
        if daily_run_id is None:
            dr = header.get("daily_run_id")
            if dr is None:
                raise SystemExit("Falta --daily-run-id y header.daily_run_id en el payload")
            daily_run_id = int(dr)
        picks = rows_from_telegram_payload(tdata, daily_run_id=int(daily_run_id))
    else:
        if daily_run_id is None:
            raise SystemExit("--daily-run-id es obligatorio salvo con --telegram-payload")
        raw = _read_input_json(args.input_json)
        picks = _normalize_picks_payload(raw)

    normalized_rows: List[Dict[str, Any]] = []
    for p in picks:
        if not isinstance(p, dict):
            raise ValueError("Cada pick debe ser un objeto JSON.")
        event_id = int(p["event_id"])
        market = str(p["market"])
        selection = p["selection"]

        picked_value = p.get("picked_value")
        odds_reference = p.get("odds_reference")

        idempotency_key = p.get("idempotency_key")
        if idempotency_key is None:
            idempotency_key = generate_idempotency_key(
                daily_run_id=int(daily_run_id),
                event_id=event_id,
                market=market,
                selection=str(selection),
                picked_value=picked_value if "picked_value" in p else None,
            )

        normalized_rows.append(
            {
                "event_id": event_id,
                "market": market,
                "selection": selection,
                "picked_value": picked_value,
                "odds_reference": odds_reference,
                "idempotency_key": str(idempotency_key),
            }
        )

    with transaction(conn):
        inserted, attempted = insert_picks(
            conn,
            daily_run_id=int(daily_run_id),
            picks=normalized_rows,
            created_at_utc=_utc_now_iso(),
        )

    skipped = max(0, attempted - inserted)
    if args.telegram_payload and attempted == 0:
        hdr = tdata.get("header") if isinstance(tdata, dict) else {}
        pc = int((hdr or {}).get("pick_count") or 0)
        if pc > 0:
            print(
                "Advertencia: header.pick_count>0 pero no se extrajo ninguna fila para DB "
                "(revisa events[].picks y odds/selection en telegram_payload).",
                file=sys.stderr,
            )
    if attempted > 0 and inserted == 0:
        print(
            "Advertencia: 0 filas insertadas (todas ignoradas por idempotency_key duplicado "
            "o mismatch con la DB). Si es un run nuevo, revisa daily_run_id y la base en --db.",
            file=sys.stderr,
        )

    result = {
        "job": "persist_picks",
        "daily_run_id": int(daily_run_id),
        "picks_attempted": attempted,
        "picks_inserted": inserted,
        "picks_skipped_duplicate_key": skipped,
        "picks_persisted": inserted,
        "picks": [
            {"event_id": r["event_id"], "market": r["market"], "selection": r["selection"], "picked_value": r.get("picked_value")}
            for r in normalized_rows
        ],
    }
    print("\n=== PERSIST_PICKS ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=== OK ===\n")


if __name__ == "__main__":
    main()

