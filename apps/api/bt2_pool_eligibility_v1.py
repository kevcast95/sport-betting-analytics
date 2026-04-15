"""
T-235–T-237 — Elegibilidad v1 del pool (Fase 0 §6) sin LLM.

Regla `pool-eligibility-v1`:
1. Fixture CDM utilizable (ids equipos, kickoff, nombres, `sportmonks_fixture_id`).
2. Cuotas válidas: al menos un mercado canónico completo (`event_passes_value_pool`).
3. ≥ 2 familias de mercado con cobertura completa (`market_diversity_family`).
4. Sin faltantes críticos en trazas `ds_input` / builder (raw SportMonks mínimo).

Códigos de descarte = subset ACTA T-244 §4 (mismos literales).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

import psycopg2.errors
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, event_passes_value_pool
from apps.api.bt2_vault_market_mix import market_diversity_family

ELIGIBILITY_RULE_VERSION_V1 = "pool-eligibility-v1"

# Códigos canónicos v1 (ACTA T-244 §4 — solo los que aplica esta regla).
POOL_ELIGIBILITY_DISCARD_CODES_V1 = frozenset(
    {
        "MISSING_FIXTURE_CORE",
        "MISSING_VALID_ODDS",
        "INSUFFICIENT_MARKET_FAMILIES",
        "MISSING_DS_INPUT_CRITICAL",
    }
)

_DS_INPUT_CRITICAL_MARKERS = frozenset(
    {
        "lineups:no_raw_sportmonks_row",
        "lineups:no_sportmonks_fixture_id",
    }
)


@runtime_checkable
class _DbCursor(Protocol):
    def execute(self, query: str, params: Any = None) -> None: ...
    def fetchall(self) -> list[Any]: ...
    def fetchone(self) -> Any: ...


def assert_pool_eligibility_discard_code(code: Optional[str]) -> None:
    if code is None:
        return
    if code not in POOL_ELIGIBILITY_DISCARD_CODES_V1:
        raise ValueError(f"primary_discard_reason inválido para v1: {code!r}")


@dataclass
class PoolEligibilityResult:
    is_eligible: bool
    primary_discard_reason: Optional[str]
    detail: dict[str, Any] = field(default_factory=dict)


def _team_names_ok(home: str, away: str) -> bool:
    h, a = (home or "").strip(), (away or "").strip()
    if not h or not a:
        return False
    if h.lower() == "unknown" or a.lower() == "unknown":
        return False
    return True


def _distinct_covered_families(agg: AggregatedOdds) -> set[str]:
    fam: set[str] = set()
    for mc, ok in (agg.market_coverage or {}).items():
        if ok:
            fam.add(market_diversity_family(mc))
    return fam


def _ds_input_critical(
    *,
    fetch_errors: list[str],
    raw_fixture_missing: bool,
) -> bool:
    if raw_fixture_missing:
        return True
    for err in fetch_errors or []:
        e = str(err).strip()
        if e in _DS_INPUT_CRITICAL_MARKERS:
            return True
    return False


def evaluate_pool_eligibility_v1(
    *,
    sportmonks_fixture_id: Optional[int],
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    kickoff_utc: Optional[datetime],
    home_team_name: str,
    away_team_name: str,
    agg: AggregatedOdds,
    ds_fetch_errors: list[str],
    raw_fixture_missing: bool,
) -> PoolEligibilityResult:
    """
    Evaluación determinística; primer fallo define `primary_discard_reason`.
    """
    d: dict[str, Any] = {
        "rule_version": ELIGIBILITY_RULE_VERSION_V1,
        "families_covered": sorted(_distinct_covered_families(agg)),
    }

    if sportmonks_fixture_id is None:
        d["reason_detail"] = "sportmonks_fixture_id_null"
        return PoolEligibilityResult(
            False, "MISSING_FIXTURE_CORE", d
        )

    if home_team_id is None or away_team_id is None:
        d["reason_detail"] = "missing_team_ids"
        return PoolEligibilityResult(
            False, "MISSING_FIXTURE_CORE", d
        )

    if kickoff_utc is None:
        d["reason_detail"] = "kickoff_utc_null"
        return PoolEligibilityResult(
            False, "MISSING_FIXTURE_CORE", d
        )

    if not _team_names_ok(home_team_name, away_team_name):
        d["reason_detail"] = "team_names_empty_or_unknown"
        return PoolEligibilityResult(
            False, "MISSING_FIXTURE_CORE", d
        )

    if not event_passes_value_pool(agg):
        d["reason_detail"] = "no_complete_canonical_market_min_decimal"
        return PoolEligibilityResult(
            False, "MISSING_VALID_ODDS", d
        )

    fams = _distinct_covered_families(agg)
    d["families_covered"] = sorted(fams)
    if len(fams) < 2:
        d["reason_detail"] = "distinct_market_families_lt_2"
        return PoolEligibilityResult(
            False, "INSUFFICIENT_MARKET_FAMILIES", d
        )

    if _ds_input_critical(
        fetch_errors=list(ds_fetch_errors),
        raw_fixture_missing=bool(raw_fixture_missing),
    ):
        d["reason_detail"] = "raw_fixture_missing_or_critical_fetch_errors"
        d["fetch_errors_sample"] = (ds_fetch_errors or [])[:12]
        return PoolEligibilityResult(
            False, "MISSING_DS_INPUT_CRITICAL", d
        )

    return PoolEligibilityResult(True, None, d)


def evaluate_pool_eligibility_v1_from_db(
    cur: _DbCursor, event_id: int
) -> Optional[PoolEligibilityResult]:
    """
    Carga evento + odds + `ds_input` vía builder; None si no existe `bt2_events.id`.
    """
    from apps.api.bt2_dsr_ds_input_builder import build_ds_input_item_from_db

    built = build_ds_input_item_from_db(cur, event_id, selection_tier="A")
    if built is None:
        return None
    item, agg = built
    diag = item.get("diagnostics") or {}
    ctx = item.get("event_context") or {}

    cur.execute(
        """
        SELECT home_team_id, away_team_id, kickoff_utc, sportmonks_fixture_id
        FROM bt2_events WHERE id = %s
        """,
        (event_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, Mapping):
        r = dict(row)
        ht_id = r["home_team_id"]
        at_id = r["away_team_id"]
        ko = r["kickoff_utc"]
        sm_fid = r["sportmonks_fixture_id"]
    else:
        ht_id, at_id, ko, sm_fid = row[0], row[1], row[2], row[3]

    return evaluate_pool_eligibility_v1(
        sportmonks_fixture_id=int(sm_fid) if sm_fid is not None else None,
        home_team_id=int(ht_id) if ht_id is not None else None,
        away_team_id=int(at_id) if at_id is not None else None,
        kickoff_utc=ko,
        home_team_name=str(ctx.get("home_team") or ""),
        away_team_name=str(ctx.get("away_team") or ""),
        agg=agg,
        ds_fetch_errors=list(diag.get("fetch_errors") or []),
        raw_fixture_missing=bool(diag.get("raw_fixture_missing")),
    )


def insert_pool_eligibility_audit_row(
    cur: _DbCursor,
    *,
    event_id: int,
    result: PoolEligibilityResult,
) -> None:
    """T-236 — append-only audit row."""
    if result.primary_discard_reason:
        assert_pool_eligibility_discard_code(result.primary_discard_reason)
    cur.execute(
        """
        INSERT INTO bt2_pool_eligibility_audit (
            event_id,
            evaluated_at,
            eligibility_rule_version,
            is_eligible,
            primary_discard_reason,
            detail_json
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            event_id,
            datetime.now(timezone.utc),
            ELIGIBILITY_RULE_VERSION_V1,
            result.is_eligible,
            result.primary_discard_reason,
            Json(result.detail),
        ),
    )


