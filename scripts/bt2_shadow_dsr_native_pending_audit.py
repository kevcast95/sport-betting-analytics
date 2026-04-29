#!/usr/bin/env python3
"""
Auditoría de pending_result para baseline DSR native (shadow_dsr_replay_native).

- Solo lectura de Postgres local + GET SportMonks (mismo patrón que bt2_shadow_evaluate_performance).
- Genera CSV/JSON de pending, comparación SM vs local, y muestra de control scored.
- No toca producción, no replays, no cambia T-60/mercado/región/proveedores.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx
import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_settings import bt2_settings

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
RUN_FAMILY = "shadow_dsr_replay_native"
SELECTION_SOURCE = "dsr_api_only"


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _norm(s: str) -> str:
    x = unicodedata.normalize("NFKD", (s or "").strip())
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"[^a-zA-Z0-9]+", " ", x).strip().lower()
    return re.sub(r"\s+", " ", x)


def _parse_sm_truth(payload: dict[str, Any]) -> tuple[Optional[str], Optional[int], Optional[int], str, str, bool]:
    """Alineado a scripts/bt2_shadow_evaluate_performance._parse_sm_truth."""
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    event_status = str(state.get("state") or state.get("name") or state.get("short_name") or "")
    participants = payload.get("participants") if isinstance(payload.get("participants"), list) else []
    p_home: int | None = None
    p_away: int | None = None
    home_name = ""
    away_name = ""
    for p in participants:
        if not isinstance(p, dict):
            continue
        loc = str((p.get("meta") or {}).get("location") or "").lower()
        if loc == "home":
            p_home = int(p.get("id") or 0) or None
            home_name = str(p.get("name") or "")
        elif loc == "away":
            p_away = int(p.get("id") or 0) or None
            away_name = str(p.get("name") or "")
    scores = payload.get("scores") if isinstance(payload.get("scores"), list) else []
    best_rank = -1
    out_home: int | None = None
    out_away: int | None = None
    for s in scores:
        if not isinstance(s, dict):
            continue
        desc = _norm(str(s.get("description") or s.get("type") or ""))
        rank = 3 if desc in {"current", "fulltime", "ft"} else 2 if "2nd" in desc else 1 if "1st" in desc else 0
        pid = int(s.get("participant_id") or 0) or None
        score_node = s.get("score")
        val = None
        if isinstance(score_node, dict):
            raw = score_node.get("goals") if score_node.get("goals") is not None else score_node.get("participant")
            if raw is None:
                raw = score_node.get("score")
            try:
                val = int(raw) if raw is not None else None
            except (TypeError, ValueError):
                val = None
        if val is None:
            try:
                val = int(s.get("score")) if s.get("score") is not None else None
            except (TypeError, ValueError):
                val = None
        if val is None:
            continue
        if pid == p_home and rank >= best_rank:
            out_home = val
            best_rank = rank
        elif pid == p_away and rank >= best_rank:
            out_away = val
            best_rank = rank
    has_score = out_home is not None and out_away is not None
    return event_status or None, out_home, out_away, home_name, away_name, has_score


def _fetch_sm_raw(fixture_ids: set[int]) -> dict[int, dict[str, Any]]:
    """fixture_id -> meta incl. http_ok, body_hint, parsed."""
    api = (bt2_settings.sportmonks_api_key or "").strip()
    out: dict[int, dict[str, Any]] = {}
    if not api or not fixture_ids:
        return out
    with httpx.Client(timeout=25) as client:
        for fid in sorted(fixture_ids):
            row: dict[str, Any] = {"fixture_id": fid, "http_status": None, "sm_error_message": None}
            try:
                r = client.get(
                    f"https://api.sportmonks.com/v3/football/fixtures/{fid}",
                    params={"api_token": api, "include": "participants;scores;state"},
                )
                row["http_status"] = r.status_code
                body = r.json() if "application/json" in (r.headers.get("content-type") or "") else {}
                if isinstance(body, dict):
                    msg = body.get("message")
                    if isinstance(msg, str):
                        row["sm_error_message"] = msg[:500]
                data = body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), dict) else {}
                if data:
                    st, rh, ra, hn, an, ok = _parse_sm_truth(data)
                    row["sm_event_status"] = st
                    row["sm_result_home"] = rh
                    row["sm_result_away"] = ra
                    row["sm_home_name"] = hn
                    row["sm_away_name"] = an
                    row["sm_has_ft_score"] = ok
                else:
                    row["sm_has_ft_score"] = False
            except Exception as ex:
                row["fetch_exception"] = str(ex)[:300]
            out[fid] = row
            time.sleep(0.08)
    return out


def _norm_status(s: str | None) -> str:
    return _norm(s or "")


def _classify_root_cause(
    *,
    bt2_event_id: int | None,
    sm_fixture_id: int | None,
    local_status: str | None,
    local_rh: int | None,
    local_ra: int | None,
    kickoff_utc: datetime | None,
    sm_meta: dict[str, Any],
    now_utc: datetime,
) -> tuple[str, str]:
    """
    Retorna (causa_primaria, detalle_corta).
    Causas alineadas al pedido del usuario.
    """
    sm_has = bool(sm_meta.get("sm_has_ft_score"))
    sm_st = str(sm_meta.get("sm_event_status") or "")
    http_s = sm_meta.get("http_status")
    sm_msg = sm_meta.get("sm_error_message") or ""

    local_has_both = local_rh is not None and local_ra is not None

    # Contradicción explícita
    if local_has_both and sm_has:
        if int(local_rh) != int(sm_meta.get("sm_result_home")) or int(local_ra) != int(sm_meta.get("sm_result_away")):
            return ("contradicción entre fuentes", "local vs SM FT distinto")

    if kickoff_utc and kickoff_utc > now_utc - timedelta(hours=1):
        return ("otra causa concreta", "kickoff reciente o futuro — posible partido no finalizado en datos")

    if sm_fixture_id is None and bt2_event_id is None:
        return ("falta de enlace limpio", "sin bt2_event_id y sin sm_fixture_id")

    if bt2_event_id is None and sm_fixture_id is not None:
        return ("falta de enlace limpio", "sin bt2_event_id; solo sm_fixture_id (evaluación depende de SM/merge)")

    if http_s and int(http_s) != 200:
        return ("sin marcador final en SM", f"HTTP {http_s} al consultar fixture")

    if sm_msg and ("subscription" in sm_msg.lower() or "plan" in sm_msg.lower() or "access" in sm_msg.lower()):
        return ("sin marcador final en SM", "mensaje API de acceso/suscripción (sin payload útil)")

    if not sm_has:
        stn = _norm_status(sm_st)
        if stn in {"ns", "not started", "scheduled", "tbd"}:
            return ("otra causa concreta", "SM aún NS / no iniciado")
        if "live" in stn or "inplay" in stn or stn == "l":
            return ("estado no cerrado aunque hay score", "SM en vivo / sin FT consolidado en payload parseado")
        if sm_fixture_id is None:
            return ("sin marcador final en SM", "sin sm_fixture_id para traer FT")
        return ("sin marcador final en SM", f"SM sin par FT parseado (state={sm_st or '∅'})")

    if not local_has_both:
        if sm_has:
            return ("sin marcador final en fuente local", "CDM/bt2_events incompleto; SM sí tiene FT")
        return ("sin marcador final en fuente local", "result_home/result_away NULL en bt2_events")

    return ("otra causa concreta", "clasificación residual")


def _merge_truth_like_evaluator(
    local_rh: int | None,
    local_ra: int | None,
    event_status: str,
    sm_meta: dict[str, Any],
) -> tuple[int | None, int | None, str, str]:
    """Replica merge de bt2_shadow_evaluate_performance (solo lectura)."""
    rh, ra = local_rh, local_ra
    est = event_status
    truth = "bt2_events_cdm_v1"
    if sm_meta.get("sm_has_ft_score") and (rh is None or ra is None):
        rh = int(sm_meta["sm_result_home"]) if sm_meta.get("sm_result_home") is not None else rh
        ra = int(sm_meta["sm_result_away"]) if sm_meta.get("sm_result_away") is not None else ra
        if sm_meta.get("sm_event_status"):
            est = str(sm_meta.get("sm_event_status") or est)
        truth = "sportmonks_fixture_api_v1"
    return rh, ra, est, truth


def main() -> None:
    now = datetime.now(timezone.utc)
    conn = psycopg2.connect(_dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT
          r.run_key,
          dp.id AS shadow_daily_pick_id,
          dp.sm_fixture_id,
          dp.bt2_event_id,
          ev.kickoff_utc,
          COALESCE(lg.name, '') AS league_name,
          ev.status AS local_event_status,
          ev.result_home AS local_result_home,
          ev.result_away AS local_result_away,
          e.eval_status,
          COALESCE(e.evaluation_reason, '') AS evaluation_reason,
          COALESCE(e.truth_source, '') AS truth_source_at_eval,
          e.result_home AS eval_stored_home,
          e.result_away AS eval_stored_away,
          e.event_status AS eval_stored_event_status
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        INNER JOIN bt2_shadow_pick_eval e ON e.shadow_daily_pick_id = dp.id
        LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
        LEFT JOIN bt2_leagues lg ON lg.id = ev.league_id
        WHERE r.run_family = %s
          AND r.selection_source = %s
          AND e.eval_status = 'pending_result'
        ORDER BY dp.id
        """,
        (RUN_FAMILY, SELECTION_SOURCE),
    )
    pending_rows = list(cur.fetchall() or [])

    fids = {int(r["sm_fixture_id"]) for r in pending_rows if r.get("sm_fixture_id") is not None}
    sm_map = _fetch_sm_raw(fids)

    audit_csv: list[dict[str, Any]] = []
    root_counts: Counter[str] = Counter()
    reconcile_merge_ft = 0

    for r in pending_rows:
        smid = int(r["sm_fixture_id"]) if r.get("sm_fixture_id") is not None else None
        sm_meta = dict(sm_map.get(smid or -1, {})) if smid else {}
        if not sm_meta and smid:
            sm_meta = {"fixture_id": smid, "http_status": None, "sm_has_ft_score": False}
        elif not smid:
            sm_meta = {"sm_has_ft_score": False, "sm_event_status": None}

        ko = r.get("kickoff_utc")
        if hasattr(ko, "tzinfo") and ko is not None and ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)

        loc_rh = int(r["local_result_home"]) if r.get("local_result_home") is not None else None
        loc_ra = int(r["local_result_away"]) if r.get("local_result_away") is not None else None
        loc_st = str(r.get("local_event_status") or "")

        primary, detail = _classify_root_cause(
            bt2_event_id=int(r["bt2_event_id"]) if r.get("bt2_event_id") is not None else None,
            sm_fixture_id=smid,
            local_status=loc_st or None,
            local_rh=loc_rh,
            local_ra=loc_ra,
            kickoff_utc=ko if isinstance(ko, datetime) else None,
            sm_meta=sm_meta,
            now_utc=now,
        )
        root_counts[primary] += 1

        mrh, mra, mest, mtruth = _merge_truth_like_evaluator(loc_rh, loc_ra, loc_st, sm_meta)
        if mrh is not None and mra is not None:
            reconcile_merge_ft += 1

        audit_csv.append(
            {
                "run_key": r["run_key"],
                "shadow_daily_pick_id": r["shadow_daily_pick_id"],
                "sm_fixture_id": r["sm_fixture_id"],
                "bt2_event_id": r["bt2_event_id"],
                "kickoff_utc": ko.isoformat() if ko else "",
                "league": r.get("league_name") or "",
                "eval_status": r["eval_status"],
                "evaluation_reason": r["evaluation_reason"],
                "truth_source_at_eval": r["truth_source_at_eval"],
                "local_event_status": loc_st,
                "local_result_home": loc_rh if loc_rh is not None else "",
                "local_result_away": loc_ra if loc_ra is not None else "",
                "sm_http_status": sm_meta.get("http_status", ""),
                "sm_event_status": sm_meta.get("sm_event_status", ""),
                "sm_result_home": sm_meta.get("sm_result_home", ""),
                "sm_result_away": sm_meta.get("sm_result_away", ""),
                "sm_has_ft_score": sm_meta.get("sm_has_ft_score", False),
                "sm_error_message": (sm_meta.get("sm_error_message") or "")[:200],
                "merged_result_home": mrh if mrh is not None else "",
                "merged_result_away": mra if mra is not None else "",
                "merged_truth_source_sim": mtruth,
                "root_cause_primary": primary,
                "root_cause_detail": detail,
                "eval_stored_home": r.get("eval_stored_home"),
                "eval_stored_away": r.get("eval_stored_away"),
            }
        )

    # Control: scored hit/miss sample
    cur.execute(
        """
        SELECT
          dp.id AS shadow_daily_pick_id,
          e.eval_status,
          COALESCE(e.truth_source, '') AS truth_source_at_eval,
          ev.result_home AS local_rh,
          ev.result_away AS local_ra,
          ev.status AS local_st,
          dp.sm_fixture_id
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        INNER JOIN bt2_shadow_pick_eval e ON e.shadow_daily_pick_id = dp.id
        LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
        WHERE r.run_family = %s AND r.selection_source = %s
          AND e.eval_status IN ('hit', 'miss')
        ORDER BY e.eval_status, dp.id
        """,
        (RUN_FAMILY, SELECTION_SOURCE),
    )
    scored = list(cur.fetchall() or [])
    hits = [x for x in scored if x["eval_status"] == "hit"]
    misses = [x for x in scored if x["eval_status"] == "miss"]
    sample_h = hits[:8]
    sample_m = misses[:8]
    scored_sample = sample_h + sample_m

    sf_scored = {int(x["sm_fixture_id"]) for x in scored_sample if x.get("sm_fixture_id")}
    sm_scored_map = _fetch_sm_raw(sf_scored)

    reliability_rows: list[dict[str, Any]] = []
    for x in scored_sample:
        smid = int(x["sm_fixture_id"]) if x.get("sm_fixture_id") is not None else None
        sm = sm_scored_map.get(smid or -1, {}) if smid else {}
        lh, la = x.get("local_rh"), x.get("local_ra")
        sh, sa = sm.get("sm_result_home"), sm.get("sm_result_away")
        agree = None
        if lh is not None and la is not None and sm.get("sm_has_ft_score"):
            agree = int(lh) == int(sh) and int(la) == int(sa)
        reliability_rows.append(
            {
                "shadow_daily_pick_id": x["shadow_daily_pick_id"],
                "eval_status": x["eval_status"],
                "truth_source_at_eval": x["truth_source_at_eval"],
                "local_result_home": lh,
                "local_result_away": la,
                "local_event_status": x.get("local_st"),
                "sm_fixture_id": smid,
                "sm_result_home_fresh": sh,
                "sm_result_away_fresh": sa,
                "sm_has_ft_score_fresh": sm.get("sm_has_ft_score"),
                "scores_local_vs_sm_agree": agree,
            }
        )

    cur.close()
    conn.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = list(audit_csv[0].keys()) if audit_csv else []
    with (OUT_DIR / "dsr_pending_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in audit_csv:
            w.writerow(row)

    truth_source_counts = Counter(str(r.get("truth_source_at_eval") or "") for r in audit_csv)
    summary = {
        "generated_at_utc": now.isoformat(),
        "run_family": RUN_FAMILY,
        "selection_source": SELECTION_SOURCE,
        "pending_count": len(pending_rows),
        "truth_source_at_eval_counts": dict(truth_source_counts),
        "root_cause_distribution": dict(root_counts),
        "reconciliation_surface": {
            "pending_with_merge_ft_available_now": reconcile_merge_ft,
            "note": "Simula el mismo merge que el evaluador (local + fallback SM). Si >0, un rerun de "
            "scripts/bt2_shadow_evaluate_performance.py con --run-key del baseline debería "
            "convertir esos casos de pending a hit/miss/void (no productivo).",
        },
        "sportmonks_api": {
            "key_configured": bool((bt2_settings.sportmonks_api_key or "").strip()),
            "fixtures_fetched_pending": len(fids),
        },
    }
    (OUT_DIR / "dsr_pending_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (OUT_DIR / "dsr_sportmonks_historical_reliability_check.csv").open("w", encoding="utf-8", newline="") as f:
        fn = list(reliability_rows[0].keys()) if reliability_rows else [
            "shadow_daily_pick_id",
            "eval_status",
            "truth_source_at_eval",
            "local_result_home",
            "local_result_away",
            "local_event_status",
            "sm_fixture_id",
            "sm_result_home_fresh",
            "sm_result_away_fresh",
            "sm_has_ft_score_fresh",
            "scores_local_vs_sm_agree",
        ]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in reliability_rows:
            w.writerow(row)

    agre_ok = sum(1 for r in reliability_rows if r.get("scores_local_vs_sm_agree") is True)
    agre_bad = sum(1 for r in reliability_rows if r.get("scores_local_vs_sm_agree") is False)
    agre_unk = sum(1 for r in reliability_rows if r.get("scores_local_vs_sm_agree") is None)

    # Estrategia markdown
    strategy_md = f"""# Estrategia de settlement — baseline DSR native (shadow)

Generado: `{now.isoformat()}`  
Ámbito: `run_family=shadow_dsr_replay_native`, `selection_source=dsr_api_only` (no productivo).

## 1. Niveles de verdad (política operativa)

| Nivel | Definición | Uso |
|-------|------------|-----|
| **Cierre oficial** | `bt2_events` (CDM local) con `result_home`/`result_away` y estado coherente con final; o verificación SM con HTTP 200 y `sm_has_ft_score` tras merge idéntico al job `bt2_shadow_evaluate_performance`. | Única base para `hit`/`miss`/`void` en eval shadow persistida. |
| **Resultado visible no oficial** | SM (o local) con FT en UI de diagnóstico pero sin pasar reglas de consistencia (p. ej. contradicción local vs SM). | Mostrar como “preliminar” en auditoría; no mover `eval_status` sin regla. |
| **Pending recheck** | `eval_status=pending_result` y merge simulado aún sin par FT; o kickoff en ventana natural. | Job diario: re-ejecutar evaluador con fallback SM; escalar tras N días. |
| **Revisión manual necesaria** | Contradicción local vs SM; `bt2_event_id` NULL; API SM con error de plan/suscripción. | Lista corta; decisión documentada (qué fuente manda y por qué). |
| **Cierre manual auditado** | Override explícito en herramienta interna con log (usuario, timestamp, motivo, fuente). | Solo si APIs y CDM no convergen y el partido es inequívoco en fuente externa puntual. |

## 2. Aterrizaje a esta auditoría (N={len(pending_rows)} pending)

- **Causas raíz (conteo)**: ver `dsr_pending_summary.json` → `root_cause_distribution`.
- **Cierre automático seguro (shadow)**: re-ejecutar `python3 scripts/bt2_shadow_evaluate_performance.py --run-key <run_key>` para el run del baseline. No cambia T-60 ni productión; solo reescribe `bt2_shadow_pick_eval`.
- **Capa resoluble hoy con merge SM**: `pending_with_merge_ft_available_now` = **{reconcile_merge_ft}** (si SM devolvió FT y el merge llena ambos goles). Es el techo inmediato si el API key tiene acceso a resultados.

## 3. Qué no relajar

- No tratar `pending` como miss ni hit.
- No usar solo “estado” sin par de goles para 1X2 H2H.
- No aceptar SM si contradice local salvo regla explícita de precedencia documentada.

## 4. Recheck (diseño ejecutable)

1. **Fin de día**: cron/dev manual — `bt2_shadow_evaluate_performance.py` con `--run-key` del native full.
2. **Histórico**: mismos fixtures con `kickoff_utc` > 48h y aún pending → revisar `sm_error_message` (suscripción) vs datos.
3. **Fallback SM**: ya implementado en el evaluador; la deuda es principalmente completitud CDM y límites del plan SM.

## 5. Control SportMonks vs local (muestra scored)

- Filas en `dsr_sportmonks_historical_reliability_check.csv`: **{len(reliability_rows)}** (8 hit + 8 miss máx).
- Acuerdo local vs SM (fresh): **coinciden={agre_ok}, discordancia={agre_bad}, sin comparación posible={agre_unk}**.

---

Documento vivo; el CSV `dsr_pending_audit.csv` es la fuente detallada por pick.
"""
    (OUT_DIR / "dsr_settlement_strategy.md").write_text(strategy_md, encoding="utf-8")

    print(json.dumps({"ok": True, "pending": len(pending_rows), "summary_path": str(OUT_DIR / "dsr_pending_summary.json")}, indent=2))


if __name__ == "__main__":
    main()
