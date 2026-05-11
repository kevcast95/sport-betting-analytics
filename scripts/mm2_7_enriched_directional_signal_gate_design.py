#!/usr/bin/env python3
"""
MM-2.7 Enriched Directional Signal Gate Design (artifact-only).

Lee artefactos MM-2.6R.3, inventaria datos enriched por fixture, define gates
candidatos, evalúa reglas conservadoras sobre el universo MM-2.6R, audita
disponibilidad DB para modelo de importancia v0 (SELECT-only, sin writes),
emite contrato v2, validator v3 y readiness — sin DSR, APIs, TOA ni escrituras.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "scripts" / "outputs"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"

PACKAGES_IN = OUT / "mm2_6r3_enriched_stage1_packages_guardrail_v2.json"
RETRY_IN = OUT / "mm2_6r3_retry_readiness.json"
VALIDATION_CSV_IN = OUT / "mm2_6r3_guardrail_v2_validation_rows.csv"
BEFORE_AFTER_IN = OUT / "mm2_6r3_before_after_guardrail_diff.csv"
POLICY_IN = OUT / "mm2_6r2_enriched_adapter_policy_v2.json"
VALIDATOR_V2_IN = OUT / "mm2_6r2_validator_v2_rules.json"
ENRICHED_BLOCKS_IN = OUT / "mm2_6r_enriched_context_blocks.json"
BASE_BLOCKS_IN = OUT / "mm2_6r_base_context_blocks.json"
FIXTURE_ROWS_IN = OUT / "mm2_6r_fixture_rows.csv"
LEAKAGE_CSV_IN = OUT / "mm2_6r_stage1_leakage_audit.csv"

INVENTORY_CSV_OUT = OUT / "mm2_7_enriched_data_inventory.csv"
GATE_DEFS_OUT = OUT / "mm2_7_candidate_gate_definitions.json"
PLAYER_MODEL_OUT = OUT / "mm2_7_player_importance_model_v0_design.json"
PLAYER_AVAIL_CSV_OUT = OUT / "mm2_7_player_importance_data_availability.csv"
SEVERE_RULE_OUT = OUT / "mm2_7_severe_absence_imbalance_rule_design.json"
GATE_ROWS_OUT = OUT / "mm2_7_gate_application_rows.csv"
PREVIEW_OUT = OUT / "mm2_7_enriched_directional_signals_preview.json"
CONTRACT_OUT = OUT / "mm2_7_enriched_directional_signal_contract_v2.json"
VALIDATOR_V3_OUT = OUT / "mm2_7_validator_v3_rules.json"
READINESS_OUT = OUT / "mm2_7_enriched_signal_gate_readiness.json"
AUDIT_OUT = AUDITS / "MM2_7_ENRICHED_DIRECTIONAL_SIGNAL_GATE_DESIGN_AUDIT.md"

MARKETS = ("FT_1X2", "OU_GOALS_2_5")


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def dsn_from_settings() -> str | None:
    try:
        from apps.api.bt2_settings import bt2_settings

        u = bt2_settings.bt2_database_url
        return u.replace("postgresql+asyncpg://", "postgresql://", 1)
    except Exception:
        return None


def db_probe_player_importance_inputs() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """SELECT-only: tablas/columnas relevantes y muestra de payload SM (fixture_id fijo si existe)."""
    meta: dict[str, Any] = {
        "connected": False,
        "error": None,
        "tables_like": [],
        "payload_keys_sample": None,
    }
    rows: list[dict[str, Any]] = []

    dsn = dsn_from_settings()
    if not dsn:
        meta["error"] = "bt2_settings unavailable"
        return _default_player_availability_rows("not_available", meta["error"]), meta

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as e:
        meta["error"] = f"psycopg2: {e}"
        return _default_player_availability_rows("not_available", meta["error"]), meta

    try:
        conn = psycopg2.connect(dsn, connect_timeout=8)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        meta["connected"] = True
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND (
                table_name ILIKE '%player%'
                OR table_name ILIKE '%squad%'
                OR table_name ILIKE '%statistic%'
                OR table_name ILIKE '%lineup%'
                OR table_name ILIKE '%sportmonks%'
              )
            ORDER BY table_name
            """
        )
        meta["tables_like"] = [r["table_name"] for r in cur.fetchall()]

        cur.execute(
            "SELECT fixture_id, payload FROM raw_sportmonks_fixtures ORDER BY fixture_id DESC LIMIT 1"
        )
        one = cur.fetchone()
        if one and one.get("payload"):
            p = one["payload"]
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except json.JSONDecodeError:
                    p = {}
            keys = list(p.keys())[:40] if isinstance(p, dict) else []
            nested = {}
            if isinstance(p, dict):
                for k in ("lineups", "sidelined", "statistics", "formations", "weather"):
                    if k in p:
                        v = p[k]
                        nested[k] = type(v).__name__
            meta["payload_keys_sample"] = {"top_level_keys": keys, "typed_children": nested}

        cur.close()
        conn.close()
    except Exception as e:
        meta["error"] = str(e)
        return _default_player_availability_rows("not_available", meta["error"]), meta

    # Clasificación por feature (heurística + tablas)
    tbl = set(meta["tables_like"])
    raw_sm = "raw_sportmonks_fixtures" in tbl

    def row(
        feature: str,
        cls: str,
        notes: str,
    ) -> dict[str, Any]:
        return {
            "feature_id": feature,
            "classification": cls,
            "notes": notes,
            "evidence": "information_schema + optional raw_sportmonks_fixtures.payload sample",
        }

    rows.append(
        row(
            "minutes_share",
            "available_in_raw_only" if raw_sm else "needs_provider",
            "En relacional BT2 no hay tabla dedicada; típicamente derivable de históricos SM u otro proveedor con minutos por partido pre-kickoff.",
        )
    )
    rows.append(
        row(
            "starter_frequency",
            "available_in_raw_only" if raw_sm else "needs_provider",
            "Aproximable desde apariciones en lineups listados en payloads históricos; requiere pipeline y timestamp gate.",
        )
    )
    rows.append(
        row(
            "recent_starts",
            "available_in_raw_only" if raw_sm else "needs_provider",
            "Misma fuente que lineups/squad en raw JSON o endpoint histórico.",
        )
    )
    rows.append(
        row(
            "goals_assists_cards",
            "available_in_raw_only" if raw_sm else "needs_provider",
            "Stats de jugador en temporada: no expuestas en tablas bt2_* actuales; posible en payload SM o agregados externos.",
        )
    )
    rows.append(
        row(
            "position",
            "available_now",
            "Presente en artefactos MM-2.6R (position_counts / absences_by_position).",
        )
    )
    rows.append(
        row(
            "goalkeeper_flag",
            "available_now",
            "Inferible por posición en mismos bloques.",
        )
    )
    rows.append(
        row(
            "team_contribution",
            "not_available",
            "Sin modelo ni tablas agregadas de xG/contribución por jugador en BT2 relacional.",
        )
    )
    rows.append(
        row(
            "provider_rating_prematch_safe",
            "unsafe_or_unknown_timestamp",
            "Rating proveedor sin política explícita de as_of por snapshot → no usar en v0 productivo.",
        )
    )
    rows.append(
        row(
            "historical_player_stats_before_kickoff",
            "available_in_raw_only" if raw_sm else "needs_provider",
            "Requiere extracción desde raw_sportmonks_fixtures u otros raw stores con ventana temporal validada.",
        )
    )
    return rows, meta


