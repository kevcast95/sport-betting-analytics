#!/usr/bin/env python3
"""
select_candidates.py

Filtra event_features por diagnostics y selecciona candidatos aptos para el agente (Copa Foxkids).

Contrato base (Tier A y B):
  - event_ok, lineups_ok, h2h_ok, team_streaks_ok, y al menos odds_all o odds_featured.

Tier A (estricto): contrato base + statistics_ok (panel de estadísticas del partido disponible).
Tier B (fallback): contrato base sin statistics_ok — evita quedarse en 0 candidatos cuando
  SofaScore no expone /statistics pre-partido; contexto vía h2h + rachas + (opcional)
  processed.team_season_stats (estadísticas de temporada en la misma liga).

Scoring: cuenta endpoints OK en diagnostics (0–7).

Exclusión partido terminado (operativo):
  Por defecto se rechazan eventos con match_state finished o status típico de FT (ended, full time, …).
  Tenis además: match_state live (el API ya sabe que va en curso; evita huecos si startTimestamp va desfasado).
  Para evaluar picks sobre datos post-partido: usar --allow-finished.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.config import get_db_config  # noqa: E402
from db.db import connect  # noqa: E402
from db.init_db import init_db  # noqa: E402
from core.candidate_contract import (  # noqa: E402
    classify_tier,
    contract_description,
    diagnostics_flags,
    normalize_sport,
    reject_reason as contract_reject_reason,
)
from db.repositories.daily_runs_repo import get_daily_run  # noqa: E402
from db.repositories.event_features_repo import fetch_event_features_by_captured_at  # noqa: E402


def _schedule_display(event_context: Dict[str, Any], tz_name: str) -> Dict[str, Any]:
    """
    SofaScore usa start_timestamp en segundos Unix (UTC).
    Expone UTC + zona local de referencia (default Colombia) para evitar confusiones en análisis.
    """
    raw_ts = event_context.get("start_timestamp")
    out: Dict[str, Any] = {
        "start_timestamp_unix": raw_ts,
        "timezone_reference": tz_name,
    }
    if raw_ts is None:
        out["note"] = "sin_start_timestamp"
        return out
    try:
        ts = int(raw_ts)
    except (TypeError, ValueError):
        out["note"] = "start_timestamp_no_entero"
        return out
    utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    out["utc_iso"] = utc_dt.strftime("%Y-%m-%d %H:%M UTC")
    try:
        local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
        out["local_iso"] = local_dt.strftime("%Y-%m-%d %H:%M %Z")
    except Exception as exc:  # noqa: BLE001
        out["local_error"] = str(exc)
    return out


def _is_terminal_match(event_context: Dict[str, Any]) -> bool:
    """
    Partido ya cerrado (no apto para picks pre-partido en modo operativo).
    Usa match_state y refuerzo por status textual / código SofaScore (100 = ended).
    """
    ms = str(event_context.get("match_state") or "").lower()
    if ms == "finished":
        return True

    st_raw = event_context.get("status")
    if isinstance(st_raw, int) and st_raw == 100:
        return True
    if isinstance(st_raw, str) and st_raw.strip() == "100":
        return True
    st = str(st_raw or "").lower()
    for hint in (
        "finished",
        "full time",
        "after penalt",
        "after extra time",
        "ended",
        # Tenis / estados finales habituales en SofaScore
        "walkover",
        "w/o",
        "retired",
        "ret.",
        "awarded",
        "abandoned",
        "cancelled",
        "canceled",
    ):
        if hint in st:
            return True
    return False


def _quality_score(flags: Dict[str, bool]) -> int:
    """Cuantos flags OK (0-8). team_season_stats_ok es respaldo opcional, no filtro duro."""
    return sum(1 for v in flags.values() if v)


def _parse_analysis_reference_utc(raw: Optional[str]) -> datetime:
    if raw is None or not str(raw).strip():
        return datetime.now(timezone.utc)
    text = str(raw).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _event_has_started(event_context: Dict[str, Any], *, ref_utc: datetime) -> bool:
    raw_ts = event_context.get("start_timestamp")
    try:
        ts = int(raw_ts)
    except (TypeError, ValueError):
        return False
    start_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    return start_utc <= ref_utc


def _min_lead_minutes() -> int:
    raw = os.environ.get("ALTEA_TENNIS_MIN_LEAD_MINUTES", "45").strip()
    try:
        v = int(raw)
    except ValueError:
        return 45
    return max(0, v)


def _event_starts_too_soon(
    event_context: Dict[str, Any], *, ref_utc: datetime, min_lead_minutes: int
) -> bool:
    raw_ts = event_context.get("start_timestamp")
    try:
        ts = int(raw_ts)
    except (TypeError, ValueError):
        return False
    start_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    delta_sec = (start_utc - ref_utc).total_seconds()
    return delta_sec < (min_lead_minutes * 60)


def _tennis_low_itf_filter_enabled() -> bool:
    return os.environ.get("ALTEA_TENNIS_EXCLUDE_LOW_ITF", "1").lower() not in (
        "0",
        "false",
        "no",
    )


def _is_low_itf_tournament(event_context: Dict[str, Any]) -> bool:
    """
    Filtro operativo para evitar torneos con baja disponibilidad en casas locales.
    Se puede ajustar por regex vía env sin tocar código.
    """
    tournament = str(event_context.get("tournament") or "").strip()
    if not tournament:
        return False
    rx = os.environ.get(
        "ALTEA_TENNIS_EXCLUDE_TOURNAMENT_REGEX",
        r"\bITF\s+W(?:15|25)\b",
    )
    try:
        return re.search(rx, tournament, flags=re.IGNORECASE) is not None
    except re.error:
        # Si regex inválida por env, no bloquear el pipeline.
        return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Selecciona eventos candidatos para DS según diagnostics (Tier A/B)."
    )
    p.add_argument("--db", required=True)
    p.add_argument("--daily-run-id", type=int, required=True)
    p.add_argument("--limit", type=int, default=50, help="Máx candidatos a devolver")
    p.add_argument("--output", "-o", type=str, default=None, help="Archivo JSON de salida")
    p.add_argument("--verbose", "-v", action="store_true", help="Mostrar resumen de filtrado")
    p.add_argument(
        "--allow-finished",
        action="store_true",
        help="Incluye partidos terminados (solo backtesting; operativo debe omitirlo).",
    )
    p.add_argument(
        "--allow-started",
        action="store_true",
        help="Incluye partidos ya iniciados (por defecto se excluyen para ahorrar tokens).",
    )
    p.add_argument(
        "--analysis-at-utc",
        type=str,
        default=None,
        help="Referencia ISO UTC para filtrar eventos iniciados (default: now UTC).",
    )
    p.add_argument(
        "--timezone",
        type=str,
        default=os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota"),
        help="Zona para schedule_display.local_iso (default: America/Bogota o env COPA_FOXKIDS_TZ).",
    )
    return p.parse_args()


def run(args: argparse.Namespace) -> None:
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

    daily = get_daily_run(conn, args.daily_run_id)
    captured_at_utc = str(daily["created_at_utc"])
    sport = normalize_sport(daily["sport"])

    rows = fetch_event_features_by_captured_at(conn, captured_at_utc, sport=sport)
    analysis_ref_utc = _parse_analysis_reference_utc(args.analysis_at_utc)
    lead_minutes = _min_lead_minutes()

    candidates: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    reasons: Dict[str, int] = {}
    rejected_reason_by_event: Dict[int, str] = {}

    for row in rows:
        event_id = int(row["event_id"])
        features = json.loads(row["features_json"])

        event_context = features.get("event_context") or {}
        match_state = str(event_context.get("match_state") or "").lower()
        if not args.allow_started and _event_has_started(
            event_context, ref_utc=analysis_ref_utc
        ):
            reasons["match_started"] = reasons.get("match_started", 0) + 1
            rejected_reason_by_event[event_id] = "match_started"
            rejected.append(
                {
                    "event_id": event_id,
                    "reason": "match_started",
                    "diagnostics": diagnostics_flags(features.get("diagnostics") or {}),
                    "match_state": match_state,
                    "start_timestamp": event_context.get("start_timestamp"),
                    "analysis_ref_utc": analysis_ref_utc.isoformat(),
                }
            )
            continue
        if (
            sport == "tennis"
            and not args.allow_started
            and _event_starts_too_soon(
                event_context,
                ref_utc=analysis_ref_utc,
                min_lead_minutes=lead_minutes,
            )
        ):
            reasons["match_start_too_soon"] = reasons.get("match_start_too_soon", 0) + 1
            rejected_reason_by_event[event_id] = "match_start_too_soon"
            rejected.append(
                {
                    "event_id": event_id,
                    "reason": "match_start_too_soon",
                    "diagnostics": diagnostics_flags(features.get("diagnostics") or {}),
                    "match_state": match_state,
                    "start_timestamp": event_context.get("start_timestamp"),
                    "analysis_ref_utc": analysis_ref_utc.isoformat(),
                    "min_lead_minutes": lead_minutes,
                }
            )
            continue
        # Tenis: si el API ya marca en vivo, descartar aunque startTimestamp esté mal
        # (evita picks cuando el reloj de programación no coincide con la realidad).
        if (
            sport == "tennis"
            and not args.allow_started
            and match_state == "live"
        ):
            reasons["match_live"] = reasons.get("match_live", 0) + 1
            rejected_reason_by_event[event_id] = "match_live"
            rejected.append(
                {
                    "event_id": event_id,
                    "reason": "match_live",
                    "diagnostics": diagnostics_flags(features.get("diagnostics") or {}),
                    "match_state": match_state,
                    "start_timestamp": event_context.get("start_timestamp"),
                    "status": event_context.get("status"),
                }
            )
            continue
        if (
            sport == "tennis"
            and _tennis_low_itf_filter_enabled()
            and _is_low_itf_tournament(event_context)
        ):
            reasons["tournament_not_operable_book"] = (
                reasons.get("tournament_not_operable_book", 0) + 1
            )
            rejected_reason_by_event[event_id] = "tournament_not_operable_book"
            rejected.append(
                {
                    "event_id": event_id,
                    "reason": "tournament_not_operable_book",
                    "diagnostics": diagnostics_flags(features.get("diagnostics") or {}),
                    "match_state": match_state,
                    "tournament": event_context.get("tournament"),
                }
            )
            continue
        if not args.allow_finished and _is_terminal_match(event_context):
            reasons["match_finished"] = reasons.get("match_finished", 0) + 1
            rejected_reason_by_event[event_id] = "match_finished"
            rejected.append(
                {
                    "event_id": event_id,
                    "reason": "match_finished",
                    "diagnostics": diagnostics_flags(features.get("diagnostics") or {}),
                    "match_state": match_state,
                    "status": event_context.get("status"),
                }
            )
            continue

        diagnostics = features.get("diagnostics") or {}
        flags = diagnostics_flags(diagnostics)
        score = _quality_score(flags)
        tier = classify_tier(flags, sport=sport)

        if tier is not None:
            candidates.append(
                {
                    "event_id": event_id,
                    "tier": tier,
                    "quality_score": score,
                    "diagnostics": flags,
                }
            )
        else:
            reason = contract_reject_reason(
                flags, str(event_context.get("match_state") or ""), sport=sport
            ) or "unknown"
            rejected_reason_by_event[event_id] = reason
            reasons[reason] = reasons.get(reason, 0) + 1
            rejected.append({"event_id": event_id, "reason": reason, "diagnostics": flags})

    # Tier A primero, luego B; dentro de cada tier, mayor quality_score
    candidates.sort(key=lambda x: (0 if x["tier"] == "A" else 1, -x["quality_score"]))
    top = candidates[: args.limit]

    tier_counts: Dict[str, int] = {}
    for c in candidates:
        tier_counts[c["tier"]] = tier_counts.get(c["tier"], 0) + 1
    tier_selected = {"A": 0, "B": 0}
    for c in top:
        tier_selected[c["tier"]] = tier_selected.get(c["tier"], 0) + 1

    desc = contract_description(sport=sport)
    result = {
        "job": "select_candidates",
        "daily_run_id": args.daily_run_id,
        "sport": sport,
        "captured_at_utc": captured_at_utc,
        "contract": desc,
        "total_events": len(rows),
        "passed_filters": len(candidates),
        "tier_counts_all_passed": tier_counts,
        "rejected": len(rejected),
        "rejection_reasons": reasons,
        "selected": [c["event_id"] for c in top],
        "tier_selected": tier_selected,
        "candidates_detail": top,
    }

    ds_input: List[Dict[str, Any]] = []
    event_ids_selected = [c["event_id"] for c in top]
    selected_id_set = set(event_ids_selected)
    passed_id_set = {c["event_id"] for c in candidates}
    tier_by_id = {c["event_id"]: c["tier"] for c in top}
    tz = str(args.timezone or "America/Bogota")

    run_inventory: List[Dict[str, Any]] = []
    for row in rows:
        features = json.loads(row["features_json"])
        eid = int(row["event_id"])
        ec = features.get("event_context") or {}
        passed = eid in passed_id_set
        run_inventory.append(
            {
                "event_id": eid,
                "home_team": ec.get("home_team"),
                "away_team": ec.get("away_team"),
                "tournament": ec.get("tournament"),
                "match_state": ec.get("match_state"),
                "schedule_display": _schedule_display(ec, tz),
                "passed_candidate_filters": passed,
                "in_ds_input": eid in selected_id_set,
                "reject_reason": None if passed else rejected_reason_by_event.get(eid),
            }
        )

    for row in rows:
        if int(row["event_id"]) in event_ids_selected:
            features = json.loads(row["features_json"])
            eid = int(row["event_id"])
            ec = features.get("event_context") or {}
            ds_input.append(
                {
                    "event_id": eid,
                    "sport": sport,
                    "selection_tier": tier_by_id.get(eid),
                    "schedule_display": _schedule_display(ec, tz),
                    "event_context": ec,
                    "processed": features.get("processed") or {},
                    "diagnostics": features.get("diagnostics") or {},
                }
            )
    id_to_idx = {eid: i for i, eid in enumerate(event_ids_selected)}
    ds_input.sort(key=lambda x: id_to_idx.get(x["event_id"], 999))

    result["run_inventory"] = run_inventory
    result["schedule_timezone"] = tz
    result["ds_input"] = ds_input
    result["ds_input_summary"] = {
        "count": len(ds_input),
        "structure_per_event": {
            "event_id": "int",
            "selection_tier": "'A' | 'B' — A=full stats+h2h+streaks+lineups+odds; B=fallback sin statistics",
            "schedule_display": "utc_iso + local_iso (zona --timezone / COPA_FOXKIDS_TZ)",
            "event_context": "dict (tournament, home_team, away_team, start_timestamp, ...)",
            "processed": "dict (lineups, statistics, h2h, team_streaks, team_season_stats, odds_all, odds_featured)",
            "diagnostics": "dict (event_ok, statistics_ok, h2h_ok, team_streaks_ok, ...)",
        },
    }

    out_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_json)
        print(f"OK written to {args.output}")

    print("\n=== SELECT_CANDIDATES ===")
    print(
        json.dumps(
            {
                "job": "select_candidates",
                "daily_run_id": args.daily_run_id,
                "total_events": len(rows),
                "passed_filters": len(candidates),
                "tier_counts_all_passed": tier_counts,
                "tier_selected": tier_selected,
                "rejected": len(rejected),
                "rejection_reasons": reasons,
                "selected_count": len(top),
                "selected_event_ids": [c["event_id"] for c in top],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print("=== OK ===\n")

    print(f"\n=== RUN_INVENTORY (validar nombres vs SofaScore; TZ ref={tz}) ===")
    for inv in run_inventory:
        sd = inv.get("schedule_display") or {}
        utc_s = sd.get("utc_iso", "?")
        loc_s = sd.get("local_iso", sd.get("local_error", "?"))
        flag = "DS_INPUT" if inv.get("in_ds_input") else ("OK_FILTRO" if inv.get("passed_candidate_filters") else f"NO:{inv.get('reject_reason')}")
        h, a = inv.get("home_team"), inv.get("away_team")
        print(
            f"  event_id={inv.get('event_id')} | {h} vs {a} | {inv.get('tournament')} | "
            f"UTC {utc_s} | local {loc_s} | {flag}"
        )
    print("=== FIN RUN_INVENTORY ===\n")

    print("\n=== PAYLOAD → juapi-tartara (Copa Foxkids) ===")
    print("Estructura: array de N objetos, uno por evento candidato.")
    print("Cada objeto incluye el bundle procesado + selection_tier (A|B).")
    print("  - event_context: meta del partido")
    print("  - processed.lineups / statistics / h2h / team_streaks / team_season_stats / odds_*")
    print("  - diagnostics: qué endpoints respondieron OK")
    print(f"Cantidad de eventos en el array: {len(ds_input)}")
    if ds_input:
        s = ds_input[0]
        ctx = s.get("event_context") or {}
        proc = s.get("processed") or {}
        proc_json_len = len(json.dumps(proc, ensure_ascii=False))
        print("\n--- Ejemplo primer evento (resumen) ---")
        print(f"  event_id: {s.get('event_id')}")
        print(f"  selection_tier: {s.get('selection_tier')}")
        print(f"  event_context: tournament={ctx.get('tournament')!r}, home={ctx.get('home_team')!r}")
        print(f"  processed: claves = {list(proc.keys())}")
        print(f"  processed: ~{proc_json_len} caracteres JSON.")
        print(f"  diagnostics: {s.get('diagnostics')}")
    print("\n--- Contrato de respuesta (picks JSON para persist_picks) ---")
    print(
        '{ "picks": [ { "event_id": int, "market": "1X2", "selection": "1"|"X"|"2", '
        '"picked_value": float?, "odds_reference": {}? } ] }'
    )
    if sport == "tennis":
        print(
            "Tenis: 1=jugador local (homeTeam), 2=visitante; processed.tennis_odds resume mercados; "
            "X casi nunca aplica."
        )
    print("Tier B implica menor cobertura de estadísticas de equipo en vivo; ponderar confianza.")
    print("=== FIN PAYLOAD DS ===\n")

    if args.output:
        print("(El archivo incluye ds_input[] con processed completo por evento.)")
    else:
        print("(Usa -o out/candidates_YYYY-MM-DD_select.json — ver openclaw/NAMING_ARTIFACTS.md.)")

    if args.verbose:
        print("\n--- Resumen ---", file=sys.stderr)
        print(f"Total eventos: {len(rows)}", file=sys.stderr)
        print(f"Pasaron filtros: {len(candidates)} (A={tier_counts.get('A', 0)}, B={tier_counts.get('B', 0)})", file=sys.stderr)
        print(f"Rechazados: {len(rejected)}", file=sys.stderr)
        for r, n in sorted(reasons.items()):
            print(f"  - {r}: {n}", file=sys.stderr)
        print(f"Seleccionados (top {args.limit}): {len(top)}", file=sys.stderr)


def main() -> None:
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
