"""Persistencia idempotente bt2_provider_odds_snapshot."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.bt2_models import Bt2ProviderOddsSnapshot


def upsert_provider_odds_snapshot(
    session: Session,
    *,
    bt2_event_id: int,
    provider: str,
    source_scope: str,
    run_id: str,
    raw_payload: dict[str, Any],
    provider_event_ref: Optional[str] = None,
    canonical_version: str = "s65-v0",
) -> Bt2ProviderOddsSnapshot:
    row = session.execute(
        select(Bt2ProviderOddsSnapshot).where(
            Bt2ProviderOddsSnapshot.bt2_event_id == bt2_event_id,
            Bt2ProviderOddsSnapshot.provider == provider,
            Bt2ProviderOddsSnapshot.source_scope == source_scope,
            Bt2ProviderOddsSnapshot.run_id == run_id,
        )
    ).scalar_one_or_none()
    if row is None:
        row = Bt2ProviderOddsSnapshot(
            bt2_event_id=bt2_event_id,
            provider=provider,
            source_scope=source_scope,
            run_id=run_id,
            canonical_version=canonical_version,
            provider_event_ref=provider_event_ref,
            raw_payload=raw_payload,
        )
        session.add(row)
    else:
        row.raw_payload = raw_payload
        row.provider_event_ref = provider_event_ref
        row.canonical_version = canonical_version
    return row
