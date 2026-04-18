#!/usr/bin/env python3
"""
Validación operativa: ¿fusionó SFS en el agregador? vs ¿qué mercado elige la bóveda?

Uso (raíz del repo):
  PYTHONPATH=apps/api:. python3 scripts/bt2_sfs/validate_fusion_live.py
  PYTHONPATH=apps/api:. python3 scripts/bt2_sfs/validate_fusion_live.py --event-id 102632

Imprime:
  - BT2_SFS_MARKETS_FUSION_ENABLED desde settings
  - Para eventos de picks del día (o uno): rows en bt2_provider_odds_snapshot (SFS)
  - market_coverage del agregador (SM + fusión si aplica)
  - Si existe pick: model_market_canonical + dsr_source (reglas del sistema)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[2]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from dotenv import load_dotenv

load_dotenv(_repo / ".env")

import psycopg2
from psycopg2.extras import RealDictCursor

from apps.api.bt2_settings import bt2_settings
from apps.api.bt2_dsr_ds_input_builder import build_ds_input_item_from_db


def _db():
    url = (bt2_settings.bt2_database_url or "").replace("postgresql+asyncpg://", "postgresql://", 1)
    return psycopg2.connect(url)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--event-id", type=int, default=0, help="Solo este bt2_events.id")
    args = p.parse_args()

    fusion_on = bool(getattr(bt2_settings, "bt2_sfs_markets_fusion_enabled", False))
    prov = str(getattr(bt2_settings, "bt2_sfs_odds_provider_slug", "") or "sofascore_experimental")

    out: dict = {
        "BT2_SFS_MARKETS_FUSION_ENABLED": fusion_on,
        "BT2_SFS_ODDS_PROVIDER_SLUG": prov,
        "BT2_DSR_ENABLED": bool(getattr(bt2_settings, "bt2_dsr_enabled", False)),
        "BT2_DSR_PROVIDER": str(getattr(bt2_settings, "bt2_dsr_provider", "") or ""),
        "note": "Si BT2_DSR_ENABLED=false y hay clave DeepSeek, la bóveda usa sql_stat_fallback: "
        "elige la CUOTA MÍNIMA entre mercados COMPLETOS → suele ser favorito 1X2 (regla aparte de la fusión).",
        "events": [],
    }

    conn = _db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if args.event_id:
        eids = [args.event_id]
    else:
        cur.execute(
            """
            SELECT DISTINCT event_id FROM bt2_daily_picks
            ORDER BY event_id DESC LIMIT 15
            """
        )
        eids = [int(r["event_id"]) for r in cur.fetchall()]

    for eid in eids:
        cur.execute(
            """
            SELECT COUNT(*)::int AS n_scopes,
                   MAX(ingested_at_utc)::text AS last_ingest
            FROM bt2_provider_odds_snapshot
            WHERE bt2_event_id = %s AND provider = %s
            """,
            (eid, prov),
        )
        snap = dict(cur.fetchone() or {})

        cur.execute(
            """
            SELECT model_market_canonical, model_selection_canonical, dsr_source, slate_rank
            FROM bt2_daily_picks
            WHERE event_id = %s
            ORDER BY slate_rank NULLS LAST
            LIMIT 1
            """,
            (eid,),
        )
        pick = cur.fetchone()

        built = build_ds_input_item_from_db(cur, eid, selection_tier="A")
        cov = {}
        diag_fusion = {}
        if built:
            _item, agg = built
            cov = {k: v for k, v in agg.market_coverage.items() if v}
            d = built[0].get("diagnostics") or {}
            diag_fusion = {
                "sfs_fusion_applied": d.get("sfs_fusion_applied"),
                "sfs_fusion_synthetic_rows": d.get("sfs_fusion_synthetic_rows"),
                "markets_available": d.get("markets_available"),
            }

        out["events"].append(
            {
                "event_id": eid,
                "sfs_snapshot_rows": snap.get("n_scopes"),
                "sfs_last_ingest": snap.get("last_ingest"),
                "fusion_diagnostics": diag_fusion,
                "market_coverage_complete": sorted(cov.keys()),
                "pick_model_market": (pick or {}).get("model_market_canonical"),
                "pick_selection": (pick or {}).get("model_selection_canonical"),
                "pick_dsr_source": (pick or {}).get("dsr_source"),
            }
        )

    cur.close()
    conn.close()
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
