#!/usr/bin/env python3
"""
Actualiza CDM desde SportMonks para los mismos candidatos que el replay admin
(GET /bt2/admin/analytics/backtest-replay): por día operativo America/Bogota,
eventos con kickoff en la ventana (ligas activas), hasta max_events_per_day * 3 IDs/día.

Correr **antes** del backtest en la UI si querés marcadores/status en `bt2_events`
alineados con SM y reducir falsos «pendiente» por CDM viejo.

**Por defecto** solo hace GET SportMonks para eventos **sin marcador CDM completo**
(`result_home` o `result_away` NULL), como el monitor «solo pendientes». Para forzar
refresco de todo el pool del replay (más cuota API): `--all-candidate-events`.

Ejemplo (últimos 7 días calendario Bogota como rango de días operativos):

    python scripts/bt2_cdm/refresh_cdm_sm_for_backtest_window.py \\
      --operating-day-from 2026-04-11 --operating-day-to 2026-04-18

Requiere `.env` en la raíz del repo con `BT2_DATABASE_URL` y `SPORTMONKS_API_KEY`.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2
import psycopg2.extras

from apps.api.bt2_admin_refresh_cdm_from_sm import (
    admin_refresh_cdm_from_sm_for_backtest_replay_window,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("refresh_cdm_sm_for_backtest_window")


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _db_conn():
    url = os.getenv("BT2_DATABASE_URL", "").replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )
    if not url.strip():
        raise SystemExit(
            "Falta BT2_DATABASE_URL en el entorno (.env en la raíz del repo)."
        )
    return psycopg2.connect(url)


def main() -> None:
    p = argparse.ArgumentParser(
        description="SM → raw → CDM para ventana backtest-replay (mismo pool que el replay)."
    )
    p.add_argument(
        "--operating-day-from",
        required=True,
        help="YYYY-MM-DD (inclusive, día operativo Bogota).",
    )
    p.add_argument(
        "--operating-day-to",
        required=True,
        help="YYYY-MM-DD (inclusive).",
    )
    p.add_argument(
        "--max-events-per-day",
        type=int,
        default=None,
        help=(
            "Debe coincidir con el backtest en UI (default: BT2_BACKTEST_MAX_EVENTS_PER_DAY "
            "o 20). El replay examina hasta este valor × 3 IDs candidatos por día."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Imprime el dict de respuesta en JSON.",
    )
    p.add_argument(
        "--all-candidate-events",
        action="store_true",
        help=(
            "Refrescar todos los event_ids del pool replay (sin filtrar por marcador pendiente). "
            "Por defecto el script solo actualiza filas sin result_home/result_away en CDM."
        ),
    )
    args = p.parse_args()

    try:
        d0 = date.fromisoformat(args.operating_day_from.strip())
        d1 = date.fromisoformat(args.operating_day_to.strip())
    except ValueError as e:
        raise SystemExit(f"Fechas inválidas (usar YYYY-MM-DD). {e}") from e

    if d0 > d1:
        raise SystemExit("operating-day-from no puede ser posterior a operating-day-to.")

    span = (d1 - d0).days + 1
    max_span = _env_int("BT2_BACKTEST_MAX_SPAN_DAYS", 31)
    if span > max_span:
        raise SystemExit(
            f"Rango de {span} días supera el máximo ({max_span}, env BT2_BACKTEST_MAX_SPAN_DAYS). "
            "Acortá el intervalo."
        )

    max_ev = args.max_events_per_day
    if max_ev is None:
        max_ev = _env_int("BT2_BACKTEST_MAX_EVENTS_PER_DAY", 20)

    api_key = (os.getenv("SPORTMONKS_API_KEY") or "").strip()
    if not api_key:
        logger.warning("SPORTMONKS_API_KEY vacío; el refresh fallará hasta que esté definida.")

    conn = _db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        raw = admin_refresh_cdm_from_sm_for_backtest_replay_window(
            cur,
            operating_day_key_from=args.operating_day_from.strip(),
            operating_day_key_to=args.operating_day_to.strip(),
            sportmonks_api_key=api_key,
            max_events_per_day=max_ev,
            only_pending_cdm=not bool(args.all_candidate_events),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    if args.json:
        print(json.dumps(raw, ensure_ascii=False, indent=2, default=str))
        return

    print(raw.get("message_es") or "")
    ok = raw.get("ok")
    logger.info(
        "ok=%s pool=%s pending_subset=%s only_pending_cdm=%s sm_fetch_ok=%s cdm_ok=%s",
        ok,
        raw.get("replay_pool_event_count"),
        raw.get("pending_cdm_event_count"),
        raw.get("only_pending_cdm"),
        raw.get("sm_fetch_ok"),
        raw.get("cdm_normalized_ok"),
    )
    notes = raw.get("notes") or []
    if notes:
        for n in notes[:40]:
            logger.warning("note: %s", n)
        if len(notes) > 40:
            logger.warning("… %s notas más", len(notes) - 40)

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
