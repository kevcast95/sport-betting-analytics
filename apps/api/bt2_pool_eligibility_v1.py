"""
T-235–T-237 — Elegibilidad v1 del pool (Fase 0 §6) sin LLM.

Regla `pool-eligibility-f2-v1` (T-235–T-237 + T-258–T-262, DECISIONES_CIERRE_F2_S6_3_FINAL):
1. Fixture CDM utilizable (ids equipos, kickoff, nombres, `sportmonks_fixture_id`).
2. Cuotas válidas: al menos un mercado canónico completo (`event_passes_value_pool`).
3. **Oficial (N≥2):** `FT_1X2` completo + al menos una familia core adicional
   (`OU_GOALS_*`, `BTTS`, `DOUBLE_CHANCE_*`) con mercado completo (§4–5 F2).
4. ≥ N familias distintas (`market_diversity_family`) cuando N≥2 ya implicado por (3) si aplica;
   modo relajado N=1: sin exigencia core whitelist (solo observabilidad).
5. Tier **A** (5 ligas F2): `raw` obligatorio; **lineups** obligatorios si liga ∈ universo F2.
   Tier **Base**: `raw` ausente no bloquea solo; lineup no bloquea Base.
6. Faltantes críticos en `ds_input` según tier (§3).

Códigos de descarte = subset ACTA T-244 §4 (mismos literales).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

import psycopg2.errors
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, event_passes_value_pool
from apps.api.bt2_vault_market_mix import market_diversity_family

ELIGIBILITY_RULE_VERSION_V1 = "pool-eligibility-v1"
# T-260 / norma F2 — versión persistida en auditoría (sustituye v1 en jobs nuevos).
ELIGIBILITY_RULE_VERSION_F2 = "pool-eligibility-f2-v1"

# Referencia oficial de sprint (no se “apaga” con env; el env solo baja el umbral operativo).
POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63 = 2

_ENV_MIN_FAMILIES = "BT2_POOL_ELIGIBILITY_MIN_FAMILIES"
# T-261 — refuerzo Tier A: exigir lineups en ligas F2 (activar cuando cobertura SM estable).
_ENV_F2_TIER_A_LINEUPS = "BT2_F2_TIER_A_REQUIRE_LINEUPS"


def _tier_a_require_lineups() -> bool:
    v = (os.getenv(_ENV_F2_TIER_A_LINEUPS) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def pool_eligibility_min_families_from_env() -> int:
    """
    Umbral mínimo de familias de mercado distintas para pasar el chequeo
    `INSUFFICIENT_MARKET_FAMILIES`.

    - Default **2** = comportamiento canónico S6.3 (misma regla que antes de esta palanca).
    - **1** = relajación temporal de observabilidad (pruebas internas); requiere re-ejecutar
      el job de auditoría para materializar filas nuevas en `bt2_pool_eligibility_audit`.
    """
    raw = (os.getenv(_ENV_MIN_FAMILIES) or "").strip()
    if not raw:
        return POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63
    try:
        n = int(raw, 10)
    except ValueError:
        logger.warning(
            "%s=%r inválido; usando %s",
            _ENV_MIN_FAMILIES,
            raw,
            POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63,
        )
        return POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63
    if n < 1:
        logger.warning(
            "%s=%s < 1; usando 1",
            _ENV_MIN_FAMILIES,
            n,
        )
        return 1
    if n > 20:
        logger.warning(
            "%s=%s > 20; usando 20",
            _ENV_MIN_FAMILIES,
            n,
        )
        return 20
    return n


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


def _ds_input_critical_f2(
    *,
    fetch_errors: list[str],
    raw_fixture_missing: bool,
    pool_tier: str,
) -> bool:
    """Tier Base: raw ausente no bloquea solo. Tier A: raw ausente bloquea."""
    for err in fetch_errors or []:
        e = str(err).strip()
        if e in _DS_INPUT_CRITICAL_MARKERS:
            return True
    if (pool_tier or "").upper() == "A" and raw_fixture_missing:
        return True
    return False


def _f2_core_whitelist_satisfied(agg: AggregatedOdds) -> bool:
    """§4 F2: FT_1X2 completo + al menos una familia core adicional completa."""
    cov = agg.market_coverage or {}
    if not cov.get("FT_1X2"):
        return False
    for mc, ok in cov.items():
        if not ok:
            continue
        if mc.startswith("OU_GOALS") or mc == "BTTS" or mc.startswith("DOUBLE_CHANCE"):
            return True
    return False


def _causal_audit_class(reason_detail: Optional[str], primary: Optional[str]) -> str:
    """T-262 — matices §3 en JSON (no nuevos códigos ACTA)."""
    rd = (reason_detail or "").lower()
    if "tier_a_lineups" in rd:
        return "missing_temporal"
    if "normalization" in rd or "not_propagated" in rd:
        return "normalization_gap"
    if "source" in rd or "unsupported" in rd:
        return "source_unsupported"
    if primary == "MISSING_DS_INPUT_CRITICAL" and "raw" in rd:
        return "missing_temporal"
    return "not_required_tier"


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
    min_distinct_market_families: Optional[int] = None,
    league_id: Optional[int] = None,
    pool_tier: str = "BASE",
    f2_official_league_bt2_ids: Optional[set[int]] = None,
    lineups_ok: bool = False,
) -> PoolEligibilityResult:
    """
    Evaluación determinística; primer fallo define `primary_discard_reason`.

    `min_distinct_market_families`: si es None, se usa `pool_eligibility_min_families_from_env()`;
    tests y llamadas explícitas pueden fijar el umbral sin depender del entorno.

    T-259–T-261: `pool_tier` **A** = una de las 5 ligas F2; refuerzo raw/lineups.
    """
    min_fam = (
        pool_eligibility_min_families_from_env()
        if min_distinct_market_families is None
        else int(min_distinct_market_families)
    )
    if min_fam < 1:
        min_fam = 1

    f2_set = f2_official_league_bt2_ids or set()
    pt = (pool_tier or "BASE").upper()
    official_style = min_fam >= POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63

    d: dict[str, Any] = {
        "rule_version": ELIGIBILITY_RULE_VERSION_F2,
        "families_covered": sorted(_distinct_covered_families(agg)),
        "min_distinct_market_families_required": min_fam,
        "min_families_official_reference_s63": POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63,
        "pool_tier": pt,
        "league_id": league_id,
    }

    if sportmonks_fixture_id is None:
        d["reason_detail"] = "sportmonks_fixture_id_null"
        d["causal_audit_class"] = _causal_audit_class("sportmonks_fixture_id_null", "MISSING_FIXTURE_CORE")
        return PoolEligibilityResult(False, "MISSING_FIXTURE_CORE", d)

    if home_team_id is None or away_team_id is None:
        d["reason_detail"] = "missing_team_ids"
        d["causal_audit_class"] = _causal_audit_class("missing_team_ids", "MISSING_FIXTURE_CORE")
        return PoolEligibilityResult(False, "MISSING_FIXTURE_CORE", d)

    if kickoff_utc is None:
        d["reason_detail"] = "kickoff_utc_null"
        d["causal_audit_class"] = _causal_audit_class("kickoff_utc_null", "MISSING_FIXTURE_CORE")
        return PoolEligibilityResult(False, "MISSING_FIXTURE_CORE", d)

    if not _team_names_ok(home_team_name, away_team_name):
        d["reason_detail"] = "team_names_empty_or_unknown"
        d["causal_audit_class"] = _causal_audit_class(
            "team_names_empty_or_unknown", "MISSING_FIXTURE_CORE"
        )
        return PoolEligibilityResult(False, "MISSING_FIXTURE_CORE", d)

    if not event_passes_value_pool(agg):
        d["reason_detail"] = "no_complete_canonical_market_min_decimal"
        d["causal_audit_class"] = _causal_audit_class(
            "no_complete_canonical_market_min_decimal", "MISSING_VALID_ODDS"
        )
        return PoolEligibilityResult(False, "MISSING_VALID_ODDS", d)

    if official_style and not _f2_core_whitelist_satisfied(agg):
        d["reason_detail"] = "f2_requires_ft_1x2_plus_second_core_family"
        d["causal_audit_class"] = "source_unsupported"
        return PoolEligibilityResult(False, "INSUFFICIENT_MARKET_FAMILIES", d)

    fams = _distinct_covered_families(agg)
    d["families_covered"] = sorted(fams)
    if len(fams) < min_fam:
        d["reason_detail"] = f"distinct_market_families_lt_{min_fam}"
        d["causal_audit_class"] = "source_unsupported"
        return PoolEligibilityResult(False, "INSUFFICIENT_MARKET_FAMILIES", d)

    if (
        _tier_a_require_lineups()
        and pt == "A"
        and league_id is not None
        and int(league_id) in f2_set
        and not lineups_ok
    ):
        d["reason_detail"] = "f2_tier_a_lineups_required_stable_league"
        d["causal_audit_class"] = "missing_temporal"
        d["fetch_errors_sample"] = (ds_fetch_errors or [])[:12]
        return PoolEligibilityResult(False, "MISSING_DS_INPUT_CRITICAL", d)

    if _ds_input_critical_f2(
        fetch_errors=list(ds_fetch_errors),
        raw_fixture_missing=bool(raw_fixture_missing),
        pool_tier=pt,
    ):
        d["reason_detail"] = "raw_or_critical_fetch_errors_f2"
        d["causal_audit_class"] = _causal_audit_class("raw_tier_a_or_markers", "MISSING_DS_INPUT_CRITICAL")
        d["fetch_errors_sample"] = (ds_fetch_errors or [])[:12]
        return PoolEligibilityResult(False, "MISSING_DS_INPUT_CRITICAL", d)

    d["causal_audit_class"] = "not_required_tier"
    return PoolEligibilityResult(True, None, d)


def evaluate_pool_eligibility_v1_from_db(
    cur: _DbCursor,
    event_id: int,
    *,
    min_distinct_market_families: Optional[int] = None,
) -> Optional[PoolEligibilityResult]:
    """
    Carga evento + odds + `ds_input` vía builder; None si no existe `bt2_events.id`.
    """
    from apps.api.bt2_dsr_ds_input_builder import build_ds_input_item_from_db
    from apps.api.bt2_f2_league_constants import (
        f2_pool_tier_label,
        resolve_f2_official_league_bt2_ids,
    )

    built = build_ds_input_item_from_db(cur, event_id, selection_tier="A")
    if built is None:
        return None
    item, agg = built
    diag = item.get("diagnostics") or {}
    ctx = item.get("event_context") or {}
    lineups_ok = bool(diag.get("lineups_ok"))

    f2_ids = set(resolve_f2_official_league_bt2_ids(cur))

    cur.execute(
        """
        SELECT home_team_id, away_team_id, kickoff_utc, sportmonks_fixture_id, league_id
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
        lg_id = r.get("league_id")
    else:
        ht_id, at_id, ko, sm_fid = row[0], row[1], row[2], row[3]
        lg_id = row[4] if len(row) > 4 else None

    league_id = int(lg_id) if lg_id is not None else None
    tier = f2_pool_tier_label(league_id, f2_ids)
    raw_missing = bool(diag.get("raw_fixture_missing"))

    res = evaluate_pool_eligibility_v1(
        sportmonks_fixture_id=int(sm_fid) if sm_fid is not None else None,
        home_team_id=int(ht_id) if ht_id is not None else None,
        away_team_id=int(at_id) if at_id is not None else None,
        kickoff_utc=ko,
        home_team_name=str(ctx.get("home_team") or ""),
        away_team_name=str(ctx.get("away_team") or ""),
        agg=agg,
        ds_fetch_errors=list(diag.get("fetch_errors") or []),
        raw_fixture_missing=raw_missing,
        league_id=league_id,
        pool_tier=tier,
        f2_official_league_bt2_ids=f2_ids,
        lineups_ok=lineups_ok,
        min_distinct_market_families=min_distinct_market_families,
    )
    # Métricas F2 §6 (T-263): proxies raw/lineups en detail sin re-ejecutar el builder.
    if res is not None:
        res.detail["raw_fixture_missing"] = raw_missing
        res.detail["lineups_ok"] = lineups_ok
    return res


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
            ELIGIBILITY_RULE_VERSION_F2,
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