def _default_player_availability_rows(cls: str, err: str) -> list[dict[str, Any]]:
    feats = [
        "minutes_share",
        "starter_frequency",
        "recent_starts",
        "goals_assists_cards",
        "position",
        "goalkeeper_flag",
        "team_contribution",
        "provider_rating_prematch_safe",
        "historical_player_stats_before_kickoff",
    ]
    return [
        {
            "feature_id": f,
            "classification": cls,
            "notes": err,
            "evidence": "fallback_no_db",
        }
        for f in feats
    ]


def default_signal(
    block: str,
    market: str,
    *,
    direction: str = "unknown",
    strength: str = "none",
    allowed: bool = False,
    rule_id: str = "default_no_directional_enriched_signal",
    reason: str = "",
    evidence_fields: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "block": block,
        "market_canonical": market,
        "direction": direction,
        "strength": strength,
        "allowed_in_signal_summary": allowed,
        "rule_id": rule_id,
        "evidence_fields": evidence_fields or [],
        "reason": reason,
        "limitations": limitations or [],
    }


def eval_weather_gate(desc: dict[str, Any], market: str) -> dict[str, Any]:
    tg = desc.get("timestamp_gate") or {}
    w = desc.get("weather") or {}
    if not tg.get("safe_gate_pass"):
        return default_signal(
            "weather",
            market,
            reason="timestamp_gate.safe_gate_pass is false; no weather directional signal.",
            evidence_fields=["enriched_descriptive_context.timestamp_gate.safe_gate_pass"],
        )
    if w.get("extreme_weather_flag") is True and market == "OU_GOALS_2_5":
        return default_signal(
            "weather",
            market,
            direction="under_2_5",
            strength="weak",
            allowed=True,
            rule_id="weather_extreme_under_weak_v1",
            reason="extreme_weather_flag true; conservative weak under on OU_GOALS_2_5.",
            evidence_fields=[
                "enriched_descriptive_context.weather.extreme_weather_flag",
                "enriched_descriptive_context.timestamp_gate.safe_gate_pass",
            ],
            limitations=[
                "No validación histórica de calibración del flag extremo en esta corrida.",
                "FT_1X2 no emite dirección desde weather en v1 de esta regla.",
            ],
        )
    return default_signal(
        "weather",
        market,
        reason="extreme_weather_flag is false or market is not OU_GOALS_2_5; descriptive only.",
        evidence_fields=["enriched_descriptive_context.weather.extreme_weather_flag"],
    )


def eval_lineup_gate(desc: dict[str, Any], market: str) -> dict[str, Any]:
    lu = desc.get("lineups") or {}
    cs = lu.get("confirmed_status")
    if cs != "confirmed":
        return default_signal(
            "lineup",
            market,
            reason="confirmed_status != confirmed; lineups descriptive only.",
            evidence_fields=["enriched_descriptive_context.lineups.confirmed_status"],
        )
    return default_signal(
        "lineup",
        market,
        reason="confirmed XI present but no lineup_strength_delta nor player_importance_model nor rotation_detection in BT2 v0.",
        evidence_fields=["enriched_descriptive_context.lineups.confirmed_status"],
        limitations=["Requires lineup_strength_delta or player importance v1+ or rotation rules."],
    )


def eval_formation_gate(desc: dict[str, Any], market: str) -> dict[str, Any]:
    return default_signal(
        "formation",
        market,
        reason="Formations default descriptive; no validated tactical edge rule.",
        evidence_fields=["enriched_descriptive_context.formations.formation_available"],
    )


def eval_venue_gate(desc: dict[str, Any], market: str) -> dict[str, Any]:
    w = desc.get("weather") or {}
    return default_signal(
        "venue",
        market,
        reason="Venue metadata is descriptive only (artifact-only gate design).",
        evidence_fields=[
            "enriched_descriptive_context.weather.venue_name",
            "enriched_descriptive_context.weather.surface",
        ],
        limitations=["No directional venue_signal in MM-2.7 v0."],
    )


