import os
import sqlite3
from typing import Iterator
from contextlib import contextmanager


def connect(db_path: str) -> sqlite3.Connection:
    # timeout: espera antes de lanzar "database is locked" (otro proceso con la DB abierta en escritura).
    try:
        tsec = float(os.environ.get("SQLITE_CONNECT_TIMEOUT_SEC", "30"))
    except ValueError:
        tsec = 30.0
    tsec = max(1.0, min(tsec, 120.0))
    # check_same_thread=False: permite reutilizar la conexión en flujos async/secuenciales del proyecto
    conn = sqlite3.connect(db_path, timeout=tsec, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # busy_timeout en ms (complementa el timeout del connect)
    conn.execute("PRAGMA busy_timeout = 30000;")
    # WAL permite concurrente: lectores + escritor (muy útil si DB Browser está abierto)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    """
    Context manager de transacciones.
    - Hace commit al salir
    - Hace rollback si hay excepción
    """
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise

