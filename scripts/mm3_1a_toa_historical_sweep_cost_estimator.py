#!/usr/bin/env python3
"""
MM-3.1A — TOA Historical Odds Sweep Cost Estimator + Pilot Plan (read-only DB por defecto).

- Inventario Big 5 desde bt2_events (SELECT).
- Estima requests/créditos para GET /v4/historical/odds (featured) según política de snapshot.
- Fórmula featured histórico: credits_per_request = 10 × n_regions × n_mercados (un request = un timestamp).

Piloto HTTP solo con --allow-toa-api y --no-dry-run (y request-cap).

Salidas: scripts/outputs/mm3_1a_*.csv|json y audit markdown en docs/bettracker2/audits/.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "scripts" / "outputs"
AUDIT_PATH = REPO / "docs" / "bettracker2" / "audits" / "MM3_1A_TOA_HISTORICAL_SWEEP_COST_ESTIMATOR_AUDIT.md"

BIG5_SM_LEAGUE_IDS = frozenset({8, 564, 82, 384, 301})

# sm_league_id -> TOA sport_key (centralizado)
try:
    from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID
except ImportError:
    sys.path.insert(0, str(REPO))
    from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID

ODDS_HISTORICAL_PATH = "https://api.the-odds-api.com/v4/historical/sports/{sport}/odds"

MM28C_ARTIFACTS = [
    REPO / "scripts" / "outputs" / "bt2_vendor_lab_day1" / "toa_credit_usage_summary.json",
    REPO / "scripts" / "outputs" / "bt2_vendor_readiness" / "the_odds_api_credit_estimator.csv",
]

CREDITS_PER_FEATURED_REQUEST_BASE = 10

P2_MARKETS_ESTIMATE = ("btts", "corners", "cards", "team_totals", "additional_other")


def _load_bt2_database_url() -> str:
    url = (os.environ.get("BT2_DATABASE_URL") or "").strip().strip('"').strip("'")
    if url:
        return url
    env_path = REPO / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("BT2_DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        print("Falta BT2_DATABASE_URL en entorno o .env", file=sys.stderr)
        sys.exit(1)
    return url


def _load_theoddsapi_key() -> str:
    try:
        from apps.api.bt2_settings import bt2_settings

        k = (bt2_settings.theoddsapi_key or "").strip()
        if k:
            return k
    except Exception:
        pass
    k = (os.environ.get("THEODDSAPI_KEY") or "").strip()
    if k:
        return k
    env_path = REPO / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("THEODDSAPI_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return k


def _sync_dsn(url: str) -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url, flags=re.I)


def _ensure_out() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h) for h in headers})


def _json_safe(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    return obj


def _norm_team(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    for tok in (" fc", " cf", " afc", " sc", " ac"):
        if s.endswith(tok):
            s = s[: -len(tok)].strip()
    return s


def _zone(tz_name: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(tz_name)
    except Exception as exc:
        print(f"Timezone inválida: {tz_name}: {exc}", file=sys.stderr)
        sys.exit(1)


def snapshot_offsets_for_policy(policy: str) -> list[timedelta]:
    """Offsets from kickoff (negative = before KO)."""
    p = policy.strip().lower()
    if p == "closing_approx":
        return [timedelta(minutes=-3)]
    if p == "t60":
        return [timedelta(minutes=-60)]
    if p == "t24":
        return [timedelta(hours=-24)]
    if p in ("t24_t60", "t24+t60"):
        return [timedelta(hours=-24), timedelta(minutes=-60)]
    if p == "multi":
        return [
            timedelta(hours=-24),
            timedelta(hours=-6),
            timedelta(hours=-1),
            timedelta(minutes=-2),
        ]
    print(f"snapshot-policy desconocida: {policy}", file=sys.stderr)
    sys.exit(1)


def credits_per_featured_request(n_regions: int, n_markets: int) -> int:
    return CREDITS_PER_FEATURED_REQUEST_BASE * n_regions * n_markets


def load_previous_observed_cost() -> dict[str, Any]:
    out: dict[str, Any] = {
        "artifact_paths_checked": [str(p) for p in MM28C_ARTIFACTS],
        "previous_observed_cost_per_request": None,
        "previous_observed_cost_per_historical_event_odds_call": None,
        "lab_historical_event_odds_avg_x_requests_last": None,
        "notes": [],
    }
    js = MM28C_ARTIFACTS[0]
    if js.is_file():
        try:
            data = json.loads(js.read_text(encoding="utf-8"))
            lasts: list[float] = []
            for c in data.get("calls") or []:
                if (c.get("step") or "") == "historical_event_odds":
                    try:
                        lasts.append(float(c.get("x-requests-last") or 0))
                    except (TypeError, ValueError):
                        pass
            if lasts:
                avg_last = sum(lasts) / len(lasts)
                out["previous_observed_cost_per_historical_event_odds_call"] = avg_last
                out["lab_historical_event_odds_avg_x_requests_last"] = avg_last
                out["notes"].append(
                    "Lab vendor day1: historical_event_odds (P2-style) observó x-requests-last≈10 "
                    "por llamada (1 mercado × 1 región); no es el mismo endpoint que historical/odds featured."
                )
        except Exception as exc:
            out["notes"].append(f"Error leyendo {js}: {exc}")
    else:
        out["notes"].append(f"No existe {js} (MM-2.8C.2/C.4 proxy opcional).")
    # Featured: teoría 10×R×M por request — sin artifact directo; usar como null y documentar.
    out["previous_observed_cost_per_request"] = None
    return out


@dataclass
class FixtureRow:
    event_id: int
    sportmonks_fixture_id: int
    sm_league_id: int
    league_name: str
    toa_sport_key: str
    kickoff_utc: datetime
    status: str
    result_home: int | None
    result_away: int | None
    season: str | None
    home_team: str
    away_team: str


def fetch_fixtures(cur, date_from: date | None, date_to: date | None) -> list[FixtureRow]:
    cur.execute(
        """
        SELECT
          e.id AS event_id,
          e.sportmonks_fixture_id,
          l.sportmonks_id AS sm_league_id,
          l.name AS league_name,
          e.kickoff_utc,
          e.status,
          e.result_home,
          e.result_away,
          e.season,
          th.name AS home_team,
          ta.name AS away_team
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE l.sportmonks_id = ANY(%s::int[])
          AND e.kickoff_utc IS NOT NULL
        ORDER BY e.kickoff_utc
        """,
        (list(BIG5_SM_LEAGUE_IDS),),
    )
    rows: list[FixtureRow] = []
    for r in cur.fetchall():
        d = dict(r)
        ko = d["kickoff_utc"]
        if ko is None:
            continue
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        ko_utc_d = ko.astimezone(timezone.utc).date()
        if date_from and ko_utc_d < date_from:
            continue
        if date_to and ko_utc_d > date_to:
            continue
        sm_id = int(d["sm_league_id"])
        sk = TOA_SPORT_KEYS_BY_SM_LEAGUE_ID.get(sm_id)
        if not sk:
            continue
        rows.append(
            FixtureRow(
                event_id=int(d["event_id"]),
                sportmonks_fixture_id=int(d["sportmonks_fixture_id"]),
                sm_league_id=sm_id,
                league_name=str(d["league_name"] or ""),
                toa_sport_key=sk,
                kickoff_utc=ko,
                status=str(d["status"] or ""),
                result_home=d.get("result_home"),
                result_away=d.get("result_away"),
                season=str(d["season"]) if d.get("season") is not None else None,
                home_team=str(d["home_team"] or ""),
                away_team=str(d["away_team"] or ""),
            )
        )
    return rows


def build_inventory_csv_rows(fixtures: list[FixtureRow], tz) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inv: list[dict[str, Any]] = []
    by_day_sk: dict[tuple[str, str], int] = defaultdict(int)
    span_min: datetime | None = None
    span_max: datetime | None = None
    for f in fixtures:
        ko = f.kickoff_utc.astimezone(tz)
        local_d = ko.date().isoformat()
        y, m = ko.year, ko.month
        has_res = f.result_home is not None and f.result_away is not None
        inv.append(
            {
                "event_id": f.event_id,
                "sportmonks_fixture_id": f.sportmonks_fixture_id,
                "sm_league_id": f.sm_league_id,
                "league_name": f.league_name,
                "toa_sport_key": f.toa_sport_key,
                "kickoff_utc": f.kickoff_utc.isoformat(),
                "kickoff_local": ko.isoformat(),
                "local_kickoff_date": local_d,
                "calendar_year": y,
                "calendar_month": m,
                "season_cdm": f.season or "",
                "status": f.status,
                "result_available": has_res,
                "result_home": f.result_home if has_res else "",
                "result_away": f.result_away if has_res else "",
                "home_team": f.home_team,
                "away_team": f.away_team,
            }
        )
        by_day_sk[(local_d, f.toa_sport_key)] += 1
        span_min = f.kickoff_utc if span_min is None or f.kickoff_utc < span_min else span_min
        span_max = f.kickoff_utc if span_max is None or f.kickoff_utc > span_max else span_max

    summary = {
        "n_fixtures": len(fixtures),
        "kickoff_utc_min": span_min.isoformat() if span_min else None,
        "kickoff_utc_max": span_max.isoformat() if span_max else None,
        "n_local_day_sport_key_buckets": len(by_day_sk),
        "events_per_local_day_sport_key_sample": [
            {"local_kickoff_date": k[0], "toa_sport_key": k[1], "n_events": v}
            for k, v in sorted(by_day_sk.items())[:40]
        ],
    }
    return inv, summary


def compute_deduped_requests(
    fixtures: list[FixtureRow],
    policy: str,
) -> set[tuple[str, str]]:
    """Set of (toa_sport_key, snapshot_iso_z) unique API calls."""
    offsets = snapshot_offsets_for_policy(policy)
    keys: set[tuple[str, str]] = set()
    for f in fixtures:
        ko = f.kickoff_utc
        for off in offsets:
            ts = ko + off
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            iso = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            keys.add((f.toa_sport_key, iso))
    return keys


def snapshot_plan_rows(
    fixtures: list[FixtureRow],
    policy: str,
    n_markets: int,
    n_regions: int,
    tz,
) -> list[dict[str, Any]]:
    offsets = snapshot_offsets_for_policy(policy)
    # group by local kickoff date
    by_day: dict[tuple[str, str], list[FixtureRow]] = defaultdict(list)
    for f in fixtures:
        local_d = f.kickoff_utc.astimezone(tz).date().isoformat()
        by_day[(local_d, f.toa_sport_key)].append(f)

    cpr = credits_per_featured_request(n_regions, n_markets)
    out_rows: list[dict[str, Any]] = []
    for (local_d, sk), evs in sorted(by_day.items()):
        kset: set[tuple[str, str]] = set()
        for f in evs:
            for off in offsets:
                ts = f.kickoff_utc + off
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                iso = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                kset.add((f.toa_sport_key, iso))
        nreq = len(kset)
        out_rows.append(
            {
                "snapshot_policy": policy,
                "toa_sport_key": sk,
                "local_kickoff_date": local_d,
                "n_events_kickoff_this_local_day": len(evs),
                "n_distinct_snapshot_requests": nreq,
                "n_markets": n_markets,
                "n_regions": n_regions,
                "estimated_requests": nreq,
                "estimated_credits": nreq * cpr,
            }
        )
    return out_rows


def scenario_definitions() -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": "A",
            "label": "P0 h2h+totals, 1 región, T-60",
            "markets": ["h2h", "totals"],
            "regions": ["eu"],
            "snapshot_policy": "t60",
        },
        {
            "scenario_id": "B",
            "label": "P0 h2h+totals, 1 región, T-24 + T-60",
            "markets": ["h2h", "totals"],
            "regions": ["eu"],
            "snapshot_policy": "t24_t60",
        },
        {
            "scenario_id": "C",
            "label": "P0+P1 h2h+totals+spreads, 1 región, T-60 (solo estimación)",
            "markets": ["h2h", "totals", "spreads"],
            "regions": ["eu"],
            "snapshot_policy": "t60",
        },
        {
            "scenario_id": "D",
            "label": "P0 h2h+totals, 2 regiones, T-60",
            "markets": ["h2h", "totals"],
            "regions": ["eu", "uk"],
            "snapshot_policy": "t60",
        },
        {
            "scenario_id": "E",
            "label": "P0 h2h+totals, 1 región, multi-snapshot",
            "markets": ["h2h", "totals"],
            "regions": ["eu"],
            "snapshot_policy": "multi",
        },
        {
            "scenario_id": "F",
            "label": "P2 additional/event-level (solo estimación, no ejecutar)",
            "markets": list(P2_MARKETS_ESTIMATE),
            "regions": ["eu"],
            "snapshot_policy": "t60",
            "cost_model": "additional_event_markets",
        },
    ]


def estimate_scenario(
    fixtures: list[FixtureRow],
    markets: list[str],
    regions: list[str],
    policy: str,
    cost_model: str,
) -> dict[str, Any]:
    n_markets = len(markets)
    n_regions = len(regions)
    if cost_model == "additional_event_markets":
        n_events = len(fixtures)
        ec = CREDITS_PER_FEATURED_REQUEST_BASE * n_regions * n_markets * n_events
        return {
            "n_events": n_events,
            "estimated_requests": n_events,
            "estimated_credits": ec,
            "cost_model": cost_model,
        }
    keys = compute_deduped_requests(fixtures, policy)
    nreq = len(keys)
    cpr = credits_per_featured_request(n_regions, n_markets)
    return {
        "n_events": len(fixtures),
        "estimated_requests": nreq,
        "estimated_credits": nreq * cpr,
        "cost_model": "featured_historical_odds",
    }


def build_batches(
    fixtures: list[FixtureRow],
    policy: str,
    markets: list[str],
    regions: list[str],
    tz,
    *,
    pilot_sport_key: str,
    pilot_max_local_days: int = 5,
    default_max_batch_days: int = 14,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Chunk por (sport_key, ventana local). El primer batch del `pilot_sport_key`
    usa como máximo `pilot_max_local_days` días calendario locales (piloto 3–5 días).
    """
    cpr = credits_per_featured_request(len(regions), len(markets))
    by_sk: dict[str, list[FixtureRow]] = defaultdict(list)
    for f in fixtures:
        by_sk[f.toa_sport_key].append(f)

    sport_order = sorted(by_sk.keys(), key=lambda sk: (0 if sk == pilot_sport_key else 1, sk))

    batches: list[dict[str, Any]] = []
    bid = 0
    pilot_rec: dict[str, Any] | None = None

    for sk in sport_order:
        evs = by_sk[sk]
        evs.sort(key=lambda x: x.kickoff_utc)
        if not evs:
            continue
        i = 0
        is_first_chunk_for_sk = True
        while i < len(evs):
            chunk = []
            start_local = evs[i].kickoff_utc.astimezone(tz).date()
            end_local = start_local
            j = i
            max_days = (
                pilot_max_local_days
                if sk == pilot_sport_key and is_first_chunk_for_sk
                else default_max_batch_days
            )
            is_first_chunk_for_sk = False
            while j < len(evs):
                dloc = evs[j].kickoff_utc.astimezone(tz).date()
                if (dloc - start_local).days >= max_days and chunk:
                    break
                chunk.append(evs[j])
                end_local = dloc
                j += 1
            keys = compute_deduped_requests(chunk, policy)
            nreq = len(keys)
            bid += 1
            row = {
                "batch_id": f"b{bid:04d}",
                "sport_key": sk,
                "date_range_local_start": start_local.isoformat(),
                "date_range_local_end": end_local.isoformat(),
                "markets": ",".join(markets),
                "region": ",".join(regions),
                "snapshot_policy": policy,
                "snapshot_count_basis": "distinct_sport_timestamp_queries",
                "estimated_requests": nreq,
                "estimated_credits": nreq * cpr,
                "stop_condition": "pause_if_rate_limit_or_budget;no_full_sweep_without_approval",
                "expected_output_path": f"scripts/outputs/mm3_1a_toa_historical_chunk_{sk}_{start_local}_{end_local}.jsonl",
                "is_pilot_candidate": bid == 1,
            }
            batches.append(row)
            if bid == 1:
                pilot_rec = dict(row)
                pilot_rec["pilot_note"] = (
                    "Primer batch operativo sugerido: una sola liga, ventana corta, "
                    f"máx {pilot_max_local_days} días locales; no mezclar ligas."
                )
            i = j
    return batches, pilot_rec or {}