def eval_availability_gate_mm27(
    desc: dict[str, Any], market: str, rule_params: dict[str, Any]
) -> dict[str, Any]:
    """
    Regla conservadora MM-2.7 (candidate_only sin validación histórica):
    - Solo FT_1X2.
    - unknown_count == 0 en ambos equipos.
    - absence_count_diff = |injury_count+suspension_count home - away| >= min_diff
    - Equipo con más typed absences tiene max(GK,DEF,ATT) >= min_line desde absences_by_position.
    - timestamp safe.
    """
    tg = desc.get("timestamp_gate") or {}
    if not tg.get("safe_gate_pass"):
        return default_signal(
            "availability",
            market,
            reason="timestamp_gate not safe; no availability directional signal.",
            evidence_fields=["enriched_descriptive_context.timestamp_gate.safe_gate_pass"],
        )
    if market != "FT_1X2":
        return default_signal(
            "availability",
            market,
            reason="availability directional candidate (MM-2.7) scoped to FT_1X2 only in v0.",
        )

    av = desc.get("availability") or {}
    hc = av.get("home_counts") or {}
    ac = av.get("away_counts") or {}
    if (hc.get("unknown_count") or 0) > 0 or (ac.get("unknown_count") or 0) > 0:
        return default_signal(
            "availability",
            market,
            reason="unknown absence types present; conservative gate blocks directional signal.",
            evidence_fields=[
                "enriched_descriptive_context.availability.home_counts.unknown_count",
                "enriched_descriptive_context.availability.away_counts.unknown_count",
            ],
        )

    th = int(hc.get("injury_count") or 0) + int(hc.get("suspension_count") or 0)
    ta = int(ac.get("injury_count") or 0) + int(ac.get("suspension_count") or 0)
    diff = abs(th - ta)
    min_diff = int(rule_params.get("absence_count_diff_min", 4))
    min_line = int(rule_params.get("min_absences_same_critical_line", 2))

    byp = av.get("absences_by_position") or {}
    home_lines = byp.get("home") or {}
    away_lines = byp.get("away") or {}

    def max_line(d: dict[str, Any]) -> int:
        return max(
            int(d.get("goalkeeper") or 0),
            int(d.get("defender") or 0),
            int(d.get("attacker") or 0),
        )

    worse_is_home = th > ta
    worse_is_away = ta > th
    if th == ta:
        return default_signal(
            "availability",
            market,
            reason="typed injury+suspension counts tied; no imbalance.",
            evidence_fields=["enriched_descriptive_context.availability.home_counts.injury_count"],
        )

    if diff < min_diff:
        return default_signal(
            "availability",
            market,
            reason=f"absence_count_diff={diff} < required {min_diff} (injury+suspension typed).",
            evidence_fields=[
                "enriched_descriptive_context.availability.home_counts.injury_count",
                "enriched_descriptive_context.availability.away_counts.injury_count",
            ],
        )

    worse_lines = home_lines if worse_is_home else away_lines
    if max_line(worse_lines) < min_line:
        return default_signal(
            "availability",
            market,
            reason=f"worse side lacks >= {min_line} absences in any critical line (GK/DEF/ATT).",
            evidence_fields=["enriched_descriptive_context.availability.absences_by_position"],
        )

    direction = "away" if worse_is_home else "home"
    return default_signal(
        "availability",
        market,
        direction=direction,
        strength="weak",
        allowed=True,
        rule_id="severe_absence_imbalance_typed_ft1x2_weak_v0_candidate",
        reason=(
            f"Typed injury+susp imbalance diff={diff} (min {min_diff}); worse side max critical line "
            f"absences={max_line(worse_lines)} (min {min_line}); favor opponent ({direction})."
        ),
        evidence_fields=[
            "enriched_descriptive_context.availability.home_counts.injury_count",
            "enriched_descriptive_context.availability.home_counts.suspension_count",
            "enriched_descriptive_context.availability.away_counts.injury_count",
            "enriched_descriptive_context.availability.away_counts.suspension_count",
            "enriched_descriptive_context.availability.absences_by_position",
            "enriched_descriptive_context.timestamp_gate.safe_gate_pass",
        ],
        limitations=[
            "candidate_only: sin validación histórica de poder predictivo.",
            "Sin player_importance: no se identifican 'key players', solo conteos por línea.",
        ],
    )


def build_inventory_row(pkg: dict[str, Any]) -> dict[str, Any]:
    ec = pkg.get("event_context") or {}
    fid = ec.get("fixture_id")
    desc = pkg.get("enriched_descriptive_context") or {}
    tg = desc.get("timestamp_gate") or {}
    lu = desc.get("lineups") or {}
    av = desc.get("availability") or {}
    fm = desc.get("formations") or {}
    w = desc.get("weather") or {}
    bb = pkg.get("blocked_blocks") or {}

    ac_s = json.dumps(av.get("absence_types_summary") or {}, ensure_ascii=False)
    return {
        "fixture_id": fid,
        "lineups_available": lu.get("available"),
        "confirmed_status": lu.get("confirmed_status"),
        "home_listed_lineup_count": lu.get("home_listed_lineup_count"),
        "away_listed_lineup_count": lu.get("away_listed_lineup_count"),
        "formation_available": fm.get("formation_available"),
        "home_formation": fm.get("home_formation"),
        "away_formation": fm.get("away_formation"),
        "formation_family_home": fm.get("formation_family_home"),
        "formation_family_away": fm.get("formation_family_away"),
        "home_sidelined_count": (av.get("home_counts") or {}).get("sidelined_count"),
        "away_sidelined_count": (av.get("away_counts") or {}).get("sidelined_count"),
        "home_unknown_count": (av.get("home_counts") or {}).get("unknown_count"),
        "away_unknown_count": (av.get("away_counts") or {}).get("unknown_count"),
        "absence_types_summary_json": ac_s,
        "absences_by_position_json": json.dumps(av.get("absences_by_position") or {}, ensure_ascii=False),
        "weather_available": w.get("available"),
        "weather_description": w.get("weather_description"),
        "temperature": w.get("temperature"),
        "wind_speed": w.get("wind_speed"),
        "rain_or_snow_flag": w.get("rain_or_snow_flag"),
        "extreme_weather_flag": w.get("extreme_weather_flag"),
        "venue_name": w.get("venue_name"),
        "surface": w.get("surface"),
        "timestamp_gate_safe": tg.get("safe_gate_pass"),
        "timestamp_fetched_before_kickoff": tg.get("fetched_before_kickoff"),
        "blocked_blocks_excluded_group_count": bb.get("excluded_group_count"),
        "blocked_blocks_policy": bb.get("policy"),
    }


