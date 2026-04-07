import os
import sqlite3
from typing import Annotated, Generator, Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db.config import get_db_config
from db.db import connect

# ── V1 deps (no tocar) ────────────────────────────────────────────────────────

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

# ── BT2 Auth deps (Sprint 03) ─────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


def get_current_bt2_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Decodifica el Bearer JWT y retorna el user_id (str UUID).
    Lanza 401 si el token es inválido o expirado.
    Usar como: Depends(get_current_bt2_user)
    """
    from apps.api.bt2_auth import decode_jwt  # import diferido para evitar circular
    payload = decode_jwt(credentials.credentials)
    return str(payload["sub"])


Bt2UserId = Annotated[str, Depends(get_current_bt2_user)]
