#!/usr/bin/env python3
"""
Comparación rápida: mercados en `bt2_odds_snapshot` (SportMonks/CDM) vs SofaScore (SFS)
para los partidos cuyo kickoff cae en un día civil local (misma ventana que la bóveda).

Uso (raíz del repo):
  PYTHONPATH=apps/api:. python3 scripts/bt2_sfs/day_markets_compare.py --date 2026-04-17
  PYTHONPATH=apps/api:. python3 scripts/bt2_sfs/day_markets_compare.py --date 2026-04-17 --with-sfs --limit 25

Salida: JSON (stdout o --out-json) con diagnóstico de bóveda + lista de partidos.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

_repo = Path(__file__).resolve().parents[2]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from dotenv import load_dotenv

load_dotenv(_repo / ".env")

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

from apps.api.bt2_dsr_odds_aggregation import aggregate_odds_for_event, event_passes_value_pool  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402
from apps.api.bt2_value_pool import (  # noqa: E402
    build_value_pool_for_snapshot,
    count_future_events_window,
    parse_priority_league_ids,
    _fetch_odds_grouped,
    _sql_prefilter_event_rows,
)
from apps.api.bt2.providers.sofascore.canonical_map import (  # noqa: E402
    count_core_additional_complete,
    is_event_useful_s65,
    is_ft_1x2_complete,
    merge_canonical_rows,
    map_all_raw_to_rows,
    map_featured_raw_to_rows,
)
from apps.api.bt2.providers.sofascore.client import sfs_client_from_settings  # noqa: E402


def _pg_url() -> str:
    url = (bt2_settings.bt2_database_url or "").replace("postgresql+asyncpg://", "postgresql://", 1)
    if not url:
        raise SystemExit("Falta BT2_DATABASE_URL / bt2_database_url en settings.")
    return url


def _user_tz(cur) -> tuple[ZoneInfo, str]:
    cur.execute("SELECT timezone::text FROM bt2_user_settings LIMIT 1")
    r = cur.fetchone()
    if not r:
        tz_name = "America/Bogota"
    else:
        v = r.get("timezone") if isinstance(r, dict) else r[0]
        tz_name = (str(v).strip() if v is not None else "") or "America/Bogota"
    try:
        return ZoneInfo(tz_name), tz_name
    except Exception:
        return timezone.utc, "UTC"


def _window_for_local_day(anchor: date, tz: ZoneInfo) -> tuple[datetime, datetime, date]:
    day_start_local = datetime.combine(anchor, datetime.min.time(), tzinfo=tz)
    day_end_local = day_start_local + timedelta(hours=24)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)
    return day_start_utc, day_end_utc, anchor


def _non_1x2_sm_complete(coverage: dict[str, bool]) -> bool:
    for k, ok in coverage.items():
        if k != "FT_1X2" and ok:
            return True
    return False


def _summarize_sfs(client, sofascore_event_id: int) -> dict[str, Any]:
    raw_f = client.fetch_odds_featured(sofascore_event_id)
    raw_a = client.fetch_odds_all(sofascore_event_id)
    if raw_f.get("_error"):
        return {"ok": False, "error": "featured", "detail": raw_f}
    if raw_a.get("_error"):
        return {"ok": False, "error": "all", "detail": raw_a}
    merged = merge_canonical_rows(map_featured_raw_to_rows(raw_f), map_all_raw_to_rows(raw_a))
    fams = sorted({str(r.get("family")) for r in merged if r.get("price") is not None})
    return {
        "ok": True,
        "sofascore_event_id": sofascore_event_id,
        "families_with_price": fams,
        "ft_1x2_complete": is_ft_1x2_complete(merged),
        "core_additional_families_count": count_core_additional_complete(merged),
        "event_useful_s65": is_event_useful_s65(merged),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="BT2 SM vs SFS — mercados por día local")
    p.add_argument("--date", required=True, help="Día civil local YYYY-MM-DD (ej. kickoff del 17 en Colombia).")
    p.add_argument("--tz", default="", help="Zona IANA (si vacío: bt2_user_settings.timezone o America/Bogota).")
    p.add_argument("--limit", type=int, default=60, help="Máximo de partidos a detallar.")
    p.add_argument("--min-decimal", type=float, default=1.30)
    p.add_argument("--with-sfs", action="store_true", help="Llamar API SofaScore (throttle). Requiere sofascore_event_id.")
    p.add_argument("--out-json", default="", help="Si se indica, escribe el JSON ahí en vez de stdout.")
    args = p.parse_args()

    anchor = date.fromisoformat(args.date.strip())
    url = _pg_url()
    conn = psycopg2.connect(url)
    # bt2_value_pool usa fetchone()[0]; requiere cursor tupla, no RealDict.
    cur_plain = conn.cursor()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if args.tz.strip():
        try:
            tz = ZoneInfo(args.tz.strip())
            tz_name = args.tz.strip()
        except Exception:
            raise SystemExit(f"TZ inválida: {args.tz!r}")
    else:
        tz, tz_name = _user_tz(cur_plain)

    day_start_utc, day_end_utc, local_day = _window_for_local_day(anchor, tz)
    league_filter = parse_priority_league_ids(bt2_settings.bt2_priority_league_ids or "")

    fut = count_future_events_window(cur_plain, day_start_utc, day_end_utc)
    pool, pre_n = build_value_pool_for_snapshot(
        cur_plain, day_start_utc, day_end_utc, league_filter=league_filter, min_decimal=args.min_decimal
    )

    cur_plain.execute(
        "SELECT MAX(kickoff_utc) FROM bt2_events WHERE status = %s",
        ("scheduled",),
    )
    mx_row = cur_plain.fetchone()
    mx_ko = mx_row[0] if mx_row else None

    vault_diag: dict[str, Any] = {
        "tz": tz_name,
        "anchor_local_date": str(local_day),
        "window_utc": [day_start_utc.isoformat(), day_end_utc.isoformat()],
        "scheduled_in_window": fut,
        "prefilter_candidates": pre_n,
        "value_pool_size": len(pool),
        "bt2_priority_league_ids": bt2_settings.bt2_priority_league_ids or "",
        "cdm_max_kickoff_scheduled_utc": mx_ko.isoformat() if mx_ko is not None else None,
        "why_vault_may_be_empty": [],
    }
    if fut == 0:
        vault_diag["why_vault_may_be_empty"].append(
            "No hay filas en bt2_events con status=scheduled, kickoff en la ventana UTC del día local, "
            "y liga is_active=true (CDM no tiene partidos elegibles ese día o aún no refrescó)."
        )
        if mx_ko is not None and mx_ko < day_end_utc:
            vault_diag["why_vault_may_be_empty"].append(
                f"El último kickoff programado en CDM es anterior al fin de la ventana del día pedido "
                f"(max_scheduled_kickoff={mx_ko.isoformat()} < window_end={day_end_utc.isoformat()}): "
                "hace falta ejecutar el pipeline CDM/SM (p. ej. fetch_upcoming / refresh) para traer fixtures."
            )
    elif pre_n == 0 and league_filter:
        vault_diag["why_vault_may_be_empty"].append(
            "Hay partidos en ventana pero el filtro BT2_PRIORITY_LEAGUE_IDS excluye todos los candidatos del prefilter."
        )
    elif pre_n > 0 and len(pool) == 0:
        vault_diag["why_vault_may_be_empty"].append(
            "Hay candidatos pero ninguno pasa value pool: en bt2_odds_snapshot no hay ningún mercado canónico "
            "completo con todas las piernas >= min_decimal (solo 1X2 u O/U incompleto / sin filas)."
        )

    cur.execute(
        """
        SELECT e.id AS bt2_event_id, e.sportmonks_fixture_id, e.sofascore_event_id, e.kickoff_utc::text,
               e.status, l.name AS league_name, l.tier AS league_tier, l.is_active AS league_active,
               ht.name AS home_name, at.name AS away_name,
               (
                 SELECT a.sofascore_event_id FROM bt2_sfs_join_audit a
                 WHERE a.bt2_event_id = e.id AND a.sofascore_event_id IS NOT NULL
                 ORDER BY a.created_at DESC NULLS LAST
                 LIMIT 1
               ) AS sofascore_from_join_audit
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams ht ON ht.id = e.home_team_id
        LEFT JOIN bt2_teams at ON at.id = e.away_team_id
        WHERE e.kickoff_utc >= %s AND e.kickoff_utc < %s
          AND e.status = 'scheduled'
          AND l.is_active = true
        ORDER BY e.kickoff_utc ASC
        LIMIT %s
        """,
        (day_start_utc, day_end_utc, int(args.limit)),
    )
    rows = list(cur.fetchall())
    eids = [int(r["bt2_event_id"]) for r in rows]
    odds_by = _fetch_odds_grouped(cur_plain, eids) if eids else {}

    client = sfs_client_from_settings() if args.with_sfs else None

    matches: list[dict[str, Any]] = []
    for r in rows:
        eid = int(r["bt2_event_id"])
        snap_rows = odds_by.get(eid, [])
        agg = aggregate_odds_for_event(snap_rows, min_decimal=args.min_decimal)
        mc_ok = {k: v for k, v in agg.market_coverage.items() if v}
        sid_col = r.get("sofascore_event_id")
        sid_audit = r.get("sofascore_from_join_audit")
        resolved_sfs: Optional[int] = None
        if sid_col is not None:
            resolved_sfs = int(sid_col)
        elif sid_audit is not None:
            resolved_sfs = int(sid_audit)

        entry: dict[str, Any] = {
            "bt2_event_id": eid,
            "sportmonks_fixture_id": r.get("sportmonks_fixture_id"),
            "sofascore_event_id": sid_col,
            "sofascore_from_join_audit": sid_audit,
            "sofascore_resolved_for_sfs_api": resolved_sfs,
            "kickoff_utc": r.get("kickoff_utc"),
            "status": r.get("status"),
            "league": r.get("league_name"),
            "league_tier": r.get("league_tier"),
            "label": f"{r.get('home_name') or '?'} vs {r.get('away_name') or '?'}",
            "bt2_sm": {
                "odds_snapshot_rows": len(snap_rows),
                "markets_available": agg.markets_available,
                "market_coverage_complete": sorted(mc_ok.keys()),
                "passes_value_pool": event_passes_value_pool(agg, min_decimal=args.min_decimal),
                "non_1x2_canonical_complete": _non_1x2_sm_complete(agg.market_coverage),
            },
            "sfs": None,
        }
        if args.with_sfs and client is not None:
            if resolved_sfs is None:
                entry["sfs"] = {"skipped": True, "reason": "no_sofascore_id_events_nor_audit"}
            else:
                entry["sfs"] = _summarize_sfs(client, resolved_sfs)
        matches.append(entry)

    out: dict[str, Any] = {
        "meta": {
            "script": "day_markets_compare",
            "min_decimal": args.min_decimal,
            "with_sfs": bool(args.with_sfs),
        },
        "vault_diag": vault_diag,
        "matches": matches,
        "summary": {
            "match_rows": len(matches),
            "with_sm_non_1x2_complete": sum(1 for m in matches if m["bt2_sm"]["non_1x2_canonical_complete"]),
            "with_sfs_core_extra": None,
        },
    }
    if args.with_sfs:
        ok_sfs = [m for m in matches if isinstance(m.get("sfs"), dict) and m["sfs"].get("ok")]
        out["summary"]["with_sfs_core_extra"] = sum(
            1 for m in ok_sfs if int(m["sfs"].get("core_additional_families_count") or 0) >= 1
        )

    cur.close()
    cur_plain.close()
    conn.close()

    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