def is_valid_directional(sig: dict[str, Any]) -> bool:
    return (
        sig.get("direction") not in (None, "", "unknown")
        and sig.get("strength") not in (None, "", "none")
        and sig.get("allowed_in_signal_summary") is True
        and bool(sig.get("rule_id"))
        and sig.get("rule_id") != "default_no_directional_enriched_signal"
        and bool(sig.get("evidence_fields"))
    )


def build_candidate_gate_definitions(rule_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(),
        "artifact_only": True,
        "gate_decision_matrix": {
            "rows": ["weather", "availability", "lineup", "formation", "venue"],
            "columns": ["preconditions", "markets_allowed", "max_strength", "signal_summary_allowed_when_met"],
            "cells": [
                {
                    "gate": "weather_signal_gate",
                    "preconditions": ["timestamp_gate.safe_gate_pass", "extreme_weather_flag==true"],
                    "markets_directional": ["OU_GOALS_2_5"],
                    "max_strength": "weak",
                    "signal_summary_allowed_when_met": True,
                    "rule_id": "weather_extreme_under_weak_v1",
                },
                {
                    "gate": "availability_signal_gate",
                    "preconditions": [
                        "no unknown_count on either side",
                        "typed injury+suspension imbalance",
                        "critical line cluster on worse side",
                        "timestamp safe",
                    ],
                    "markets_directional": ["FT_1X2"],
                    "max_strength": "weak",
                    "signal_summary_allowed_when_met": True,
                    "rule_id": "severe_absence_imbalance_typed_ft1x2_weak_v0_candidate",
                    "params": rule_params,
                },
                {
                    "gate": "lineup_signal_gate",
                    "preconditions": ["confirmed_status==confirmed", "lineup_strength_delta OR player_importance OR rotation"],
                    "markets_directional": ["FT_1X2", "OU_GOALS_2_5"],
                    "max_strength": "TBD",
                    "signal_summary_allowed_when_met": "only with explicit future rules",
                },
                {
                    "gate": "formation_signal_gate",
                    "preconditions": ["explicit validated tactical rule (future)"],
                    "markets_directional": [],
                    "max_strength": "none",
                    "default": "descriptive_only",
                },
                {
                    "gate": "venue_signal_gate",
                    "preconditions": [],
                    "markets_directional": [],
                    "default": "descriptive_only_no_direction",
                },
            ],
        },
        "gates": {
            "weather_signal_gate": {
                "true_extreme_weather": {
                    "market_canonical": "OU_GOALS_2_5",
                    "direction": "under_2_5",
                    "strength": "weak",
                    "allowed_in_signal_summary": True,
                    "rule_id": "weather_extreme_under_weak_v1",
                },
                "not_extreme": {
                    "direction": "unknown",
                    "strength": "none",
                    "allowed_in_signal_summary": False,
                },
            },
            "availability_signal_gate": {
                "note": "Sin player importance: solo conteos y líneas críticas; regla MM-2.7 en severe_absence_imbalance_rule_design.json",
            },
            "lineup_signal_gate": {
                "unconfirmed": {
                    "direction": "unknown",
                    "strength": "none",
                    "allowed_in_signal_summary": False,
                },
                "confirmed_requires": ["lineup_strength_delta", "player_importance_model", "rotation_detection"],
            },
            "formation_signal_gate": {"default": "descriptive_only"},
            "venue_signal_gate": {"default": "descriptive_only"},
        },
    }


def build_severe_rule_design(rule_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": "severe_absence_imbalance_typed_ft1x2_weak_v0_candidate",
        "status": "candidate_only",
        "markets": ["FT_1X2"],
        "max_strength": "weak",
        "definition": {
            "typed_absence_numerator_home": "injury_count + suspension_count",
            "typed_absence_numerator_away": "injury_count + suspension_count",
            "absence_count_diff": "abs(home_typed - away_typed)",
            "absence_count_diff_min": rule_params.get("absence_count_diff_min", 4),
            "critical_lines": ["goalkeeper", "defender", "attacker"],
            "worse_side_critical_line_min": rule_params.get("min_absences_same_critical_line", 2),
            "unknown_absence_exclusion": "home_counts.unknown_count==0 AND away_counts.unknown_count==0",
            "timestamp_gate": "safe_gate_pass==true",
            "direction_mapping": "favor opponent of worse typed-absence side: home worse -> away; away worse -> home",
        },
        "limitations": [
            "No validación histórica en MM-2.7.",
            "No player importance; no lenguaje de key player.",
            "No implica edge ni poder predictivo.",
        ],
    }


def build_player_model_v0() -> dict[str, Any]:
    return {
        "model_id": "player_importance_v0_design_only",
        "purpose": "Evitar inferencia implícita de 'key absence' con señales auditables.",
        "proposed_inputs": [
            {"id": "minutes_share", "description": "minutos jugados / minutos posibles en ventana pre-partido."},
            {"id": "starter_frequency", "description": "frecuencia de titularidad en últimos N partidos pre-kickoff."},
            {"id": "recent_starts", "description": "conteo de titularidades recientes antes del target."},
            {"id": "goals", "description": "goles acumulados temporada-to-date pre-kickoff."},
            {"id": "assists", "description": "asistencias idem."},
            {"id": "cards_suspensions", "description": "amarillas/rojas y suspensiones acumuladas."},
            {"id": "position", "description": "GK/DEF/MID/FW para ponderar línea crítica."},
            {"id": "goalkeeper_flag", "description": "binario para reglas de línea crítica."},
            {"id": "team_contribution", "description": "share de xG/xA o métricas de equipo (si proveedor y timestamp-safe)."},
            {
                "id": "provider_rating",
                "description": "solo si as_of confirmado pre-match y política de freshness.",
            },
            {
                "id": "historical_player_stats",
                "description": "stats agregados estrictamente anteriores al kickoff del fixture objetivo.",
            },
        ],
        "v0_output_sketch": {
            "importance_score_0_1": "normalizado por posición/liga",
            "tier": "A|B|C|unknown",
            "emit_only_with_min_sample": True,
        },
        "non_goals": ["No inventar importancia desde nombres o narrativa.", "No usar stats del fixture objetivo."],
    }


