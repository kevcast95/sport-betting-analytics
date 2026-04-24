"""Sesión SQLAlchemy sync contra Postgres BT2 (staging/prod según .env)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[2]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.bt2_settings import bt2_settings


def _sync_database_url() -> str:
    """SQLAlchemy sync no puede usar driver asyncpg."""
    url = (os.environ.get("BT2_DATABASE_URL") or bt2_settings.bt2_database_url or "").strip()
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def make_session() -> Session:
    url = _sync_database_url()
    eng = create_engine(url, pool_pre_ping=True)
    return sessionmaker(bind=eng, expire_on_commit=False)()
