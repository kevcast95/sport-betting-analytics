"""
Ingesta SofaScore → `bt2_provider_odds_snapshot` compartida por `scripts/bt2_sfs/cli.py`
y `scripts/bt2_cdm/fetch_upcoming.py` (CDM diario).

Run id por defecto `cdm_fetch_upcoming`: idempotente por (evento, proveedor, scope, run).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from apps.api.bt2_models import Bt2Event
from apps.api.bt2.providers.sofascore.canonical_map import CANONICAL_VERSION_S65
from apps.api.bt2.providers.sofascore.client import SfsHttpClient, sfs_client_from_settings
from apps.api.bt2.providers.sofascore.join_resolve import (
    load_seed_mapping,
    persist_join_audit,
    resolve_sfs_event_id,
)
from apps.api.bt2.providers.sofascore.snapshot_repo import upsert_provider_odds_snapshot
from apps.api.bt2_settings import bt2_settings

logger = logging.getLogger(__name__)

PROVIDER_SFS = "sofascore_experimental"
DEFAULT_CDM_SFS_RUN_ID = "cdm_fetch_upcoming"


def _sync_database_url() -> str:
    url = (
        os.environ.get("BT2_DATABASE_URL") or getattr(bt2_settings, "bt2_database_url", "") or ""
    ).strip()
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def make_sync_session() -> Session:
    eng = create_engine(_sync_database_url(), pool_pre_ping=True)
    return sessionmaker(bind=eng, expire_on_commit=False)()


def process_bt2_events_sfs_odds(
    session: Session,
    events: list[Bt2Event],
    *,
    run_id: str,
    client: SfsHttpClient,
    seed_by_sm_fixture: dict[int, int],
    skip_layer2: bool,
    dry_run: bool,
) -> dict[str, int]:
    """
    Para cada evento: join SM→SofaScore, fetch featured+all, upsert snapshot + audit.
    """
    stats = {
        "events_in_batch": len(events),
        "snapshots_upserted": 0,
        "skipped_no_join": 0,
    }
    for ev in events:
        jr = resolve_sfs_event_id(
            session,
            ev,
            client,
            seed_by_sm_fixture=seed_by_sm_fixture,
            try_layer2=not skip_layer2,
        )
        persist_join_audit(session, run_id=run_id, bt2_event_id=ev.id, result=jr)
        if jr.sofascore_event_id is not None and not dry_run:
            ev.sofascore_event_id = int(jr.sofascore_event_id)
        if jr.sofascore_event_id is None or dry_run:
            session.flush()
            stats["skipped_no_join"] += 1
            continue
        raw_f = client.fetch_odds_featured(jr.sofascore_event_id)
        raw_a = client.fetch_odds_all(jr.sofascore_event_id)
        upsert_provider_odds_snapshot(
            session,
            bt2_event_id=ev.id,
            provider=PROVIDER_SFS,
            source_scope="featured",
            run_id=run_id,
            raw_payload=raw_f,
            provider_event_ref=str(jr.sofascore_event_id),
            canonical_version=CANONICAL_VERSION_S65,
        )
        upsert_provider_odds_snapshot(
            session,
            bt2_event_id=ev.id,
            provider=PROVIDER_SFS,
            source_scope="all",
            run_id=run_id,
            raw_payload=raw_a,
            provider_event_ref=str(jr.sofascore_event_id),
            canonical_version=CANONICAL_VERSION_S65,
        )
        session.flush()
        stats["snapshots_upserted"] += 2
    return stats


def run_sfs_auto_ingest_after_cdm_fetch(bt2_event_ids: list[int]) -> dict[str, Any]:
    """
    Tras `fetch_upcoming`: rellena `bt2_provider_odds_snapshot` para los eventos tocados.

    Kill switch: `BT2_SFS_AUTO_INGEST_ENABLED=false`.
    Cap: `bt2_sfs_experiment_max_events_per_run` (orden estable: primeros N ids únicos).
    """
    out: dict[str, Any] = {"skipped": False}
    if not getattr(bt2_settings, "bt2_sfs_auto_ingest_enabled", True):
        out["skipped"] = True
        out["reason"] = "bt2_sfs_auto_ingest_disabled"
        return out

    if not bt2_event_ids:
        out["skipped"] = True
        out["reason"] = "no_event_ids"
        return out

    ids = list(dict.fromkeys(bt2_event_ids))
    max_e = int(getattr(bt2_settings, "bt2_sfs_experiment_max_events_per_run", 500) or 500)
    truncated = False
    if len(ids) > max_e:
        ids = ids[:max_e]
        truncated = True

    run_id = str(
        getattr(bt2_settings, "bt2_sfs_cdm_run_id", None) or DEFAULT_CDM_SFS_RUN_ID
    ).strip() or DEFAULT_CDM_SFS_RUN_ID

    seed_path = getattr(bt2_settings, "bt2_sfs_join_seed_json_path", None) or None
    seed = load_seed_mapping(str(seed_path) if seed_path else None)

    session = make_sync_session()
    try:
        evs = list(
            session.execute(select(Bt2Event).where(Bt2Event.id.in_(ids))).scalars().all()
        )
        if not evs:
            out["skipped"] = True
            out["reason"] = "no_bt2_events_loaded"
            return out

        client = sfs_client_from_settings()
        stats = process_bt2_events_sfs_odds(
            session,
            evs,
            run_id=run_id,
            client=client,
            seed_by_sm_fixture=seed,
            skip_layer2=False,
            dry_run=False,
        )
        session.commit()
        out.update(stats)
        out["run_id"] = run_id
        out["truncated_to_cap"] = truncated
        out["events_requested"] = len(ids)
        logger.info(
            "[SFS-CDM] auto-ingest ok run_id=%s events=%s snapshots=%s skipped_join=%s truncated=%s",
            run_id,
            stats.get("events_in_batch"),
            stats.get("snapshots_upserted"),
            stats.get("skipped_no_join"),
            truncated,
        )
        return out
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
