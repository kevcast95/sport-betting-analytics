"""BT2 — línea SofaScore experimental (S6.5). No depende de SQLite V1 operativamente."""

from apps.api.bt2.providers.sofascore.client import SfsHttpClient
from apps.api.bt2.providers.sofascore.canonical_map import (
    CANONICAL_VERSION_S65,
    merge_canonical_rows,
    map_all_raw_to_rows,
    map_featured_raw_to_rows,
)

__all__ = [
    "SfsHttpClient",
    "CANONICAL_VERSION_S65",
    "map_featured_raw_to_rows",
    "map_all_raw_to_rows",
    "merge_canonical_rows",
]