def build_validator_v3() -> dict[str, Any]:
    v2 = read_json(VALIDATOR_V2_IN, {})
    v2_rules = v2.get("rules") or []
    extra = [
        {
            "id": "reject_key_player_language_without_importance_model",
            "severity": "reject",
            "description": "DSR menciona key player / jugador clave sin player_importance_model activo y señal availability permitida.",
            "condition": "player_importance_model_active == false OR availability_signal references forbid key language",
        },
        {
            "id": "reject_confirmed_lineup_language_when_unconfirmed",
            "severity": "reject",
            "description": "DSR afirma alineación confirmada cuando enriched_descriptive_context.lineups.confirmed_status != confirmed.",
            "condition": "confirmed_status != 'confirmed'",
        },
        {
            "id": "reject_absence_signal_when_gate_disallows",
            "severity": "reject",
            "description": "DSR usa conteos de ausencia como señal cuando availability_signal.allowed_in_signal_summary=false.",
            "condition": "availability_signal.allowed_in_signal_summary == false",
        },
        {
            "id": "reject_formation_edge_when_gate_disallows",
            "severity": "reject",
            "description": "DSR usa formación como ventaja táctica cuando formation_signal.allowed_in_signal_summary=false.",
            "condition": "formation_signal.allowed_in_signal_summary == false",
        },
        {
            "id": "reject_weather_ou_when_gate_disallows",
            "severity": "reject",
            "description": "DSR usa clima para over/under cuando weather_signal.allowed_in_signal_summary=false.",
            "condition": "weather_signal.allowed_in_signal_summary == false",
        },
        {
            "id": "reject_stage1_odds_benchmark_board",
            "severity": "reject",
            "description": "DSR menciona odds, benchmark, market board en Stage 1.",
            "condition": "always Stage 1",
        },
        {
            "id": "reject_invented_signal_not_in_contract",
            "severity": "reject",
            "description": "DSR crea señal ausente de enriched_directional_signals contractadas para ese fixture/market.",
            "condition": "signal not in enriched_directional_signals list for fixture+market",
        },
    ]
    return {
        "generated_at_utc": utc_now(),
        "ruleset_id": "mm2_7_validator_v3_rules",
        "inherits": "mm2_6r2_validator_v2_rules",
        "v2_rules_snapshot_count": len(v2_rules),
        "rules": v2_rules + extra,
    }


def build_contract_v2() -> dict[str, Any]:
    example_weather = {
        "block": "weather",
        "market_canonical": "OU_GOALS_2_5",
        "direction": "under_2_5",
        "strength": "weak",
        "allowed_in_signal_summary": True,
        "rule_id": "weather_extreme_under_weak_v1",
        "evidence_fields": [
            "enriched_descriptive_context.weather.extreme_weather_flag",
            "enriched_descriptive_context.timestamp_gate.safe_gate_pass",
        ],
        "reason": "extreme weather flag true pre-kickoff.",
        "limitations": ["No calibración histórica en MM-2.7."],
    }
    return {
        "contract_version": "mm2_7_enriched_directional_signals_v2",
        "generated_at_utc": utc_now(),
        "description": "Contrato de señales direccionales enriched para Stage 1; solo entradas con rule_id explícito y evidence_fields.",
        "enriched_directional_signals": [],
        "note_empty_array": "En runtime el adapter rellena solo señales que pasen gates; si ningún gate califica, el array permanece vacío.",
        "field_requirements": {
            "block": "availability|lineup|formation|weather|venue",
            "market_canonical": "FT_1X2|OU_GOALS_2_5",
            "direction": "home|draw|away|over_2_5|under_2_5|unknown",
            "strength": "none|weak|medium|strong",
            "allowed_in_signal_summary": "boolean",
            "rule_id": "string",
            "evidence_fields": "array of dot-paths into adapter package",
            "reason": "string",
            "limitations": "array of strings",
        },
        "example_allowed_weather": example_weather,
        "example_payload_shape": {"enriched_directional_signals": [example_weather]},
    }


