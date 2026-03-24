#!/usr/bin/env python3
"""Genera hasta 2 combinaciones sugeridas para un daily_run (misma lógica que la API)."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.config import get_db_config  # noqa: E402
from db.db import connect  # noqa: E402
from db.init_db import init_db  # noqa: E402
from db.repositories.suggest_combos_repo import regenerate_suggested_combos  # noqa: E402
from db.repositories.tracking_repo import ensure_pick_baselines_for_run  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--daily-run-id", type=int, required=True)
    p.add_argument("--db", default=None)
    p.add_argument("--skip-baselines", action="store_true")
    args = p.parse_args()
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)
    if not args.skip_baselines:
        ensure_pick_baselines_for_run(conn, daily_run_id=args.daily_run_id)
    ids = regenerate_suggested_combos(conn, daily_run_id=args.daily_run_id)
    conn.commit()
    print("suggested_combo_ids:", ids)


if __name__ == "__main__":
    main()
