import os
import sqlite3
from typing import Annotated, Generator, Optional

from fastapi import Depends, Header, HTTPException

from db.config import get_db_config
from db.db import connect


def verify_local_api_key(
    x_local_api_key: Optional[str] = Header(None, alias="X-Local-Api-Key"),
) -> None:
    """Si WEB_API_KEY está definido, exige el mismo valor en el header (auth local opcional)."""
    expected = os.environ.get("WEB_API_KEY")
    if not expected:
        return
    if not x_local_api_key or x_local_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Local-Api-Key")


def get_conn() -> Generator[sqlite3.Connection, None, None]:
    cfg = get_db_config()
    conn = connect(cfg.path)
    try:
        yield conn
    finally:
        conn.close()


DbConn = Annotated[sqlite3.Connection, Depends(get_conn)]