def main() -> int:
    rule_params = {"absence_count_diff_min": 4, "min_absences_same_critical_line": 2}

    packages_doc = read_json(PACKAGES_IN)
    if not packages_doc or "packages" not in packages_doc:
        print("Missing packages input", PACKAGES_IN, file=sys.stderr)
        return 1
    packages: list[dict[str, Any]] = packages_doc["packages"]

    inventory_rows = [build_inventory_row(p) for p in packages]
    inv_fields = list(inventory_rows[0].keys()) if inventory_rows else []
    write_csv(INVENTORY_CSV_OUT, inventory_rows, inv_fields)

    def _b(x: Any) -> bool:
        return x is True or str(x).lower() == "true"

    inv_stats = {
        "fixture_count": len(inventory_rows),
        "extreme_weather_true": sum(1 for r in inventory_rows if _b(r.get("extreme_weather_flag"))),
        "confirmed_lineup_status": sum(
            1 for r in inventory_rows if r.get("confirmed_status") == "confirmed"
        ),
        "timestamp_gate_safe": sum(1 for r in inventory_rows if _b(r.get("timestamp_gate_safe"))),
        "any_home_unknown": sum(1 for r in inventory_rows if int(r.get("home_unknown_count") or 0) > 0),
        "any_away_unknown": sum(1 for r in inventory_rows if int(r.get("away_unknown_count") or 0) > 0),
        "formation_available_true": sum(1 for r in inventory_rows if _b(r.get("formation_available"))),
    }

    gate_defs = build_candidate_gate_definitions(rule_params)
    write_json(GATE_DEFS_OUT, gate_defs)

    write_json(PLAYER_MODEL_OUT, build_player_model_v0())

    avail_rows, db_meta = db_probe_player_importance_inputs()
    write_csv(
        PLAYER_AVAIL_CSV_OUT,
        avail_rows,
        ["feature_id", "classification", "notes", "evidence"],
    )

    severe = build_severe_rule_design(rule_params)
    severe["db_probe_meta"] = db_meta
    write_json(SEVERE_RULE_OUT, severe)

    gate_rows: list[dict[str, Any]] = []

    any_valid = False
    for pkg in packages:
        ec = pkg.get("event_context") or {}
        fid = ec.get("fixture_id")
        desc = pkg.get("enriched_descriptive_context") or {}

        for m in MARKETS:
            w_sig = eval_weather_gate(desc, m)
            a_sig = eval_availability_gate_mm27(desc, m, rule_params)
            l_sig = eval_lineup_gate(desc, m)
            f_sig = eval_formation_gate(desc, m)
            v_sig = eval_venue_gate(desc, m)

            for s in (w_sig, a_sig, l_sig, f_sig, v_sig):
                if is_valid_directional(s):
                    any_valid = True

            allowed_ct = sum(
                1
                for s in (w_sig, a_sig, l_sig, f_sig, v_sig)
                if s.get("allowed_in_signal_summary")
            )
            directional_ct = sum(
                1
                for s in (w_sig, a_sig, l_sig, f_sig, v_sig)
                if is_valid_directional(s)
            )
            reasons = []
            if directional_ct == 0:
                reasons.append("no gate produced direction!=unknown with strength!=none and allowed summary")

            gate_rows.append(
                {
                    "fixture_id": fid,
                    "market_canonical": m,
                    "weather_direction": w_sig.get("direction"),
                    "weather_strength": w_sig.get("strength"),
                    "weather_allowed_in_signal_summary": w_sig.get("allowed_in_signal_summary"),
                    "weather_rule_id": w_sig.get("rule_id"),
                    "availability_direction": a_sig.get("direction"),
                    "availability_strength": a_sig.get("strength"),
                    "availability_allowed_in_signal_summary": a_sig.get("allowed_in_signal_summary"),
                    "availability_rule_id": a_sig.get("rule_id"),
                    "lineup_direction": l_sig.get("direction"),
                    "lineup_strength": l_sig.get("strength"),
                    "lineup_allowed_in_signal_summary": l_sig.get("allowed_in_signal_summary"),
                    "lineup_rule_id": l_sig.get("rule_id"),
                    "formation_direction": f_sig.get("direction"),
                    "formation_strength": f_sig.get("strength"),
                    "formation_allowed_in_signal_summary": f_sig.get("allowed_in_signal_summary"),
                    "formation_rule_id": f_sig.get("rule_id"),
                    "venue_direction": v_sig.get("direction"),
                    "venue_strength": v_sig.get("strength"),
                    "venue_allowed_in_signal_summary": v_sig.get("allowed_in_signal_summary"),
                    "venue_rule_id": v_sig.get("rule_id"),
                    "final_enriched_directional_signal_count": directional_ct,
                    "allowed_in_signal_summary_count": allowed_ct,
                    "reason_if_none": "; ".join(reasons) if reasons else "",
                }
            )

    # Preview: full combined per fixture (both markets)
    preview_full: list[dict[str, Any]] = []
    for pkg in packages:
        ec = pkg.get("event_context") or {}
        fid = ec.get("fixture_id")
        desc = pkg.get("enriched_descriptive_context") or {}
        combined: list[dict[str, Any]] = []
        for m in MARKETS:
            combined.extend(
                [
                    eval_weather_gate(desc, m),
                    eval_availability_gate_mm27(desc, m, rule_params),
                    eval_lineup_gate(desc, m),
                    eval_formation_gate(desc, m),
                    eval_venue_gate(desc, m),
                ]
            )
        preview_full.append({"fixture_id": fid, "enriched_directional_signals": combined})

    write_json(PREVIEW_OUT, {"generated_at_utc": utc_now(), "fixtures": preview_full})

    write_csv(
        GATE_ROWS_OUT,
        gate_rows,
        list(gate_rows[0].keys()) if gate_rows else [],
    )

    write_json(CONTRACT_OUT, build_contract_v2())
    write_json(VALIDATOR_V3_OUT, build_validator_v3())

    leakage_ok = True
    leak_rows = read_csv(LEAKAGE_CSV_IN)
    for r in leak_rows:
        if str(r.get("leakage_status", "")).strip().upper() != "PASS":
            leakage_ok = False
            break

    prompt_guardrails_compatible = True

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)

    readiness = {
        "generated_at_utc": utc_now(),
        "mode": "mm2_7_enriched_directional_signal_gate_design_artifact_only",
        "inputs_used": [
            _rel(PACKAGES_IN),
            _rel(RETRY_IN),
            _rel(VALIDATION_CSV_IN),
            _rel(BEFORE_AFTER_IN),
            _rel(POLICY_IN),
            _rel(VALIDATOR_V2_IN),
            _rel(ENRICHED_BLOCKS_IN),
            _rel(BASE_BLOCKS_IN),
            _rel(FIXTURE_ROWS_IN),
            _rel(LEAKAGE_CSV_IN),
        ],
        "restrictions_observed": {
            "artifact_only": True,
            "dsr_calls": False,
            "toa_calls": False,
            "sportmonks_api_calls": False,
            "external_calls": False,
            "db_writes": False,
            "select_only_db_probe": True,
        },
        "MM2_7_enriched_directional_signal_gate_design_completed": True,
        "MM2_7_valid_directional_gate_available_now": any_valid,
        "MM2_7_ready_for_guarded_dsr_retry": bool(
            any_valid and prompt_guardrails_compatible and leakage_ok
        ),
        "db_probe_connected": db_meta.get("connected"),
        "db_probe_error": db_meta.get("error"),
        "criteria_notes": {
            "valid_gate_requires": [
                "direction != unknown",
                "strength != none",
                "allowed_in_signal_summary true",
                "explicit rule_id",
                "non-empty evidence_fields",
                "validator_v3 compatible (structural)",
            ],
            "leakage_audit_csv_pass": leakage_ok,
            "prompt_guardrails_compatible_assumption": prompt_guardrails_compatible,
        },
        "recommendation_if_no_valid_gate": (
            "No llamar DSR con enriched direccional; mantener enriched como descriptivo/artifact-only; "
            "construir modelo de importancia y/o esperar fixtures con extreme_weather_flag o datos sin unknown_count "
            "que pasen reglas candidatas validadas históricamente."
        ),
    }
    write_json(READINESS_OUT, readiness)

    # Audit markdown (sections 1–21)
    retry = read_json(RETRY_IN, {})
    val_csv = read_csv(VALIDATION_CSV_IN)
    audit_body = _render_audit(
        packages,
        inventory_rows,
        inv_stats,
        any_valid,
        readiness["MM2_7_ready_for_guarded_dsr_retry"],
        retry,
        val_csv,
        db_meta,
    )
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(audit_body, encoding="utf-8")

    print("MM-2.7 artifacts written under", OUT)
    print("Audit:", AUDIT_OUT)
    return 0


