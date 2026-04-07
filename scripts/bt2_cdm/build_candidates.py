"""
build_candidates.py — Sprint 03 US-BE-008

Lee bt2_events + bt2_odds_snapshot del CDM y genera archivos JSON
en el formato ds_input compatible con el pipeline DSR existente:

    python scripts/bt2_cdm/build_candidates.py --date 2024-08-17
    python jobs/deepseek_batches_to_telegram_payload_parts.py \\
      --input-glob "out/batches/candidates_2024-08-17_exec_BT2_batch*.json" \\
      --date 2024-08-17 --exec-id exec_BT2

Parámetros CLI:
    --date YYYY-MM-DD     (requerido) Fecha del día a procesar.
    --output-dir PATH     (default: out/batches/) Directorio de salida.
    --max-events N        (default: 50) Máx eventos totales.
    --batch-size N        (default: 10) Eventos por archivo JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv
load_dotenv(Path(_repo_root) / ".env")

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("build_candidates")


def _db_conn():
    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)


def _fetch_candidates(target_date: date, max_events: int, status_filter: str = "scheduled") -> list[dict]:
    """
    Retorna eventos del día `target_date` (00:00 UTC a target_date+1 06:00 UTC)
    con al menos 1 odd disponible.
    status_filter: 'scheduled' (producción) | 'finished' (backtest/test histórico)
    """
    start_utc = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_utc = start_utc + timedelta(days=1, hours=6)

    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                e.id,
                e.kickoff_utc,
                th.name AS home_team,
                ta.name AS away_team,
                l.name  AS tournament,
                -- 1X2 best odds
                MAX(CASE WHEN o.market = 'Match Winner' AND o.selection = 'Home'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_home,
                MAX(CASE WHEN o.market = 'Match Winner' AND o.selection = 'Draw'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_draw,
                MAX(CASE WHEN o.market = 'Match Winner' AND o.selection = 'Away'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_away,
                -- Over/Under 2.5 best odds
                MAX(CASE WHEN o.market = 'Goals Over/Under' AND o.selection = 'Over'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_over25,
                MAX(CASE WHEN o.market = 'Goals Over/Under' AND o.selection = 'Under'
                         THEN CAST(o.odds AS FLOAT) END) AS odds_under25
            FROM bt2_events e
            JOIN bt2_teams th ON e.home_team_id = th.id
            JOIN bt2_teams ta ON e.away_team_id = ta.id
            JOIN bt2_leagues l ON e.league_id = l.id
            JOIN bt2_odds_snapshot o ON o.event_id = e.id
            WHERE e.kickoff_utc >= %s
              AND e.kickoff_utc < %s
              AND e.status = %s
            GROUP BY e.id, e.kickoff_utc, th.name, ta.name, l.name, l.tier
            ORDER BY
                CASE l.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END ASC,
                e.kickoff_utc ASC
            LIMIT %s
        """, (start_utc, end_utc, status_filter, max_events))
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return [dict(row) for row in rows]


def _build_ds_input(ev: dict) -> dict:
    """Construye el dict ds_input en formato compatible con el pipeline DSR."""
    odds_1x2: dict = {}
    if ev.get("odds_home"):
        odds_1x2["1"] = ev["odds_home"]
    if ev.get("odds_draw"):
        odds_1x2["X"] = ev["odds_draw"]
    if ev.get("odds_away"):
        odds_1x2["2"] = ev["odds_away"]

    odds_ou: dict = {}
    if ev.get("odds_over25"):
        odds_ou["Over 2.5"] = ev["odds_over25"]
    if ev.get("odds_under25"):
        odds_ou["Under 2.5"] = ev["odds_under25"]

    kickoff_str = (
        ev["kickoff_utc"].date().isoformat()
        if ev.get("kickoff_utc")
        else date.today().isoformat()
    )

    ds_input = {
        "event_id": ev["id"],
        "sport": "football",
        "event_context": {
            "home_team": ev["home_team"],
            "away_team": ev["away_team"],
            "tournament": ev["tournament"],
            "date": kickoff_str,
        },
        "processed": {
            "odds_all": {}
        },
    }

    if odds_1x2:
        ds_input["processed"]["odds_all"]["1X2"] = odds_1x2
    if odds_ou:
        ds_input["processed"]["odds_all"]["Over/Under 2.5"] = odds_ou

    return ds_input


def build_candidates(
    target_date: date,
    output_dir: Path,
    max_events: int = 50,
    batch_size: int = 10,
    status_filter: str = "scheduled",
) -> list[Path]:
    """
    Genera archivos JSON de candidatos para la fecha dada.
    Retorna lista de paths de archivos generados.
    status_filter='scheduled' (default producción) | 'finished' (para backtest/test con datos históricos)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[BTC] Buscando candidatos para %s (status=%s, max=%d)", target_date, status_filter, max_events)
    rows = _fetch_candidates(target_date, max_events, status_filter)

    if not rows:
        logger.info("[BTC] 0 candidatos para %s — no se generan archivos.", target_date)
        return []

    # Filtrar eventos con al menos 1 odd 1X2
    candidates = [r for r in rows if r.get("odds_home") or r.get("odds_draw") or r.get("odds_away")]

    if not candidates:
        logger.info("[BTC] 0 eventos con odds 1X2 para %s.", target_date)
        return []

    total = len(candidates)
    n_batches = (total + batch_size - 1) // batch_size
    date_str = target_date.isoformat()
    generated: list[Path] = []

    for batch_idx in range(n_batches):
        start = batch_idx * batch_size
        batch = candidates[start : start + batch_size]
        ds_inputs = [_build_ds_input(ev) for ev in batch]

        fname = output_dir / f"candidates_{date_str}_exec_BT2_batch{batch_idx+1}of{n_batches}.json"
        fname.write_text(json.dumps(ds_inputs, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[BTC] Batch %d/%d → %s (%d eventos)", batch_idx+1, n_batches, fname.name, len(batch))
        generated.append(fname)

    logger.info("[BTC] Generados %d archivos | %d eventos totales", len(generated), total)
    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera candidatos BT2 en formato ds_input para el pipeline DSR.",
        epilog="""
Ejemplo de integración:
    python scripts/bt2_cdm/build_candidates.py --date 2024-08-17
    python jobs/deepseek_batches_to_telegram_payload_parts.py \\
      --input-glob "out/batches/candidates_2024-08-17_exec_BT2_batch*.json" \\
      --date 2024-08-17 --exec-id exec_BT2
""",
    )
    parser.add_argument("--date", required=True, help="Fecha YYYY-MM-DD a procesar")
    parser.add_argument("--output-dir", default="out/batches/", help="Directorio de salida")
    parser.add_argument("--max-events", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--status",
        default="scheduled",
        choices=["scheduled", "finished"],
        help="Filtro de status. Usar 'finished' para backtest con datos históricos.",
    )
    args = parser.parse_args()

    try:
        target = date.fromisoformat(args.date)
    except ValueError:
        logger.error("Formato de fecha inválido: %s (usa YYYY-MM-DD)", args.date)
        sys.exit(1)

    out_dir = Path(_repo_root) / args.output_dir
    paths = build_candidates(target, out_dir, args.max_events, args.batch_size, args.status)

    if paths:
        print(f"\nArchivos generados ({len(paths)}):")
        for p in paths:
            print(f"  {p}")
    else:
        print(f"\n0 candidatos para {target}.")
