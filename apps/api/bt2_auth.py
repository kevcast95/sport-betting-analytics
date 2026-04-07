"""
BT2 Auth — Sprint 03 US-BE-006

Funciones de autenticación BT2: bcrypt hash, JWT create/decode.
NUNCA importar este módulo en apps/api/main.py.
Solo desde bt2_router.py y deps.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt as _bcrypt_lib
from fastapi import HTTPException, status
from jose import JWTError, jwt

from apps.api.bt2_settings import bt2_settings

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 7


def hash_password(plain: str) -> str:
    return _bcrypt_lib.hashpw(plain.encode("utf-8"), _bcrypt_lib.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_jwt(user_id: str, expires_days: int = _TOKEN_EXPIRE_DAYS) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=expires_days),
    }
    return jwt.encode(payload, bt2_settings.bt2_secret_key, algorithm=_ALGORITHM)


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, bt2_settings.bt2_secret_key, algorithms=[_ALGORITHM])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: sin sub",
            )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido o expirado: {exc}",
        ) from exc
