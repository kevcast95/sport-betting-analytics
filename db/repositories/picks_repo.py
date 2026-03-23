import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from db.repositories.json_utils import dumps_json_stable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_selection(selection: Any) -> str:
    s = str(selection).strip().upper()
    if s in ("1", "X", "2"):
        return s
    # Alias defensivo (por si el input trae strings tipo "home/away")
    if s in ("HOME", "H", "HOME_WIN"):
        return "1"
    if s in ("AWAY", "A", "AWAY_WIN"):
        return "2"
    if s in ("DRAW", "D"):
        return "X"
    raise ValueError(f"selection inválida: {selection!r}")


def generate_idempotency_key(
    *,
    event_id: int,
    market: str,
    selection: str,
    picked_value: Optional[Any],
) -> str:
    """
    Estable por especificación:
      event_id + market + selection + (picked_value si existe)
    """
    sel = normalize_selection(selection)
    pv_part = ""
    if picked_value is not None:
        # str() preserva el formato del número tal como viene del JSON
        pv_part = str(picked_value)
    return f"{event_id}|{market}|{sel}|{pv_part}"


def insert_picks(
    conn: sqlite3.Connection,
    *,
    daily_run_id: int,
    picks: Iterable[Dict[str, Any]],
    created_at_utc: Optional[str] = None,
) -> None:
    created = created_at_utc or _utc_now_iso()
    rows = []
    for p in picks:
        event_id = int(p["event_id"])
        market = str(p["market"])
        selection = normalize_selection(p["selection"])
        picked_value = p.get("picked_value")
        odds_reference = p.get("odds_reference")
        odds_reference_text = dumps_json_stable(odds_reference) if odds_reference is not None else None
        idempotency_key = p["idempotency_key"]

        rows.append(
            (
                daily_run_id,
                event_id,
                market,
                selection,
                picked_value,
                odds_reference_text,
                "pending",
                created,
                idempotency_key,
            )
        )

    conn.executemany(
        """
        INSERT OR IGNORE INTO picks (
            daily_run_id, event_id, market, selection, picked_value,
            odds_reference, status, created_at_utc, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def fetch_pending_picks_without_results(
    conn: sqlite3.Connection,
    *,
    daily_run_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[sqlite3.Row]:
    """
    Picks:
    - status=pending
    - sin registro en pick_results
      o con pick_results.outcome='pending' (revalidación)
    """
    sql = """
        SELECT
            p.pick_id, p.daily_run_id, p.event_id, p.market, p.selection, p.picked_value, p.odds_reference,
            (pr.pick_id IS NOT NULL AND pr.outcome = 'pending') AS is_revalidation
        FROM picks p
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        WHERE p.status = 'pending' AND (pr.pick_id IS NULL OR pr.outcome = 'pending')
    """
    params: List[Any] = []
    if daily_run_id is not None:
        sql += " AND p.daily_run_id = ?"
        params.append(daily_run_id)
    sql += " ORDER BY p.created_at_utc ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    cur = conn.execute(sql, tuple(params))
    return cur.fetchall()


def set_pick_status(conn: sqlite3.Connection, *, pick_id: int, status: str) -> None:
    if status not in ("pending", "validated", "void"):
        raise ValueError(f"status inválido: {status}")
    conn.execute(
        "UPDATE picks SET status = ? WHERE pick_id = ?",
        (status, pick_id),
    )

