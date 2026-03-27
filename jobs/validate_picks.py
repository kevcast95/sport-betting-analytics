import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any, List, Optional
from zoneinfo import ZoneInfo


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


async def _validate_one(
    event_id: int,
    market: str,
    selection: str,
    picked_value: Optional[float],
) -> Any:
    from core.validate_pick import validate_pick  # noqa: E402

    return await validate_pick(
        event_id,
        market=str(market or ""),
        selection=str(selection or ""),
        picked_value=picked_value,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validar picks contra el evento SofaScore (mercados soportados en processors/pick_settlement)."
    )
    p.add_argument("--db", required=True)
    p.add_argument("--daily-run-id", type=int, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--timezone",
        default=os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota"),
        help="Zona para --only-created-local-on / horas (default COPA_FOXKIDS_TZ o America/Bogota).",
    )
    p.add_argument(
        "--only-created-local-on",
        default=None,
        metavar="YYYY-MM-DD",
        help="Solo picks cuya created_at_utc cae en este día calendario local (opcional: acotar con hour-min/max-excl; si omites horas, cuenta todo el día).",
    )
    p.add_argument(
        "--only-created-local-hour-min",
        type=int,
        default=None,
        metavar="H",
        help="Hora local inclusiva 0-23 (medio abierto junto con max-excl).",
    )
    p.add_argument(
        "--only-created-local-hour-max-excl",
        type=int,
        default=None,
        metavar="H",
        help="Hora local exclusiva 1-24 (ej. 16 y 24 → [16,24) = 16:00–23:59).",
    )
    return p.parse_args()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_created_utc(s: str) -> datetime:
    t = str(s).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _pick_matches_created_local_window(
    created_at_utc_str: str,
    *,
    tz_name: str,
    target_local_date: date,
    hour_min_incl: Optional[int],
    hour_max_excl: Optional[int],
) -> bool:
    dt_local = _parse_created_utc(created_at_utc_str).astimezone(ZoneInfo(tz_name))
    if dt_local.date() != target_local_date:
        return False
    if hour_min_incl is None and hour_max_excl is None:
        return True
    h = dt_local.hour
    lo = 0 if hour_min_incl is None else int(hour_min_incl)
    hi = 24 if hour_max_excl is None else int(hour_max_excl)
    return lo <= h < hi


def _filter_pending_by_created_local(
    rows: List[Any],
    *,
    tz_name: str,
    local_on: Optional[str],
    hour_min: Optional[int],
    hour_max_excl: Optional[int],
) -> List[Any]:
    if not local_on or not str(local_on).strip():
        return list(rows)
    target = date.fromisoformat(str(local_on).strip())
    if (hour_min is not None or hour_max_excl is not None) and (
        hour_min is None or hour_max_excl is None
    ):
        raise ValueError(
            "Filtro local: usa ambos --only-created-local-hour-min y "
            "--only-created-local-hour-max-excl, o ninguno (día entero)."
        )
    out: List[Any] = []
    for row in rows:
        created = str(row["created_at_utc"])
        if _pick_matches_created_local_window(
            created,
            tz_name=tz_name,
            target_local_date=target,
            hour_min_incl=hour_min,
            hour_max_excl=hour_max_excl,
        ):
            out.append(row)
    return out


async def _run(args: argparse.Namespace) -> None:
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

    if args.daily_run_id is not None:
        _ = get_daily_run(conn, args.daily_run_id)  # valida existencia

    pending_all = fetch_pending_picks_without_results(
        conn,
        daily_run_id=args.daily_run_id,
        limit=args.limit,
    )

    pending = _filter_pending_by_created_local(
        pending_all,
        tz_name=str(args.timezone),
        local_on=args.only_created_local_on,
        hour_min=args.only_created_local_hour_min,
        hour_max_excl=args.only_created_local_hour_max_excl,
    )

    if not pending:
        print("\n=== VALIDATE_PICKS ===")
        msg = "No hay picks pendientes de validar"
        if args.only_created_local_on:
            msg += f" (filtro local {args.only_created_local_on}"
            if args.only_created_local_hour_min is not None:
                msg += f" hora [{args.only_created_local_hour_min},{args.only_created_local_hour_max_excl})"
            msg += f", TZ {args.timezone})"
        print(
            json.dumps(
                {
                    "job": "validate_picks",
                    "pending": 0,
                    "pending_before_filter": len(pending_all),
                    "message": msg,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
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
        pv = row["picked_value"]
        picked_float: Optional[float] = float(pv) if pv is not None else None

        res = await _validate_one(event_id, market, selection, picked_float)
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
        "pending_before_filter": len(pending_all),
        "validated": validated_count,
        "pending_outcomes": pending_count,
        "primera_validacion": first_time_count,
        "revalidacion": revalidation_count,
    }
    if args.only_created_local_on:
        result["filter"] = {
            "local_date": args.only_created_local_on,
            "hour_min_incl": args.only_created_local_hour_min,
            "hour_max_excl": args.only_created_local_hour_max_excl,
            "timezone": args.timezone,
        }
    print("\n=== VALIDATE_PICKS ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=== OK ===\n")


def main() -> None:
    args = parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

