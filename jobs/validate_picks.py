import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(REPO_ROOT, "playwright-browsers")

from db.config import get_db_config  # noqa: E402
from db.db import connect, transaction  # noqa: E402
from db.init_db import init_db  # noqa: E402
from db.repositories.daily_runs_repo import get_daily_run  # noqa: E402
from db.repositories.pick_results_repo import insert_pick_result  # noqa: E402
from db.repositories.picks_repo import fetch_pending_picks_without_results, set_pick_status  # noqa: E402
from db.repositories.tracking_repo import sync_realized_returns_for_pick  # noqa: E402


async def _validate_one(event_id: int, selection: str) -> Any:
    from core.validate_1x2 import validate_1x2  # noqa: E402

    return await validate_1x2(event_id, selection)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validar picks 1X2 contra marcador final (idempotente).")
    p.add_argument("--db", required=True)
    p.add_argument("--daily-run-id", type=int, default=None)
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _run(args: argparse.Namespace) -> None:
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

    if args.daily_run_id is not None:
        _ = get_daily_run(conn, args.daily_run_id)  # valida existencia

    pending = fetch_pending_picks_without_results(
        conn,
        daily_run_id=args.daily_run_id,
        limit=args.limit,
    )

    if not pending:
        print("\n=== VALIDATE_PICKS ===")
        print(json.dumps({"job": "validate_picks", "pending": 0, "message": "No hay picks pendientes de validar"}, indent=2))
        print("=== OK (nada que validar) ===\n")
        return

    validated_count = 0
    pending_count = 0
    first_time_count = 0
    revalidation_count = 0

    # Validación secuencial: cada pick dispara un fetch/bot y mantener determinismo.
    for row in pending:
        # sqlite3.Row no tiene .get(); usar indexación
        if bool(row["is_revalidation"]):
            revalidation_count += 1
        else:
            first_time_count += 1
        pick_id = int(row["pick_id"])
        event_id = int(row["event_id"])
        market = str(row["market"] or "")
        selection = str(row["selection"])

        if market.strip().upper() != "1X2":
            print(
                json.dumps(
                    {
                        "pick_id": pick_id,
                        "skipped": True,
                        "reason": "validate_picks solo soporta mercado 1X2",
                        "market": market,
                    },
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            continue

        res = await _validate_one(event_id, selection)
        outcome = str(res.get("outcome") or "pending")
        result_1x2 = res.get("result_1x2")
        score = res.get("score") or {}
        home_score = score.get("home")
        away_score = score.get("away")

        # outcome del processor: win|loss|pending.
        evidence = res

        with transaction(conn):
            insert_pick_result(
                conn,
                pick_id=pick_id,
                validated_at_utc=_utc_now_iso(),
                home_score=home_score,
                away_score=away_score,
                result_1x2=result_1x2,
                outcome=outcome if outcome in ("win", "loss", "pending") else "pending",
                evidence_json=evidence,
            )

            # Mapeo status picks (schema): pending|validated|void
            if outcome in ("win", "loss"):
                set_pick_status(conn, pick_id=pick_id, status="validated")
                validated_count += 1
            else:
                set_pick_status(conn, pick_id=pick_id, status="pending")
                pending_count += 1

            sync_realized_returns_for_pick(conn, pick_id=pick_id)

    result = {
        "job": "validate_picks",
        "total_processed": len(pending),
        "validated": validated_count,
        "pending_outcomes": pending_count,
        "primera_validacion": first_time_count,
        "revalidacion": revalidation_count,
    }
    print("\n=== VALIDATE_PICKS ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=== OK ===\n")


def main() -> None:
    args = parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

