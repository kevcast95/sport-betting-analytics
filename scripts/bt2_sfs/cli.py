#!/usr/bin/env python3
"""
S6.5 — pipeline BT2-SFS (historical 6d, daily, métricas, shadow, export join).

Desde la raíz del repo:
  python scripts/bt2_sfs/cli.py historical --run-id s65-h1 --anchor-date 2026-04-17 --force
  python scripts/bt2_sfs/cli.py daily --run-id s65-d1 --anchor-date 2026-04-17 --force
  python scripts/bt2_sfs/cli.py metrics --run-id s65-h1 --out-json out/s65_metrics.json
  python scripts/bt2_sfs/cli.py shadow --run-id s65-h1 --limit 20 --force
  python scripts/bt2_sfs/cli.py export-join --run-id s65-h1 --out-csv out/s65_join.csv

Migración: `j4k5l6m7n8o9`. Kill switch: BT2_SFS_EXPERIMENT_ENABLED=1 o --force (TL).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_repo = Path(__file__).resolve().parents[2]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from dotenv import load_dotenv

load_dotenv(_repo / ".env")

from sqlalchemy import select
from sqlalchemy.orm import Session
from apps.api.bt2_models import Bt2DsrDsInputShadow, Bt2Event, Bt2ProviderOddsSnapshot, Bt2SfsJoinAudit
from apps.api.bt2.providers.sofascore.canonical_map import (
    CANONICAL_VERSION_S65,
    merge_canonical_rows,
    map_all_raw_to_rows,
    map_featured_raw_to_rows,
)
from apps.api.bt2.providers.sofascore.client import sfs_client_from_settings
from apps.api.bt2.providers.sofascore.join_resolve import load_seed_mapping
from apps.api.bt2_sfs_cdm_ingest import process_bt2_events_sfs_odds
from apps.api.bt2_settings import bt2_settings
from scripts.bt2_sfs._db import make_session
from scripts.bt2_sfs._metrics_core import compute_run_metrics, verdict_from_metrics

PROVIDER_SFS = "sofascore_experimental"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger("bt2_sfs_cli")


def _require_experiment(force: bool) -> None:
    if force:
        return
    if not getattr(bt2_settings, "bt2_sfs_experiment_enabled", False):
        logger.error("BT2_SFS_EXPERIMENT_ENABLED no está en true; usar --force (TL).")
        sys.exit(2)


def _closed_days_before_anchor(anchor: date) -> list[date]:
    return [anchor - timedelta(days=i) for i in range(6, 0, -1)]


def _events_kickoff_day(session: Session, day: date, limit: int) -> list[Bt2Event]:
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return list(
        session.execute(
            select(Bt2Event)
            .where(Bt2Event.kickoff_utc.isnot(None))
            .where(Bt2Event.kickoff_utc >= start)
            .where(Bt2Event.kickoff_utc < end)
            .order_by(Bt2Event.id)
            .limit(limit)
        ).scalars().all()
    )


def _process_event_batch(
    session: Session,
    evs: list[Bt2Event],
    *,
    run_id: str,
    client,
    seed: dict[int, int],
    skip_layer2: bool,
    dry_run: bool,
) -> None:
    process_bt2_events_sfs_odds(
        session,
        evs,
        run_id=run_id,
        client=client,
        seed_by_sm_fixture=seed,
        skip_layer2=skip_layer2,
        dry_run=dry_run,
    )


def cmd_historical(args: argparse.Namespace) -> None:
    _require_experiment(args.force)
    anchor = date.fromisoformat(args.anchor_date)
    days = _closed_days_before_anchor(anchor)
    seed = load_seed_mapping(args.seed_json or bt2_settings.bt2_sfs_join_seed_json_path or None)
    max_e = int(args.max_events or bt2_settings.bt2_sfs_experiment_max_events_per_run)
    client = sfs_client_from_settings()
    session = make_session()
    try:
        for day in days:
            evs = _events_kickoff_day(session, day, max_e)
            logger.info("day=%s events=%s", day.isoformat(), len(evs))
            _process_event_batch(
                session,
                evs,
                run_id=args.run_id,
                client=client,
                seed=seed,
                skip_layer2=args.skip_layer2,
                dry_run=args.dry_run,
            )
            session.commit()
        man = {
            "run_id": args.run_id,
            "anchor_date": args.anchor_date,
            "mode": "historical_6d",
            "days": [d.isoformat() for d in days],
        }
        outp = Path("out") / f"s65_historical_manifest_{args.run_id}.json"
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(man, indent=2), encoding="utf-8")
        logger.info("manifest %s", outp)
    finally:
        session.close()


def cmd_daily(args: argparse.Namespace) -> None:
    _require_experiment(args.force)
    anchor = date.fromisoformat(args.anchor_date)
    seed = load_seed_mapping(args.seed_json or bt2_settings.bt2_sfs_join_seed_json_path or None)
    max_e = int(args.max_events or bt2_settings.bt2_sfs_experiment_max_events_per_run)
    client = sfs_client_from_settings()
    session = make_session()
    try:
        evs = _events_kickoff_day(session, anchor, max_e)
        logger.info("daily anchor=%s events=%s", anchor, len(evs))
        _process_event_batch(
            session,
            evs,
            run_id=args.run_id,
            client=client,
            seed=seed,
            skip_layer2=False,
            dry_run=False,
        )
        session.commit()
        man = {"run_id": args.run_id, "anchor_date": args.anchor_date, "mode": "daily"}
        outp = Path("out") / f"s65_daily_manifest_{args.run_id}.json"
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(man, indent=2), encoding="utf-8")
        logger.info("manifest %s", outp)
    finally:
        session.close()


def cmd_metrics(args: argparse.Namespace) -> None:
    session = make_session()
    try:
        m = compute_run_metrics(session, args.run_id)
        m["verdict_heuristic"] = verdict_from_metrics(m)
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(m, indent=2), encoding="utf-8")
        logger.info("wrote %s", out)
    finally:
        session.close()


def cmd_shadow(args: argparse.Namespace) -> None:
    _require_experiment(args.force)
    session = make_session()
    try:
        audits = list(
            session.execute(
                select(Bt2SfsJoinAudit)
                .where(Bt2SfsJoinAudit.run_id == args.run_id, Bt2SfsJoinAudit.sofascore_event_id.isnot(None))
                .limit(args.limit)
            ).scalars().all()
        )
        n = 0
        for a in audits:
            feat = session.execute(
                select(Bt2ProviderOddsSnapshot).where(
                    Bt2ProviderOddsSnapshot.run_id == args.run_id,
                    Bt2ProviderOddsSnapshot.bt2_event_id == a.bt2_event_id,
                    Bt2ProviderOddsSnapshot.source_scope == "featured",
                )
            ).scalar_one_or_none()
            alls = session.execute(
                select(Bt2ProviderOddsSnapshot).where(
                    Bt2ProviderOddsSnapshot.run_id == args.run_id,
                    Bt2ProviderOddsSnapshot.bt2_event_id == a.bt2_event_id,
                    Bt2ProviderOddsSnapshot.source_scope == "all",
                )
            ).scalar_one_or_none()
            if not feat or not alls:
                continue
            rf = feat.raw_payload if isinstance(feat.raw_payload, dict) else {}
            ra = alls.raw_payload if isinstance(alls.raw_payload, dict) else {}
            merged = merge_canonical_rows(map_featured_raw_to_rows(rf), map_all_raw_to_rows(ra))
            ingested = feat.ingested_at_utc.isoformat() if feat.ingested_at_utc else None
            payload = {
                "experimental": True,
                "odds_provider": PROVIDER_SFS,
                "truth_source": "sportmonks_cdm_plus_sfs_experiment",
                "provider_event_ref": str(a.sofascore_event_id),
                "provider_snapshot_run_id": args.run_id,
                "ingested_at_utc": ingested,
                "canonical_version": CANONICAL_VERSION_S65,
                "odds_canonical_v0": merged,
            }
            session.add(Bt2DsrDsInputShadow(bt2_event_id=a.bt2_event_id, run_id=args.run_id, payload_json=payload))
            n += 1
        session.commit()
        logger.info("shadow rows written: %s", n)
    finally:
        session.close()


def cmd_export_join(args: argparse.Namespace) -> None:
    session = make_session()
    try:
        rows = session.execute(select(Bt2SfsJoinAudit).where(Bt2SfsJoinAudit.run_id == args.run_id)).scalars().all()
        outp = Path(args.out_csv)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["bt2_event_id", "sofascore_event_id", "match_layer", "match_status", "detail_json"])
            for r in rows:
                w.writerow(
                    [
                        r.bt2_event_id,
                        r.sofascore_event_id,
                        r.match_layer,
                        r.match_status,
                        json.dumps(r.detail_json or {}, ensure_ascii=False),
                    ]
                )
        logger.info("wrote %s", outp)
    finally:
        session.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Bypass BT2_SFS_EXPERIMENT_ENABLED (TL).")
    sp = p.add_subparsers(dest="cmd", required=True)

    ph = sp.add_parser("historical")
    ph.add_argument("--run-id", required=True)
    ph.add_argument("--anchor-date", required=True)
    ph.add_argument("--seed-json", default="")
    ph.add_argument("--max-events", type=int, default=0)
    ph.add_argument("--dry-run", action="store_true")
    ph.add_argument("--skip-layer2", action="store_true")
    ph.set_defaults(func=cmd_historical)

    pdaily = sp.add_parser("daily")
    pdaily.add_argument("--run-id", required=True)
    pdaily.add_argument("--anchor-date", required=True)
    pdaily.add_argument("--seed-json", default="")
    pdaily.add_argument("--max-events", type=int, default=0)
    pdaily.set_defaults(func=cmd_daily)

    pm = sp.add_parser("metrics")
    pm.add_argument("--run-id", required=True)
    pm.add_argument("--out-json", default="out/s65_metrics.json")
    pm.set_defaults(func=cmd_metrics)

    ps = sp.add_parser("shadow")
    ps.add_argument("--run-id", required=True)
    ps.add_argument("--limit", type=int, default=20)
    ps.set_defaults(func=cmd_shadow)

    pe = sp.add_parser("export-join")
    pe.add_argument("--run-id", required=True)
    pe.add_argument("--out-csv", default="out/s65_join.csv")
    pe.set_defaults(func=cmd_export_join)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