def _render_audit(
    packages: list[dict[str, Any]],
    inventory_rows: list[dict[str, Any]],
    inv_stats: dict[str, Any],
    any_valid: bool,
    ready_retry: bool,
    retry: dict[str, Any],
    val_csv: list[dict[str, Any]],
    db_meta: dict[str, Any],
) -> str:
    n_fix = len(packages)
    lines = [
        "# MM-2.7 Enriched Directional Signal Gate Design Audit",
        "",
        "## 1. Executive summary",
        "",
        "MM-2.7 define gates direccionales candidatos (weather, availability, lineup, formation, venue), "
        "un contrato `enriched_directional_signals` v2, validator v3 y evalúa el universo MM-2.6R (10 fixtures) "
        "en modo artifact-only. "
        f"**Dirección válida emitida por gates MM-2.7 en este universo:** {'sí' if any_valid else 'no'}. "
        f"**Listo para DSR guardado:** {'sí' if ready_retry else 'no'}. "
        "Sin llamadas DSR/API/TOA/SportMonks ni escrituras a base de datos.",
        "",
        "## 2. Scope and restrictions",
        "",
        "- Artifact-only; SELECT-only opcional para inventario de tablas/payload.",
        "- Sin DSR, TOA, SportMonks API, llamadas externas, DB writes, producción, bt2_daily_picks, Telegram, vault, apuestas, tenis, Stage 2, picks, settlement nuevo, ROI/hit rate, activación de enriched productivo ni odds en Stage 1.",
        "",
        "## 3. Why MM-2.7 was needed",
        "",
        "MM-2.6R.3 demostró que el contexto enriched es seguro y separable, pero **no direccional**: "
        "`MM2_6r3_valid_directional_enriched_signal_available=false`. Se requiere diseño explícito de gates y contrato "
        "para que el adapter solo emita señales cuando reglas sean auditables y validables, evitando que DSR invente edge desde datos descriptivos.",
        "",
        "## 4. Inputs used",
        "",
        "- `docs/bettracker2/audits/MM2_6R3_GUARDRAIL_V2_PACKAGE_VALIDATION_AUDIT.md` (contexto previo).",
        f"- `{PACKAGES_IN.relative_to(ROOT)}`",
        f"- `{RETRY_IN.relative_to(ROOT)}`",
        f"- `{VALIDATION_CSV_IN.relative_to(ROOT)}`",
        f"- `{BEFORE_AFTER_IN.relative_to(ROOT)}`",
        f"- `{POLICY_IN.relative_to(ROOT)}`",
        f"- `{VALIDATOR_V2_IN.relative_to(ROOT)}`",
        f"- `{ENRICHED_BLOCKS_IN.relative_to(ROOT)}` (si existe).",
        f"- `{BASE_BLOCKS_IN.relative_to(ROOT)}` (si existe).",
        f"- `{FIXTURE_ROWS_IN.relative_to(ROOT)}`",
        f"- `{LEAKAGE_CSV_IN.relative_to(ROOT)}`",
        "",
        "Salidas MM-2.7 generadas por `scripts/mm2_7_enriched_directional_signal_gate_design.py`:",
        "- `scripts/outputs/mm2_7_enriched_data_inventory.csv`",
        "- `scripts/outputs/mm2_7_candidate_gate_definitions.json`",
        "- `scripts/outputs/mm2_7_player_importance_model_v0_design.json`",
        "- `scripts/outputs/mm2_7_player_importance_data_availability.csv`",
        "- `scripts/outputs/mm2_7_severe_absence_imbalance_rule_design.json`",
        "- `scripts/outputs/mm2_7_gate_application_rows.csv`",
        "- `scripts/outputs/mm2_7_enriched_directional_signals_preview.json`",
        "- `scripts/outputs/mm2_7_enriched_directional_signal_contract_v2.json`",
        "- `scripts/outputs/mm2_7_validator_v3_rules.json`",
        "- `scripts/outputs/mm2_7_enriched_signal_gate_readiness.json`",
        "- `docs/bettracker2/audits/MM2_7_ENRICHED_DIRECTIONAL_SIGNAL_GATE_DESIGN_AUDIT.md`",
        "",
        "## 5. Enriched data inventory",
        "",
        f"Se emitió `scripts/outputs/mm2_7_enriched_data_inventory.csv` con {n_fix} filas (una por fixture). "
        "Campos: lineups, confirmed_status, conteos listados, formations, ausencias por tipo/posición, weather, venue (desde bloque weather), timestamp_gate, blocked_blocks.",
        "",
        "Resumen agregado (MM-2.6R universe):",
        f"- `timestamp_gate_safe==true`: {inv_stats.get('timestamp_gate_safe')} / {inv_stats.get('fixture_count')}.",
        f"- `extreme_weather_flag==true`: {inv_stats.get('extreme_weather_true')}.",
        f"- `confirmed_status==confirmed`: {inv_stats.get('confirmed_lineup_status')}.",
        f"- Fixtures con `home_unknown_count>0`: {inv_stats.get('any_home_unknown')}; con `away_unknown_count>0`: {inv_stats.get('any_away_unknown')}.",
        f"- `formation_available==true`: {inv_stats.get('formation_available_true')}.",
        "",
        "## 6. Candidate gates",
        "",
        "Ver `scripts/outputs/mm2_7_candidate_gate_definitions.json` (matriz y definiciones por gate).",
        "",
        "## 7. Weather signal gate",
        "",
        "- Si `extreme_weather_flag=true` y `timestamp_gate.safe_gate_pass` y mercado `OU_GOALS_2_5`: "
        "`under_2_5`, fuerza `weak`, `allowed_in_signal_summary=true`, `rule_id=weather_extreme_under_weak_v1`.",
        "- Si no extremo: `unknown` / `none` / no permitido en resumen.",
        "",
        "## 8. Availability signal gate",
        "",
        "Regla candidata **typed severe imbalance** (FT_1X2 solamente): ver sección 13 y JSON de diseño. "
        "Requiere `unknown_count=0` en ambos equipos, diferencia mínima de `injury+suspension`, y cluster crítico en el peor lado.",
        "",
        "## 9. Lineup signal gate",
        "",
        "- Sin `confirmed_status=confirmed`: solo descriptivo.",
        "- Con confirmado: no se emite dirección sin `lineup_strength_delta`, modelo de importancia o detección de rotación.",
        "",
        "## 10. Formation signal gate",
        "",
        "Por defecto descriptivo; sin ventaja táctica validada.",
        "",
        "## 11. Venue signal gate",
        "",
        "Solo metadatos (venue_name, surface); sin señal direccional en v0.",
        "",
        "## 12. Player importance model v0 design",
        "",
        "Ver `scripts/outputs/mm2_7_player_importance_model_v0_design.json` y disponibilidad en "
        "`scripts/outputs/mm2_7_player_importance_data_availability.csv`.",
        f"- DB probe connected: {db_meta.get('connected')}; error: {db_meta.get('error')}.",
        f"- Tablas candidatas (muestra): {', '.join(db_meta.get('tables_like') or [])[:500]}.",
        "",
        "## 13. Severe absence imbalance rule",
        "",
        "Ver `scripts/outputs/mm2_7_severe_absence_imbalance_rule_design.json`. Estado **candidate_only** (sin backtest en MM-2.7).",
        "",
        "## 14. Gate application to MM-2.6R universe",
        "",
        f"Evaluados {n_fix} fixtures × 2 mercados. Salida: `scripts/outputs/mm2_7_gate_application_rows.csv` y "
        "`scripts/outputs/mm2_7_enriched_directional_signals_preview.json`.",
        "",
        "## 15. Directional signal contract v2",
        "",
        "Ver `scripts/outputs/mm2_7_enriched_directional_signal_contract_v2.json`.",
        "",
        "## 16. Validator v3",
        "",
        "Ver `scripts/outputs/mm2_7_validator_v3_rules.json` (incluye snapshot de reglas v2 más extensiones v3). Nuevas reglas v3 (rechazo):",
        "- Lenguaje de *key player* sin `player_importance_model` activo.",
        "- Alineación “confirmada” cuando `confirmed_status != confirmed`.",
        "- Ausencias como señal si `availability_signal.allowed_in_signal_summary=false`.",
        "- Borde táctico por formación si `formation_signal.allowed_in_signal_summary=false`.",
        "- Clima para over/under si `weather_signal.allowed_in_signal_summary=false`.",
        "- Odds / benchmark / market board en Stage 1.",
        "- Señal no listada en `enriched_directional_signals` del contrato para el fixture/mercado.",
        "",
        "## 17. V1 packaging lesson",
        "",
        "v1 usaba `processed.*` para compactar antes del LLM. BT2 debe retener solo el **patrón** de empaquetado "
        "(contexto procesado y separación clara), no copiar estadísticas del fixture objetivo, key_player sin modelo, "
        "odds en Stage 1 ni conversión libre de descriptivo a rationale direccional.",
        "",
        "## 18. Readiness decision",
        "",
        f"- MM2_6r3_retry snapshot: valid_directional={retry.get('MM2_6r3_valid_directional_enriched_signal_available')}, "
        f"ready_dsr={retry.get('MM2_6r3_ready_for_dsr_retry')}.",
        f"- MM2_7_valid_directional_gate_available_now: **{any_valid}**.",
        f"- MM2_7_ready_for_guarded_dsr_retry: **{ready_retry}**.",
        "",
        "## 19. What this proves",
        "",
        "- Diseño de gates y contrato v2 coherentes con restricciones MM-2.",
        "- Inventario factual del universo MM-2.6R respecto a campos enriched usados por los gates.",
        "- Evaluación reproducible sobre artefactos sin pipeline productivo.",
        "",
        "## 20. What this does not prove",
        "",
        "- No prueba edge, ROI, acierto, valor de mercado ni calidad predictiva de reglas candidatas.",
        "- No valida que `extreme_weather_flag` esté bien calibrado.",
        "- No sustituye revisión legal/compliance de prompts en producción.",
        "",
        "## 21. Recommended next step",
        "",
        "- Si no hay gate válido: **no** llamar DSR; seguir artifact-only; priorizar modelo de importancia v1 y/o "
        "calibración histórica de `severe_absence_imbalance` y del flag de clima extremo.",
        "- Cuando exista al menos una señal con `rule_id`, `evidence_fields` y validación v3 en cero fallos, reevaluar mini-run DSR acotado.",
        "",
        "---",
        "",
        "### Pregunta final (respuesta operativa)",
        "",
        "**¿Qué `enriched_directional_signals` podemos generar hoy de forma segura y auditable?** "
        "En el universo MM-2.6R observado: ninguna con dirección distinta de `unknown` y fuerza distinta de `none` "
        "bajo las reglas conservadoras (clima no extremo, alineaciones no confirmadas, ausencias con `unknown_count`, etc.). "
        "A nivel de **diseño**, sí están especificadas señales potenciales: OU bajo clima extremo (débil) y FT a favor del "
        "rival ante desequilibrio tipado de ausencias en líneas críticas (débil, candidata).",
        "",
        "**¿Qué reglas/modelos faltan?** Modelo de importancia de jugadores, deltas de calidad de XI confirmada, "
        "detección de rotación, reglas tácticas de formación validadas, calibración de clima extremo, y validación histórica "
        "de la regla de ausencias severas; además de datos sin `unknown` en tipos de baja y más fixtures con gates activos.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
