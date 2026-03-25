import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, List, Optional


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.config import get_db_config  # noqa: E402
from db.db import connect, transaction  # noqa: E402
from db.init_db import init_db  # noqa: E402
from db.repositories.daily_runs_repo import (
    ensure_daily_run,
    get_daily_run,
    update_status,
)  # noqa: E402

from jobs.persist_event_bundle import persist_event_bundle  # noqa: E402


def _validate_run_date(date_str: str) -> None:
    """
    Evita copiar el placeholder de la documentación tal cual (provoca 404 en SofaScore).
    """
    s = (date_str or "").strip()
    if s.upper() == "YYYY-MM-DD" or "YYYY" in s.upper():
        print(
            "Error: --date debe ser una fecha real (ej. 2026-03-22), no el texto YYYY-MM-DD del README.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        parsed = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: --date inválida {date_str!r}; usa formato YYYY-MM-DD.", file=sys.stderr)
        sys.exit(2)
    # Evita typos tipo 2016 en lugar de 2026 (run huérfano: dashboard no lo ve con la fecha real).
    if os.environ.get("ALTEA_ALLOW_DIVERGENT_INGEST_DATE", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        today = date.today()
        if abs(parsed - today) > timedelta(days=400):
            print(
                f"Error: --date={date_str} está a más de ~400 días de hoy ({today.isoformat()}). "
                "¿Typo de año? Para forzar, exporta ALTEA_ALLOW_DIVERGENT_INGEST_DATE=1.",
                file=sys.stderr,
            )
            sys.exit(2)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingesta daily events y persiste bundles en SQLite.")
    p.add_argument("--sport", required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--db", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--include-finished",
        action="store_true",
        help="Si se activa, también persiste events match_state=finished (backtesting).",
    )
    return p.parse_args()


def _extract_event_ids(payload: Any) -> List[int]:
    # SofaScore suele devolver dict con array dentro, pero soportamos formas variadas.
    if isinstance(payload, list):
        ids = []
        for it in payload:
            if isinstance(it, dict) and "id" in it:
                ids.append(int(it["id"]))
            elif isinstance(it, int):
                ids.append(it)
        return ids

    if isinstance(payload, dict):
        for key in ("events", "scheduledEvents", "scheduled_events"):
            if key in payload and isinstance(payload[key], list):
                return _extract_event_ids(payload[key])
        if "id" in payload:
            try:
                return [int(payload["id"])]
            except Exception:
                return []
    return []


def _fetch_scheduled_events(sport: str, date: str) -> Any:
    url = f"https://www.sofascore.com/api/v1/sport/{sport}/scheduled-events/{date}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


async def _run(args: argparse.Namespace) -> None:
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

    daily_run_id, existing_status = ensure_daily_run(conn, args.date, args.sport)
    if existing_status in ("complete", "completed"):
        print("\n=== INGEST_DAILY_EVENTS ===")
        print(json.dumps({"job": "ingest_daily_events", "daily_run_id": daily_run_id, "status": "already_complete"}, indent=2))
        print("=== OK (skip) ===\n")
        return

    daily = get_daily_run(conn, daily_run_id)
    captured_at_utc = daily["created_at_utc"]

    try:
        if args.include_finished:
            os.environ["INCLUDE_FINISHED"] = "true"

        payload = _fetch_scheduled_events(args.sport, args.date)
        event_ids = _extract_event_ids(payload)
        if args.limit is not None:
            event_ids = event_ids[: int(args.limit)]

        if not event_ids:
            raise RuntimeError("No eventIds returned by scheduled-events endpoint.")

        print("\n=== INGEST_DAILY_EVENTS ===", flush=True)
        print(f"  daily_run_id: {daily_run_id}", flush=True)
        print(f"  run_date: {args.date}", flush=True)
        print(f"  sport: {args.sport}", flush=True)
        print(f"  event_ids_fetched: {len(event_ids)}", flush=True)
        print(f"  event_ids (primeros 10): {event_ids[:10]}", flush=True)
        print(f"  captured_at_utc: {captured_at_utc}", flush=True)
        print("  --- Persistiendo bundles ---", flush=True)
        persisted = 0
        skipped = 0
        t0 = time.monotonic()
        total = len(event_ids)
        for i, event_id in enumerate(event_ids, start=1):
            print(f"    [{i}/{total}] event_id={event_id} ...", flush=True)
            ok = await persist_event_bundle(
                event_id=event_id,
                conn=conn,
                captured_at_utc=captured_at_utc,
            )
            if ok:
                persisted += 1
                state = "persisted"
            else:
                skipped += 1
                state = "skipped"
            elapsed = time.monotonic() - t0
            print(
                f"      -> {state} | persisted={persisted} skipped={skipped} elapsed={elapsed:.1f}s",
                flush=True,
            )

        update_status(conn, daily_run_id, "complete")

        result = {
            "job": "ingest_daily_events",
            "daily_run_id": daily_run_id,
            "events_attempted": len(event_ids),
            "events_persisted": persisted,
            "events_skipped_finished": skipped,
            "status": "complete",
        }
        print("\n  --- RESULT ---", flush=True)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        print("=== OK INGEST ===\n", flush=True)
    except Exception as e:
        update_status(conn, daily_run_id, "failed")
        raise e


def main() -> None:
    args = parse_args()
    _validate_run_date(args.date)
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

