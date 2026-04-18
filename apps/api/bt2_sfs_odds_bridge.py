"""
Puente Postgres → filas sintéticas compatibles con `classify_snapshot_row` / agregador DSR.

Fusiona payloads `bt2_provider_odds_snapshot` (featured + all) SofaScore ya ingeridos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from apps.api.bt2.providers.sofascore.canonical_map import (
    merge_canonical_rows,
    map_all_raw_to_rows,
    map_featured_raw_to_rows,
)


DEFAULT_SFS_PROVIDER = "sofascore_experimental"


def fetch_latest_sfs_payloads_psycopg(
    cur,
    bt2_event_id: int,
    *,
    provider: str = DEFAULT_SFS_PROVIDER,
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Último featured y último `all` por `ingested_at_utc` por scope."""
    cur.execute(
        """
        SELECT DISTINCT ON (source_scope) source_scope, raw_payload
        FROM bt2_provider_odds_snapshot
        WHERE bt2_event_id = %s AND provider = %s
          AND source_scope IN ('featured', 'all')
        ORDER BY source_scope, ingested_at_utc DESC NULLS LAST
        """,
        (bt2_event_id, provider),
    )
    featured: Optional[dict[str, Any]] = None
    all_raw: Optional[dict[str, Any]] = None
    for row in cur.fetchall():
        scope = row[0] if not isinstance(row, dict) else row.get("source_scope")
        payload = row[1] if not isinstance(row, dict) else row.get("raw_payload")
        if isinstance(payload, dict) and payload.get("_error"):
            continue
        if scope == "featured":
            featured = payload if isinstance(payload, dict) else None
        elif scope == "all":
            all_raw = payload if isinstance(payload, dict) else None
    return featured, all_raw


def merged_canonical_rows_from_sfs_payloads(
    featured: Optional[dict[str, Any]],
    all_raw: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    rf = featured if isinstance(featured, dict) else {}
    ra = all_raw if isinstance(all_raw, dict) else {}
    merged = merge_canonical_rows(map_featured_raw_to_rows(rf), map_all_raw_to_rows(ra))
    return merged


def canonical_sfs_rows_to_snapshot_tuples(
    merged: list[dict[str, Any]],
    *,
    fetched_at: Optional[datetime] = None,
) -> list[tuple[Any, ...]]:
    """
    Genera tuplas (bookmaker, market, selection, odds_decimal, fetched_at)
    reconocidas por `classify_snapshot_row`.
    """
    ts = fetched_at or datetime.now(tz=timezone.utc)
    out: list[tuple[Any, ...]] = []

    for r in merged:
        fam = str(r.get("family") or "")
        sel = str(r.get("selection") or "")
        price = r.get("price")
        if price is None:
            continue
        try:
            p = float(price)
        except (TypeError, ValueError):
            continue
        if p < 1.01:
            continue

        # Book fijo para trazabilidad en by_bookmaker (no afecta mediana fuerte si solo hay uno).
        book = "sofascore"

        if fam == "FT_1X2":
            label_by_sel = {"1": "Home", "X": "Draw", "2": "Away"}
            if sel not in label_by_sel:
                continue
            out.append((book, "Full Time Result", label_by_sel[sel], p, ts))

        elif fam == "OU_GOALS_2_5":
            su = sel.upper()
            # Texto mercado debe incluir la línea (consistente con classify_snapshot_row §O/U).
            if su == "OVER":
                out.append((book, "Goals Over/Under 2.5", "Over 2.5", p, ts))
            elif su == "UNDER":
                out.append((book, "Goals Over/Under 2.5", "Under 2.5", p, ts))

        elif fam == "BTTS":
            sl = sel.lower()
            if sl == "yes":
                out.append((book, "Both Teams To Score", "yes", p, ts))
            elif sl == "no":
                out.append((book, "Both Teams To Score", "no", p, ts))

        elif fam == "DOUBLE_CHANCE":
            label = sel.upper().replace(" ", "")
            if label == "1X":
                out.append((book, "Double Chance", "1X", p, ts))
            elif label == "X2":
                out.append((book, "Double Chance", "X2", p, ts))
            elif label == "12":
                out.append((book, "Double Chance", "12", p, ts))

    return out


def synthetic_odds_tuples_for_bt2_event_psycopg(
    cur,
    bt2_event_id: int,
    *,
    provider: str = DEFAULT_SFS_PROVIDER,
) -> tuple[list[tuple[Any, ...]], dict[str, Any]]:
    """Retorna tuplas extra + meta (sin errores si no hay snapshots)."""
    feat, allp = fetch_latest_sfs_payloads_psycopg(cur, bt2_event_id, provider=provider)
    if not feat and not allp:
        return [], {"applied": False, "reason": "no_provider_snapshots"}
    merged = merged_canonical_rows_from_sfs_payloads(feat, allp)
    if not merged:
        return [], {"applied": False, "reason": "empty_canonical_merge"}
    tuples = canonical_sfs_rows_to_snapshot_tuples(merged)
    return tuples, {
        "applied": bool(tuples),
        "canonical_rows_in": len(merged),
        "synthetic_rows": len(tuples),
    }
