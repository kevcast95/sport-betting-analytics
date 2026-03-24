"""
Genera hasta 2 combinaciones sugeridas (2 piernas c/u), sin repetir event_id dentro del combo.
Orden: confianza (Alta > Media-Alta > Media > Baja) y luego cuota descendente.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

CONF_RANK = {
    "Alta": 4,
    "Media-Alta": 3,
    "Media": 2,
    "Baja": 1,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_odds_ref(raw: Optional[str]) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _confidence_rank(odds_ref_parsed: Any) -> int:
    if not isinstance(odds_ref_parsed, dict):
        return 0
    key = str(odds_ref_parsed.get("confianza") or "").strip()
    return int(CONF_RANK.get(key, 0))


def _sort_key(row: sqlite3.Row) -> Tuple[int, float, int]:
    ref = _parse_odds_ref(row["odds_reference"])
    conf = _confidence_rank(ref)
    pv = row["picked_value"]
    odds = float(pv) if pv is not None else 0.0
    return (-conf, -odds, -int(row["pick_id"]))


def _first_pair(rows: List[sqlite3.Row]) -> Optional[List[int]]:
    if len(rows) < 2:
        return None
    a = rows[0]
    aid = int(a["pick_id"])
    ae = int(a["event_id"])
    for b in rows[1:]:
        if int(b["event_id"]) != ae:
            return [aid, int(b["pick_id"])]
    return None


def _remaining_after_pair(
    rows: List[sqlite3.Row], pair_ids: List[int]
) -> List[sqlite3.Row]:
    ps = set(pair_ids)
    return [r for r in rows if int(r["pick_id"]) not in ps]


def regenerate_suggested_combos(conn: sqlite3.Connection, *, daily_run_id: int) -> List[int]:
    """
    Borra combos previos del run e inserta hasta 2 nuevos (rank 1 y 2).
    Retorna lista de suggested_combo_id creados.
    """
    cur = conn.execute(
        "SELECT pick_id, event_id, picked_value, odds_reference FROM picks WHERE daily_run_id = ?",
        (daily_run_id,),
    )
    rows = list(cur.fetchall())
    if not rows:
        return []

    rows.sort(key=_sort_key)

    combos: List[List[int]] = []
    first = _first_pair(rows)
    if first:
        combos.append(first)
        rest = _remaining_after_pair(rows, first)
        second = _first_pair(rest)
        if second:
            combos.append(second)

    conn.execute(
        "DELETE FROM suggested_combos WHERE daily_run_id = ?",
        (daily_run_id,),
    )

    created: List[int] = []
    for rank, legs in enumerate(combos, start=1):
        note = (
            "Greedy por confianza+cuota; piernas en distintos event_id; "
            f"máx 2 combos diarios (rank {rank})."
        )
        cur2 = conn.execute(
            """
            INSERT INTO suggested_combos (daily_run_id, rank_order, created_at_utc, strategy_note)
            VALUES (?, ?, ?, ?)
            """,
            (daily_run_id, rank, _utc_now_iso(), note),
        )
        cid = int(cur2.lastrowid)
        for order, pid in enumerate(legs, start=1):
            conn.execute(
                """
                INSERT INTO suggested_combo_legs (suggested_combo_id, pick_id, leg_order)
                VALUES (?, ?, ?)
                """,
                (cid, pid, order),
            )
        created.append(cid)
    return created


def list_suggested_combos_with_legs(
    conn: sqlite3.Connection, *, daily_run_id: int
) -> List[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT suggested_combo_id, daily_run_id, rank_order, created_at_utc, strategy_note
        FROM suggested_combos
        WHERE daily_run_id = ?
        ORDER BY rank_order ASC
        """,
        (daily_run_id,),
    )
    return cur.fetchall()


def list_legs_for_combo(conn: sqlite3.Connection, *, suggested_combo_id: int) -> List[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT l.pick_id, l.leg_order, p.event_id, p.market, p.selection
        FROM suggested_combo_legs l
        JOIN picks p ON p.pick_id = l.pick_id
        WHERE l.suggested_combo_id = ?
        ORDER BY l.leg_order ASC
        """,
        (suggested_combo_id,),
    )
    return cur.fetchall()
