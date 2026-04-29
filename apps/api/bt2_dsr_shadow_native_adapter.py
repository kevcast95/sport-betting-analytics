"""
Adapter shadow-native → input DSR (experimento; no productivo).

Lee cuotas TOA desde `bt2_shadow_provider_snapshots.raw_payload` (p. ej. `payload_summary`
JSON con `data.bookmakers`) y las agrega con la misma canonización que `bt2_odds_snapshot`.

No usa `bt2_odds_snapshot` ni `aggregated_odds_for_event_psycopg` para la elegibilidad
shadow-native; la identidad del evento para el lote DSR es `shadow_daily_pick.id`
(sintética, estable por fila).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, aggregate_odds_for_event, event_passes_value_pool
from apps.api.bt2_dsr_ds_input_builder import build_ds_input_item
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT


def _parse_ts(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _unwrap_inner_payload(blob: Any) -> dict[str, Any]:
    """TOA historical: objeto con `data`, o string JSON de payload_summary."""
    if blob is None:
        return {}
    if isinstance(blob, str):
        blob = blob.strip()
        if not blob:
            return {}
        try:
            blob = json.loads(blob)
        except json.JSONDecodeError:
            return {}
    if not isinstance(blob, dict):
        return {}
    data = blob.get("data")
    if isinstance(data, dict) and data:
        return data
    return blob


def extract_toa_data_from_shadow_raw_payload(raw_payload: Any) -> dict[str, Any]:
    """
    Extrae el bloque `data` TOA desde lo persistido en shadow.

    Soporta:
    - raw_payload ya como dict API (`data` anidado o plano con bookmakers)
    - raw_payload.payload_summary (string JSON del CSV/lab)
    - raw_payload anidado solo con payload_summary
    """
    if raw_payload is None:
        return {}
    if isinstance(raw_payload, str):
        try:
            raw_payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw_payload, dict):
        return {}

    ps = raw_payload.get("payload_summary")
    if isinstance(ps, str) and ps.strip().startswith("{"):
        inner = _unwrap_inner_payload(ps)
        if inner:
            return inner
    inner = _unwrap_inner_payload(raw_payload)
    if inner:
        return inner
    return _unwrap_inner_payload(raw_payload.get("data"))


def _norm_team(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _outcome_to_classify_selection(outcome_name: str, *, home_team: str, away_team: str) -> Optional[str]:
    """
    TOA devuelve nombres de club en outcomes; `classify_snapshot_row` espera Home/Away/Draw
    (o alias) para FT_1X2.
    """
    o = (outcome_name or "").strip()
    ol = o.lower()
    if ol == "draw":
        return "Draw"
    nh, na = _norm_team(home_team), _norm_team(away_team)
    on = _norm_team(o)
    if nh and on == nh:
        return "Home"
    if na and on == na:
        return "Away"
    # Coincidencia por prefijo (nombres largos / sufijos de TV)
    if nh and (nh in on or on in nh):
        return "Home"
    if na and (na in on or on in na):
        return "Away"
    return None


def toa_bookmakers_to_aggregate_rows(
    bookmakers: list[Any],
    *,
    default_fetched_at: datetime,
    home_team: str = "",
    away_team: str = "",
) -> list[tuple[Any, ...]]:
    """
    Convierte bookmakers TOA (mercado h2h) en filas para `aggregate_odds_for_event`.

    Tupla: (bookmaker_key, market_label, selection_name, decimal_odds, fetched_at).
    """
    rows: list[tuple[Any, ...]] = []
    if not isinstance(bookmakers, list):
        return rows
    for bm in bookmakers:
        if not isinstance(bm, dict):
            continue
        bkey = str(bm.get("key") or bm.get("title") or "unknown")
        for mkt in bm.get("markets") or []:
            if not isinstance(mkt, dict):
                continue
            if str(mkt.get("key") or "").lower() != "h2h":
                continue
            lu = _parse_ts(mkt.get("last_update")) or _parse_ts(bm.get("last_update")) or default_fetched_at
            for oc in mkt.get("outcomes") or []:
                if not isinstance(oc, dict):
                    continue
                name = str(oc.get("name") or "").strip()
                cls_sel = _outcome_to_classify_selection(name, home_team=home_team, away_team=away_team)
                if not cls_sel:
                    continue
                try:
                    price = float(oc.get("price"))
                except (TypeError, ValueError):
                    continue
                rows.append((bkey, "match winner", cls_sel, price, lu))
    return rows


def aggregated_odds_from_toa_shadow_payload(
    raw_payload: Any,
    *,
    provider_snapshot_time: Optional[datetime] = None,
    min_decimal: float = MIN_ODDS_DECIMAL_DEFAULT,
) -> tuple[AggregatedOdds, dict[str, Any]]:
    data = extract_toa_data_from_shadow_raw_payload(raw_payload)
    bookmakers = data.get("bookmakers") if isinstance(data, dict) else None
    if not isinstance(bookmakers, list):
        bookmakers = []
    ht = str(data.get("home_team") or "") if isinstance(data, dict) else ""
    at = str(data.get("away_team") or "") if isinstance(data, dict) else ""
    ft = provider_snapshot_time or datetime.now(tz=timezone.utc)
    rows = toa_bookmakers_to_aggregate_rows(
        bookmakers, default_fetched_at=ft, home_team=ht, away_team=at
    )
    meta = {
        "toa_home_team": (data.get("home_team") if isinstance(data, dict) else None) or "",
        "toa_away_team": (data.get("away_team") if isinstance(data, dict) else None) or "",
        "toa_commence_time": (data.get("commence_time") if isinstance(data, dict) else None) or "",
        "bookmaker_rows_normalized": len(rows),
    }
    return aggregate_odds_for_event(rows, min_decimal=min_decimal), meta


def shadow_native_passes_value_pool(
    agg: AggregatedOdds,
    *,
    min_decimal: float = MIN_ODDS_DECIMAL_DEFAULT,
) -> bool:
    return event_passes_value_pool(agg, min_decimal=min_decimal)


def build_ds_input_shadow_native(
    *,
    synthetic_event_id: int,
    league_name: str,
    country: Optional[str],
    league_tier: Optional[str],
    home_team: str,
    away_team: str,
    kickoff_utc: Optional[datetime],
    event_status: str,
    agg: AggregatedOdds,
) -> dict[str, Any]:
    """Misma forma que `build_ds_input_item` pero `event_id` = id shadow (correlación DSR)."""
    return build_ds_input_item(
        event_id=int(synthetic_event_id),
        selection_tier="A",
        kickoff_utc=kickoff_utc,
        event_status=event_status,
        league_name=league_name,
        country=country,
        league_tier=league_tier,
        home_team=home_team,
        away_team=away_team,
        agg=agg,
        sfs_fusion_applied=False,
        sfs_fusion_synthetic_rows=0,
    )


def merge_pick_inputs_odds_blob(payload_json: Any) -> Optional[str]:
    """Si odds_row trae payload_summary (lab/backfill), úsalo para parsear bookmakers."""
    if not isinstance(payload_json, dict):
        return None
    od = payload_json.get("odds_row")
    if not isinstance(od, dict):
        return None
    ps = od.get("payload_summary")
    if isinstance(ps, str) and ps.strip():
        return ps
    return None