def fetch_latest_eligibility_by_event_ids(
    cur: _DbCursor,
    event_ids: list[int],
) -> dict[int, tuple[bool, Optional[str]]]:
    """Última fila por evento (por `evaluated_at`)."""
    if not event_ids:
        return {}
    try:
        cur.execute(
            """
            SELECT DISTINCT ON (event_id)
                   event_id, is_eligible, primary_discard_reason
            FROM bt2_pool_eligibility_audit
            WHERE event_id = ANY(%s::int[])
            ORDER BY event_id, evaluated_at DESC
            """,
            (event_ids,),
        )
    except psycopg2.errors.UndefinedTable:
        cur.connection.rollback()
        logger.warning(
            "bt2_pool_eligibility_audit ausente: aplicar migraciones "
            "(p. ej. alembic upgrade head). Pool Fase 1 sin auditoría hasta entonces."
        )
        return {}
    out: dict[int, tuple[bool, Optional[str]]] = {}
    for row in cur.fetchall():
        r = (
            dict(row)
            if isinstance(row, Mapping)
            else {"event_id": row[0], "is_eligible": row[1], "primary_discard_reason": row[2]}
        )
        eid = int(r["event_id"])
        out[eid] = (bool(r["is_eligible"]), r.get("primary_discard_reason"))
    return out
