import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DBConfig:
    path: str


def get_db_config(db_path_arg: Optional[str] = None) -> DBConfig:
    """
    Resolución de ruta DB con prioridad:
      1) --db / arg explícito
      2) env DB_PATH
      3) default ./db/sport-tracker.sqlite3
    """
    default_path = os.path.join(os.path.dirname(__file__), "sport-tracker.sqlite3")
    path = db_path_arg or os.environ.get("DB_PATH") or default_path
    return DBConfig(path=os.path.abspath(path))

