"""
D-06-068 §6 — normalización de etiquetas home/away para matching SM ↔ SofaScore.

Usado por runbook `docs/bettracker2/runbooks/bt2_f3_sm_intraday_observation_d06_068.md`
y por jobs de benchmark (T-283, T-284). No forma parte del pipeline productivo CDM/BT2.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_benchmark_team_name(label: str | None) -> str:
    """
    Devuelve una clave estable en minúsculas para comparar nombres de clubes entre proveedores.
    """
    if label is None:
        return ""
    s = unicodedata.normalize("NFKC", str(label)).strip().lower()
    s = "".join(
        ch
        for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()
