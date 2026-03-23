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
from db.repositories.picks_repo import (
    generate_idempotency_key,
    insert_picks,
)  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Persistir picks en SQLite (idempotente).")
    p.add_argument("--daily-run-id", type=int, required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--input-json", type=str, default=None, help="Ruta JSON. Si no, lee stdin.")
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    args = parse_args()
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

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
        insert_picks(conn, daily_run_id=args.daily_run_id, picks=normalized_rows, created_at_utc=_utc_now_iso())

    result = {
        "job": "persist_picks",
        "daily_run_id": args.daily_run_id,
        "picks_persisted": len(normalized_rows),
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

