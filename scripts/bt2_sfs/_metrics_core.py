"""Cálculo métricas S6.5 (D-06-067 / D-06-068)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.bt2_models import Bt2ProviderOddsSnapshot, Bt2SfsJoinAudit
from apps.api.bt2.providers.sofascore.canonical_map import (
    is_event_useful_s65,
    map_all_raw_to_rows,
    map_featured_raw_to_rows,
    merge_canonical_rows,
)
from scripts.bt2_sfs._sm_rows import sm_odds_snapshot_rows_for_event

PROVIDER_SFS = "sofascore_experimental"


def _raw_ok(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and not payload.get("_error")


def compute_run_metrics(session: Session, run_id: str) -> dict[str, Any]:
    audits = session.execute(select(Bt2SfsJoinAudit).where(Bt2SfsJoinAudit.run_id == run_id)).scalars().all()
    n_cohort = len(audits)
    n_matched = sum(1 for a in audits if a.sofascore_event_id is not None and a.match_status == "matched")
    n_no_comp = sum(
        1
        for a in audits
        if a.sofascore_event_id is None or a.match_status != "matched"
    )
    match_rate = (n_matched / n_cohort) if n_cohort else 0.0
    no_comp_rate = (n_no_comp / n_cohort) if n_cohort else 0.0

    n_comparable = 0
    sm_useful = 0
    sfs_useful = 0
    solo_sm = solo_sfs = both = neither = 0

    for a in audits:
        if a.sofascore_event_id is None or a.match_status != "matched":
            continue
        ev_id = a.bt2_event_id
        sm_rows = sm_odds_snapshot_rows_for_event(session, ev_id)
        feat = session.execute(
            select(Bt2ProviderOddsSnapshot).where(
                Bt2ProviderOddsSnapshot.run_id == run_id,
                Bt2ProviderOddsSnapshot.bt2_event_id == ev_id,
                Bt2ProviderOddsSnapshot.provider == PROVIDER_SFS,
                Bt2ProviderOddsSnapshot.source_scope == "featured",
            )
        ).scalar_one_or_none()
        alls = session.execute(
            select(Bt2ProviderOddsSnapshot).where(
                Bt2ProviderOddsSnapshot.run_id == run_id,
                Bt2ProviderOddsSnapshot.bt2_event_id == ev_id,
                Bt2ProviderOddsSnapshot.provider == PROVIDER_SFS,
                Bt2ProviderOddsSnapshot.source_scope == "all",
            )
        ).scalar_one_or_none()
        if not feat or not alls:
            continue
        rf = feat.raw_payload if isinstance(feat.raw_payload, dict) else {}
        ra = alls.raw_payload if isinstance(alls.raw_payload, dict) else {}
        if not _raw_ok(rf) or not _raw_ok(ra):
            continue
        sfs_merged = merge_canonical_rows(map_featured_raw_to_rows(rf), map_all_raw_to_rows(ra))
        sm_u = is_event_useful_s65(sm_rows)
        sfs_u = is_event_useful_s65(sfs_merged)
        if not sm_rows and not sfs_merged:
            continue
        n_comparable += 1
        if sm_u:
            sm_useful += 1
        if sfs_u:
            sfs_useful += 1
        if sm_u and sfs_u:
            both += 1
        elif sm_u and not sfs_u:
            solo_sm += 1
        elif sfs_u and not sm_u:
            solo_sfs += 1
        else:
            neither += 1

    kpi_sm = (100.0 * sm_useful / n_comparable) if n_comparable else None
    kpi_sfs = (100.0 * sfs_useful / n_comparable) if n_comparable else None
    gap_pp: float | None = None
    if kpi_sm is not None and kpi_sfs is not None:
        gap_pp = float(kpi_sm) - float(kpi_sfs)

    return {
        "schema_version": "s65-metrics-v1",
        "run_id": run_id,
        "n_cohort": n_cohort,
        "n_matched_join": n_matched,
        "match_rate": round(match_rate, 6),
        "n_no_comparable": n_no_comp,
        "no_comparable_rate": round(no_comp_rate, 6),
        "n_comparable_kpi": n_comparable,
        "sm_useful_count": sm_useful,
        "sfs_useful_count": sfs_useful,
        "kpi_principal_pct_sm": None if kpi_sm is None else round(kpi_sm, 4),
        "kpi_principal_pct_sfs": None if kpi_sfs is None else round(kpi_sfs, 4),
        "gap_sm_minus_sfs_pp": None if gap_pp is None else round(gap_pp, 4),
        "secondary_solo_sm": solo_sm,
        "secondary_solo_sfs": solo_sfs,
        "secondary_both": both,
        "secondary_neither": neither,
    }


def verdict_from_metrics(m: dict[str, Any]) -> str:
    """Heurística GO/PIVOT/NO-GO (requiere shadow_ok y ops en acta humana)."""
    mr = float(m.get("match_rate") or 0)
    nc = float(m.get("no_comparable_rate") or 0)
    if mr < 0.70:
        return "NO-GO"
    if nc > 0.15:
        return "NO-GO"
    gap = m.get("gap_sm_minus_sfs_pp")
    if gap is not None and float(gap) > 10:
        return "NO-GO"
    if mr >= 0.85 and nc <= 0.15 and gap is not None and float(gap) <= 5:
        return "GO_CANDIDATE"
    return "PIVOT"