def pick_pilot_dates(fixtures: list[FixtureRow], sport_key: str, n_days: int, tz) -> list[date]:
    sub = [f for f in fixtures if f.toa_sport_key == sport_key]
    counts: dict[date, int] = defaultdict(int)
    for f in sub:
        d = f.kickoff_utc.astimezone(tz).date()
        counts[d] += 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    out = [d for d, _ in ranked[:n_days]]
    out.sort()
    if len(out) < n_days:
        # relleno cronológico
        all_d = sorted({f.kickoff_utc.astimezone(tz).date() for f in sub})
        for d in all_d:
            if d not in out:
                out.append(d)
            if len(out) >= n_days:
                break
        out.sort()
    return out[:n_days]


def http_get_json(
    url: str, timeout: int = 45
) -> tuple[dict[str, Any] | list[Any], dict[str, str], int]:
    """
    GET JSON; 404 se trata como respuesta vacía (mismo criterio que theoddsapi_worker)
    para poder leer headers de facturación.
    """
    req = Request(url, headers={"User-Agent": "mm3-1a-toa-estimator/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            code = getattr(resp, "status", 200) or 200
            return json.loads(raw) if raw.strip() else {}, headers, int(code)
    except HTTPError as e:
        headers = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        if e.code == 404:
            try:
                raw = e.read().decode("utf-8")
                body = json.loads(raw) if raw.strip() else {}
            except (json.JSONDecodeError, ValueError):
                body = {}
            return body, headers, 404
        raise
    except URLError:
        raise


def run_pilot(
    fixtures: list[FixtureRow],
    sport_key: str,
    pilot_days: int,
    markets: list[str],
    regions: list[str],
    request_cap: int,
    policy: str,
) -> dict[str, Any]:
    api_key = _load_theoddsapi_key()
    if not api_key:
        return {"ok": False, "error": "THEODDSAPI_KEY vacío"}

    tz = _zone("America/Bogota")
    pdates = pick_pilot_dates(fixtures, sport_key, pilot_days, tz)
    pilot_fixtures = [f for f in fixtures if f.toa_sport_key == sport_key and f.kickoff_utc.astimezone(tz).date() in set(pdates)]
    keys = list(compute_deduped_requests(pilot_fixtures, policy))
    keys.sort()
    if len(keys) > request_cap:
        keys = keys[:request_cap]

    markets_param = ",".join(markets)
    regions_param = ",".join(regions)

    raw_calls: list[dict[str, Any]] = []
    headers_acc: list[dict[str, str]] = []
    total_last = 0.0
    errors: list[str] = []

    for sk, date_iso in keys:
        if sk != sport_key:
            continue
        params = {
            "apiKey": api_key,
            "regions": regions_param,
            "markets": markets_param,
            "dateFormat": "iso",
            "oddsFormat": "decimal",
            "date": date_iso,
        }
        url = ODDS_HISTORICAL_PATH.format(sport=sk) + "?" + urlencode(params)
        try:
            body, hdrs, status = http_get_json(url)
            raw_calls.append(
                {
                    "url": url.split("apiKey=")[0] + "apiKey=***",
                    "http_status": status,
                    "response": body,
                    "request_headers_echo": {},
                }
            )
            headers_acc.append(hdrs)
            try:
                total_last += float(hdrs.get("x-requests-last") or 0)
            except (TypeError, ValueError):
                pass
            if status in (401, 402, 403):
                errors.append(f"{date_iso}: HTTP {status} (sin acceso / plan)")
            elif status == 429:
                errors.append(f"{date_iso}: HTTP 429 rate limit")
        except Exception as exc:
            errors.append(f"{date_iso}: {exc}")

    out_raw = {
        "sport_key": sport_key,
        "pilot_local_dates": [d.isoformat() for d in pdates],
        "n_fixtures_in_pilot": len(pilot_fixtures),
        "requests_planned_before_cap": len(compute_deduped_requests(pilot_fixtures, policy)),
        "requests_executed": len(raw_calls),
        "calls": raw_calls,
        "errors": errors,
    }
    (OUT_DIR / "mm3_1a_toa_pilot_raw.json").write_text(
        json.dumps(_json_safe(out_raw), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    last_hdr = headers_acc[-1] if headers_acc else {}
    pilot_cost = {
        "requests_executed": len(raw_calls),
        "sum_x_requests_last": total_last,
        "last_x_requests_remaining": last_hdr.get("x-requests-remaining"),
        "last_x_requests_used": last_hdr.get("x-requests-used"),
        "avg_x_requests_last": (total_last / len(raw_calls)) if raw_calls else None,
    }
    (OUT_DIR / "mm3_1a_toa_pilot_cost.json").write_text(
        json.dumps(pilot_cost, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Match rows
    match_rows: list[dict[str, Any]] = []
    reject_rows: list[dict[str, Any]] = []

    def parse_commence(x: str) -> datetime | None:
        try:
            return datetime.fromisoformat(x.replace("Z", "+00:00"))
        except Exception:
            return None

    for call in raw_calls:
        body = call.get("response")
        events = []
        if isinstance(body, dict):
            ev = body.get("data")
            if isinstance(ev, list):
                events = ev
        for ev in events:
            if not isinstance(ev, dict):
                continue
            eid = str(ev.get("id") or "")
            h = str(ev.get("home_team") or "")
            a = str(ev.get("away_team") or "")
            ct = str(ev.get("commence_time") or "")
            ctd = parse_commence(ct)
            best: FixtureRow | None = None
            best_score = -1
            for f in pilot_fixtures:
                if ctd and f.kickoff_utc:
                    delta = abs((f.kickoff_utc - ctd).total_seconds())
                else:
                    delta = 999999
                sh = _norm_team(f.home_team) == _norm_team(h)
                sa = _norm_team(f.away_team) == _norm_team(a)
                score = (2 if sh and sa else 0) - min(delta, 3600) / 3600.0
                if score > best_score:
                    best_score = score
                    best = f
            if best and best_score >= 1.5:
                match_rows.append(
                    {
                        "bt2_event_id": best.event_id,
                        "toa_event_id": eid,
                        "sport_key": sport_key,
                        "kickoff_bt2_utc": best.kickoff_utc.isoformat(),
                        "commence_toa": ct,
                        "home_bt2": best.home_team,
                        "away_bt2": best.away_team,
                        "home_toa": h,
                        "away_toa": a,
                        "match_score": round(best_score, 4),
                    }
                )
            else:
                reject_rows.append(
                    {
                        "toa_event_id": eid,
                        "commence_toa": ct,
                        "home_toa": h,
                        "away_toa": a,
                        "reason": "no_confident_bt2_match",
                    }
                )

    _write_csv(
        OUT_DIR / "mm3_1a_toa_pilot_match_rows.csv",
        [
            "bt2_event_id",
            "toa_event_id",
            "sport_key",
            "kickoff_bt2_utc",
            "commence_toa",
            "home_bt2",
            "away_bt2",
            "home_toa",
            "away_toa",
            "match_score",
        ],
        match_rows,
    )
    _write_csv(
        OUT_DIR / "mm3_1a_toa_pilot_rejections.csv",
        ["toa_event_id", "commence_toa", "home_toa", "away_toa", "reason"],
        reject_rows,
    )

    return {
        "ok": len(errors) == 0 and len(raw_calls) > 0,
        "pilot_cost": pilot_cost,
        "n_matched": len(match_rows),
        "n_rejected": len(reject_rows),
        "errors": errors,
    }


def main() -> None:
    import psycopg2
    import psycopg2.extras

    p = argparse.ArgumentParser(description="MM-3.1A TOA historical sweep cost estimator")
    p.add_argument("--date-from", default="", help="YYYY-MM-DD filtro kickoff_utc (inclusive)")
    p.add_argument("--date-to", default="", help="YYYY-MM-DD filtro kickoff_utc (inclusive)")
    p.add_argument("--timezone", default="America/Bogota")
    p.add_argument("--markets", default="h2h,totals", help="Lista CSV mercados featured")
    p.add_argument("--regions", default="eu", help="Lista CSV regiones TOA")
    p.add_argument("--snapshot-policy", default="t60", dest="snapshot_policy")
    p.add_argument("--allow-toa-api", action="store_true")
    p.add_argument("--request-cap", type=int, default=20)
    p.add_argument("--no-dry-run", action="store_true", help="Permite HTTP piloto con --allow-toa-api")
    p.add_argument("--pilot-sport-key", default="soccer_epl")
    p.add_argument("--pilot-days", type=int, default=5)
    p.add_argument("--db-url", default="", help="Override BT2_DATABASE_URL")
    p.add_argument("--conservative-multiplier", type=float, default=1.15)
    p.add_argument(
        "--operational-credit-budget",
        type=float,
        default=0.0,
        help="Si >0, dispara balance_required_warning si estimación P0 t60 excede",
    )
    args = p.parse_args()

    dry_run = not args.no_dry_run
    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    if not markets or not regions:
        print("--markets y --regions requieren al menos un valor", file=sys.stderr)
        sys.exit(1)

    _ensure_out()
    dsn = _sync_dsn(args.db_url.strip() or _load_bt2_database_url())
    tz = _zone(args.timezone)

    date_from = date.fromisoformat(args.date_from) if args.date_from else None
    date_to = date.fromisoformat(args.date_to) if args.date_to else None

    print("MM3_1A: conectando Postgres (SELECT)…", flush=True)
    conn = psycopg2.connect(dsn, connect_timeout=30)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout TO 0")

    fixtures = fetch_fixtures(cur, date_from, date_to)
    conn.close()

    if not fixtures:
        print("Sin fixtures Big5 en rango; abortando.", file=sys.stderr)
        sys.exit(2)

    inv_rows, inv_summary = build_inventory_csv_rows(fixtures, tz)
    _write_csv(
        OUT_DIR / "mm3_1a_big5_fixture_inventory.csv",
        [
            "event_id",
            "sportmonks_fixture_id",
            "sm_league_id",
            "league_name",
            "toa_sport_key",
            "kickoff_utc",
            "kickoff_local",
            "local_kickoff_date",
            "calendar_year",
            "calendar_month",
            "season_cdm",
            "status",
            "result_available",
            "result_home",
            "result_away",
            "home_team",
            "away_team",
        ],
        inv_rows,
    )

    policy_main = args.snapshot_policy
    plan_rows = snapshot_plan_rows(
        fixtures, policy_main, len(markets), len(regions), tz
    )
    _write_csv(
        OUT_DIR / "mm3_1a_snapshot_plan_rows.csv",
        [
            "snapshot_policy",
            "toa_sport_key",
            "local_kickoff_date",
            "n_events_kickoff_this_local_day",
            "n_distinct_snapshot_requests",
            "n_markets",
            "n_regions",
            "estimated_requests",
            "estimated_credits",
        ],
        plan_rows,
    )

    keys_main = compute_deduped_requests(fixtures, policy_main)
    nreq_main = len(keys_main)
    cpr_main = credits_per_featured_request(len(regions), len(markets))
    ec_main = nreq_main * cpr_main

    prev = load_previous_observed_cost()
    budget = float(args.operational_credit_budget or 0.0)
    warn_budget = budget > 0 and ec_main > budget

    est_json = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_span": inv_summary,
        "current_selected_markets": markets,
        "regions": regions,
        "snapshot_policy": policy_main,
        "snapshot_count_distinct_requests": nreq_main,
        "credits_per_request_formula": "10 * n_regions * n_markets",
        "credits_per_request": cpr_main,
        "estimated_requests": nreq_main,
        "estimated_credits": ec_main,
        "previous_observed_from_artifacts": prev,
        "conservative_multiplier": args.conservative_multiplier,
        "estimated_credits_conservative": round(ec_main * args.conservative_multiplier, 2),
        "recommended_safe_batch_size_requests": max(1, min(50, int(nreq_main * 0.05) or 1)),
        "balance_required_warning": warn_budget,
        "operational_credit_budget": budget or None,
        "notes": [
            "Requests = pares únicos (toa_sport_key, snapshot_utc) con snapshot por política relativa a kickoff.",
            "closing_approx usa kickoff_utc - 3 min como proxy documentado de línea de cierre.",
            "P2/event odds es modelo distinto (10×R×M×eventos); ver scenario F.",
        ],
    }
    (OUT_DIR / "mm3_1a_cost_estimate.json").write_text(
        json.dumps(_json_safe(est_json), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # by_policy csv
    by_pol_rows: list[dict[str, Any]] = []
    for pol in ("closing_approx", "t60", "t24", "t24_t60", "multi"):
        k = compute_deduped_requests(fixtures, pol)
        nr = len(k)
        cpr = credits_per_featured_request(len(regions), len(markets))
        by_pol_rows.append(
            {
                "snapshot_policy": pol,
                "current_selected_markets": ",".join(markets),
                "regions": ",".join(regions),
                "snapshot_count": nr,
                "estimated_requests": nr,
                "estimated_credits": nr * cpr,
                "credits_per_request": cpr,
                "previous_observed_cost_per_request": prev.get("previous_observed_cost_per_request"),
                "lab_event_odds_avg_x_requests_last_mm28c_proxy": prev.get(
                    "lab_historical_event_odds_avg_x_requests_last"
                ),
                "conservative_multiplier": args.conservative_multiplier,
                "recommended_safe_batch_size_requests": max(1, min(50, int(nr * 0.05) or 1)),
                "balance_required_warning": budget > 0 and nr * cpr > budget,
            }
        )
    _write_csv(
        OUT_DIR / "mm3_1a_cost_estimate_by_policy.csv",
        [
            "snapshot_policy",
            "current_selected_markets",
            "regions",
            "snapshot_count",
            "estimated_requests",
            "estimated_credits",
            "credits_per_request",
            "previous_observed_cost_per_request",
            "lab_event_odds_avg_x_requests_last_mm28c_proxy",
            "conservative_multiplier",
            "recommended_safe_batch_size_requests",
            "balance_required_warning",
        ],
        by_pol_rows,
    )

    scen_out: list[dict[str, Any]] = []
    for s in scenario_definitions():
        cm = s.get("cost_model") or "featured_historical_odds"
        est = estimate_scenario(fixtures, s["markets"], s["regions"], s["snapshot_policy"], cm)
        scen_out.append(
            {
                "scenario_id": s["scenario_id"],
                "label": s["label"],
                "markets": ",".join(s["markets"]),
                "regions": ",".join(s["regions"]),
                "snapshot_policy": s["snapshot_policy"],
                "cost_model": cm,
                **{k: est[k] for k in ("estimated_requests", "estimated_credits", "n_events") if k in est},
            }
        )
    _write_csv(
        OUT_DIR / "mm3_1a_scenario_estimates.csv",
        [
            "scenario_id",
            "label",
            "markets",
            "regions",
            "snapshot_policy",
            "cost_model",
            "n_events",
            "estimated_requests",
            "estimated_credits",
        ],
        scen_out,
    )

    batches, pilot_batch_rec = build_batches(
        fixtures,
        policy_main,
        markets,
        regions,
        tz,
        pilot_sport_key=args.pilot_sport_key,
        pilot_max_local_days=min(5, max(3, args.pilot_days)),
    )
    (OUT_DIR / "mm3_1a_backfill_batches.json").write_text(
        json.dumps(
            _json_safe({"pilot_batch_recommended": pilot_batch_rec, "batches": batches}),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    toa_pilot_executed = False
    pilot_result: dict[str, Any] = {}
    if args.allow_toa_api and not dry_run:
        print("MM3_1A: ejecutando piloto TOA (historical/odds)…", flush=True)
        pilot_result = run_pilot(
            fixtures,
            args.pilot_sport_key,
            min(max(3, args.pilot_days), 5),
            markets=["h2h", "totals"],
            regions=["eu"],
            request_cap=args.request_cap,
            policy="t60",
        )
        toa_pilot_executed = bool(pilot_result.get("ok"))
    elif args.allow_toa_api and dry_run:
        print("MM3_1A: --allow-toa-api sin --no-dry-run → no HTTP (solo artefactos).", flush=True)

    # Reconciliation + readiness
    t60_row = next((x for x in scen_out if x["scenario_id"] == "A"), {})
    multi_row = next((x for x in scen_out if x["scenario_id"] == "E"), {})

    recon: dict[str, Any] = {
        "pilot_executed": toa_pilot_executed,
        "theoretical_credits_per_request_t60_p0": credits_per_featured_request(1, 2),
        "notes": [],
    }
    if toa_pilot_executed and pilot_result:
        pc = pilot_result.get("pilot_cost") or {}
        exec_req = int(pc.get("requests_executed") or 0)
        sum_last = float(pc.get("sum_x_requests_last") or 0)
        obs_per_req = (sum_last / exec_req) if exec_req else None
        recon["observed_avg_x_requests_last"] = obs_per_req
        recon["observed_cost_per_market_region_snapshot"] = (
            (sum_last / exec_req) / max(1, 2 * 1) if exec_req else None
        )
        recon["theoretical_requests"] = exec_req
        recon["theoretical_credits_linear"] = exec_req * credits_per_featured_request(1, 2)
        if obs_per_req is not None:
            close = abs(obs_per_req - credits_per_featured_request(1, 2)) <= 2.0
            recon["cost_formula_confirmed"] = close
            recon["observed_cost_per_snapshot"] = obs_per_req
            recon["notes"].append(
                "x-requests-last promedio vs 10×R×M: si difiere, TOA puede contar fraccional distinto o headers no alineados a créditos de facturación."
            )
    else:
        recon["observed_avg_x_requests_last"] = None
        recon["cost_formula_confirmed"] = False
        recon["notes"].append("Sin piloto ejecutado: reconciliación pendiente.")

    (OUT_DIR / "mm3_1a_cost_reconciliation.json").write_text(
        json.dumps(recon, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ready_for_full = False
    readiness = {
        "MM3_1a_cost_estimator_completed": True,
        "TOA_pilot_executed": toa_pilot_executed,
        "estimated_full_p0_t60_credits": float(t60_row.get("estimated_credits") or 0),
        "estimated_full_p0_multi_snapshot_credits": float(multi_row.get("estimated_credits") or 0),
        "observed_pilot_cost": pilot_result.get("pilot_cost") if pilot_result else None,
        "cost_formula_confirmed": recon.get("cost_formula_confirmed", False),
        "recommended_first_production_batch": pilot_batch_rec or (batches[0] if batches else None),
        "ready_for_full_backfill": ready_for_full,
        "ready_for_full_backfill_gates": [
            "piloto ejecutado exitosamente",
            "costo real razonable vs estimación",
            "sin errores críticos de proveedor",
            "plan de batches presente",
            "costo total dentro de presupuesto",
            "aprobación explícita del usuario (instrucción posterior)",
        ],
    }
    (OUT_DIR / "mm3_1a_sweep_readiness.json").write_text(
        json.dumps(_json_safe(readiness), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    scen_md = "\n".join(
        ["| Escenario | Mercados | Regiones | Política | Requests | Créditos |", "|---|---|---|---:|---:|---:|"]
        + [
            f"| {x['scenario_id']} | {x['markets']} | {x['regions']} | {x['snapshot_policy']} | "
            f"{x['estimated_requests']} | {x['estimated_credits']} |"
            for x in scen_out
        ]
    )

    # Audit markdown (conciso, datos enlazados a CSV/JSON)
    pilot_status = "Ejecutado" if toa_pilot_executed else ("Omitido (dry-run o sin --no-dry-run)" if not args.allow_toa_api else "Fallido o sin llamadas")
    audit = f"""# MM-3.1A — TOA Historical Sweep Cost Estimator (Audit)

## 1. Executive summary

- Universo Big 5 en DB local: **{inv_summary["n_fixtures"]}** eventos con kickoff en rango filtrado.
- Kickoff UTC (min/max): `{inv_summary.get("kickoff_utc_min")}` → `{inv_summary.get("kickoff_utc_max")}`.
- **Créditos estimados (P0 h2h+totals, eu, política `{policy_main}`)**: **{ec_main}** ({nreq_main} requests × {cpr_main} créditos/request).
- Política recomendada para empezar: **T-60** (un snapshot prepartido estable por evento, alineado al laboratorio SM LBU).
- Piloto seguro: **1 liga** (`{args.pilot_sport_key}`), **3–5 días** calendario locales con volumen, **h2h+totals**, **eu**, **T-60**, **request_cap** bajo.
- **¿Listos para backfill mayor?** **No** por defecto (`ready_for_full_backfill=false`); falta piloto exitoso + reconciliación + aprobación explícita.

## 2. Why TOA sweep is needed

`bt2_odds_snapshot` batch no provee `fetched_at` ROI-safe prematch (MM-3.0A). TOA `historical/odds` permite snapshots en timestamps explícitos prepartido.

## 3. Inputs used

- `bt2_events` + `bt2_leagues` + `bt2_teams` (SELECT).
- Mapeo TOA: `apps/api/bt2_theoddsapi_mapping.py`.
- Flags: markets={markets}, regions={regions}, timezone={args.timezone}, policy={policy_main}.
- Artefactos previos opcionales: `scripts/outputs/bt2_vendor_lab_day1/toa_credit_usage_summary.json`.

## 4. Fixture inventory

Archivo: `scripts/outputs/mm3_1a_big5_fixture_inventory.csv`.

## 5. Market priorities

- P0: h2h, totals (ejecución estimada / piloto).
- P1: spreads (solo escenarios CSV).
- P2: BTTS, corners, cards, team_totals (scenario F, costo event-level estimado).

## 6. Snapshot policies

- `closing_approx`: kickoff − 3 min (proxy documentado).
- `t60`, `t24`, `t24_t60`, `multi` (T-24 + T-6 + T-1h + cierre-2min).

## 7. Cost formula

Featured `GET /v4/historical/odds`: **créditos = 10 × regiones × mercados × requests**, donde cada **request** es un par único `(sport_key, timestamp_utc)` (deduplicado). Con 2 mercados (h2h+totals) y 1 región (eu) ⇒ **20 créditos por request**.

Para políticas con un solo offset por evento (`closing_approx`, `t60`, `t24`), si los timestamps resultantes no colisionan entre partidos, **requests ≈ número de eventos** (en este inventario: **{nreq_main}** ≈ **{inv_summary["n_fixtures"]}** eventos). `t24_t60` y `multi` suman offsets y luego deduplican ⇒ más requests.

P2 event-level / additional markets (escenario F): **10 × R × M × eventos** (estimación conservadora de orden de magnitud; no ejecutado).

## 8. Scenario estimates

`scripts/outputs/mm3_1a_scenario_estimates.csv`.

{scen_md}

## 9. Recommended pilot

- `{args.pilot_sport_key}`, 3–5 días locales, h2h+totals, eu, T-60, cap {args.request_cap}.
- Comando: `python3 scripts/mm3_1a_toa_historical_sweep_cost_estimator.py --allow-toa-api --no-dry-run --request-cap {args.request_cap}`

## 10. Batch plan

- `scripts/outputs/mm3_1a_backfill_batches.json` incluye `pilot_batch_recommended` + `batches`.
- Primer batch sugerido (piloto): `{pilot_batch_rec.get("sport_key", "")}` ventana local `{pilot_batch_rec.get("date_range_local_start", "")}` → `{pilot_batch_rec.get("date_range_local_end", "")}`, ~**{pilot_batch_rec.get("estimated_requests", 0)}** requests, ~**{pilot_batch_rec.get("estimated_credits", 0)}** créditos (política `{policy_main}` actual).

## 11. Pilot execution status

{pilot_status}

## 12. Cost reconciliation

`scripts/outputs/mm3_1a_cost_reconciliation.json`.

## 13. Sweep readiness

`scripts/outputs/mm3_1a_sweep_readiness.json`.

## 14. Risks

- Mismatch equipos BT2 ↔ TOA; líneas ausentes en timestamp; costo real vs `x-requests-last`; rate limits.

## 15. Recommended next step

1. Ejecutar piloto con `--allow-toa-api --no-dry-run` y revisar `mm3_1a_cost_reconciliation.json`.
2. Ajustar batch size según headers reales.
3. Solicitar aprobación explícita antes de cualquier backfill amplio.
"""
    AUDIT_PATH.write_text(audit, encoding="utf-8")

    print("MM3_1A: artefactos escritos en scripts/outputs/ y", AUDIT_PATH, flush=True)


if __name__ == "__main__":
    main()
