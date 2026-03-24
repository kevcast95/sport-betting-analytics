import os
import sys

# Cuando se ejecuta `python3 jobs/<script>.py`, Python no incluye la raíz del repo en sys.path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(REPO_ROOT, "playwright-browsers")

import argparse  # noqa: E402
import asyncio  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import Any, Dict, Optional  # noqa: E402

from db.config import get_db_config  # noqa: E402
from db.db import connect, transaction  # noqa: E402
from db.init_db import init_db  # noqa: E402
from db.repositories.event_features_repo import insert_event_features  # noqa: E402
from db.repositories.event_snapshots_repo import upsert_event_snapshot  # noqa: E402

from core.event_bundle_scraper import fetch_event_bundle  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _processor_versions_json(repo_root: str) -> Dict[str, Any]:
    """
    Versionado por contenido (hash SHA256) de los módulos usados.
    Esto es determinista mientras el repo no cambie.
    """
    paths = {
        "core.event_bundle_scraper": os.path.join(repo_root, "core", "event_bundle_scraper.py"),
        "processors.lineups_processor": os.path.join(repo_root, "processors", "lineups_processor.py"),
        "processors.statistics_processor": os.path.join(repo_root, "processors", "statistics_processor.py"),
        "processors.h2h_processor": os.path.join(repo_root, "processors", "h2h_processor.py"),
        "processors.team_streaks_processor": os.path.join(repo_root, "processors", "team_streaks_processor.py"),
        "processors.odds_all_processor": os.path.join(repo_root, "processors", "odds_all_processor.py"),
        "processors.odds_feature_processor": os.path.join(repo_root, "processors", "odds_feature_processor.py"),
        "processors.team_season_stats_processor": os.path.join(repo_root, "processors", "team_season_stats_processor.py"),
        "processors.tennis_odds_processor": os.path.join(repo_root, "processors", "tennis_odds_processor.py"),
    }
    return {k: _sha256_file(v) for k, v in paths.items()}


async def persist_event_bundle(
    *,
    event_id: int,
    conn,
    captured_at_utc: Optional[str] = None,
    sport: str = "football",
) -> bool:
    """
    Persistencia idempotente:
    - event_snapshots (event|lineups|statistics|h2h|team_streaks|team_season_stats|odds_all|odds_featured)
    - event_features (JSON procesado completo)
    """
    # Forzamos el path inmediatamente antes del launch (Playwright puede basarse en env runtime).
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(REPO_ROOT, "playwright-browsers")
    sp = (sport or "football").strip().lower()
    captured = captured_at_utc
    if captured is None:
        # Idempotencia fuerte:
        # Si ya existe event_features para este event_id, reutilizamos su captured_at_utc
        # para que el re-run NO cree nuevas filas.
        cur = conn.execute(
            """
            SELECT captured_at_utc
            FROM event_features
            WHERE event_id = ? AND sport = ?
            ORDER BY captured_at_utc DESC
            LIMIT 1
            """,
            (event_id, sp),
        )
        row = cur.fetchone()
        if row is not None and row["captured_at_utc"]:
            captured = str(row["captured_at_utc"])

    if captured is None:
        captured = _utc_now_iso()

    # Si ya tenemos event_features para (event_id, captured_at_utc), no recalculamos.
    already = conn.execute(
        "SELECT 1 FROM event_features WHERE sport = ? AND event_id = ? AND captured_at_utc = ? LIMIT 1",
        (sp, event_id, captured),
    ).fetchone()
    if already is not None:
        return True

    bundle = await fetch_event_bundle(event_id, sport=sp)
    bundle_meta = bundle.get("bundle_meta") or {}
    source = str(bundle_meta.get("source") or "sofascore")

    event_context = bundle.get("event_context") or {}
    match_state = str(event_context.get("match_state") or "").lower()

    def _env_truthy(key: str) -> bool:
        return os.environ.get(key, "").lower() in ("1", "true", "yes")

    # INCLUDE_FINISHED preferido; ALTEA_INCLUDE_FINISHED solo compatibilidad antigua
    include_finished = _env_truthy("INCLUDE_FINISHED") or _env_truthy("ALTEA_INCLUDE_FINISHED")
    if match_state == "finished" and not include_finished:
        # Evita llenar la DB con eventos ya terminados en flujos operativos.
        return False

    processed = bundle.get("processed") or {}

    datasets = {
        "event": event_context,
        "lineups": processed.get("lineups") or {},
        "statistics": processed.get("statistics") or {},
        "h2h": processed.get("h2h") or {},
        "team_streaks": processed.get("team_streaks") or {},
        "team_season_stats": processed.get("team_season_stats") or {},
        "odds_all": processed.get("odds_all") or {},
        "odds_featured": processed.get("odds_featured") or {},
    }

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    versions = _processor_versions_json(repo_root)

    diagnostics = bundle.get("diagnostics") or {}

    features_json: Dict[str, Any] = {
        "bundle_meta": bundle_meta,
        "event_context": bundle.get("event_context") or {},
        "diagnostics": diagnostics,
        "processed": processed,
    }

    with transaction(conn):
        for dataset, payload in datasets.items():
            upsert_event_snapshot(
                conn=conn,
                event_id=event_id,
                dataset=dataset,
                captured_at_utc=captured,
                payload_raw=payload,
                source=source,
                sport=sp,
            )
        insert_event_features(
            conn=conn,
            event_id=event_id,
            captured_at_utc=captured,
            features_json=features_json,
            processor_versions_json=versions,
            sport=sp,
        )

    return True

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Persistir snapshot+features de un eventId en SQLite.")
    p.add_argument("--event-id", "-e", type=int, required=True)
    p.add_argument("--sport", default="football", help="Slug daily_runs / SofaScore (football, tennis, …).")
    p.add_argument("--db", required=True)
    p.add_argument("--captured-at-utc", type=str, default=None, help="ISO datetime (opcional).")
    p.add_argument(
        "--include-finished",
        action="store_true",
        help="Si se activa, también persiste events match_state=finished (útil para backtesting).",
    )
    p.add_argument("--pretty", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

    if args.include_finished:
        os.environ["INCLUDE_FINISHED"] = "true"

    persisted = asyncio.run(
        persist_event_bundle(
            event_id=args.event_id,
            conn=conn,
            captured_at_utc=args.captured_at_utc,
            sport=args.sport,
        )
    )
    result = {
        "job": "persist_event_bundle",
        "event_id": args.event_id,
        "persisted": persisted,
        "db": cfg.path,
        "captured_at_utc": args.captured_at_utc,
    }
    print("\n=== PERSIST_EVENT_BUNDLE ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=== OK ===\n")


if __name__ == "__main__":
    main()

