#!/usr/bin/env python3
"""
Diagnóstico SportMonks — mismas rutas que el monitor admin (between + GET por id).

Uso (desde la raíz del repo):
  python scripts/bt2_sm_diagnostic_monitor_fixtures.py
  python scripts/bt2_sm_diagnostic_monitor_fixtures.py --fixture-id 19427731

Lee SPORTMONKS_API_KEY desde .env en la raíz. No imprime la clave.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from dotenv import load_dotenv

load_dotenv(_repo_root / ".env")

from apps.api.bt2_sportmonks_bulk import fetch_fixtures_between_dates
from apps.api.bt2_sportmonks_includes import BT2_SM_FIXTURE_INCLUDES

# IDs típicos del log monitor (actualizar si hace falta)
DEFAULT_FIXTURE_IDS = (
    19427731,
    19425205,
    19425516,
    19645464,
    19645463,
    19502708,
    19636308,
    19636303,
    19636311,
    19636312,
    19636305,
    19636310,
    19645016,
    19443194,
)

SM_BASE = "https://api.sportmonks.com/v3/football/fixtures"


def _print_json_snippet(label: str, obj: object, max_len: int = 900) -> None:
    try:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        s = s[:max_len] + "\n… [truncado]"
    print(f"\n--- {label} ---\n{s}")


def probe_get_raw(fixture_id: int, api_key: str, include: str | None) -> None:
    """GET manual: una petición, sin degradación (para ver respuesta cruda)."""
    params: dict[str, str] = {"api_token": api_key}
    if include:
        params["include"] = include
    qs = urlencode(params)
    url = f"{SM_BASE}/{int(fixture_id)}?{qs}"
    print(f"\n>>> GET (raw) fixture={fixture_id} include={'(vacío)' if not include else include[:60]+'…'}")
    print(f"    URL (sin token): {SM_BASE}/{fixture_id}?api_token=***&include=…")
    try:
        req = Request(url, headers={"Accept": "application/json"}, method="GET")
        with urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.getcode()
    except HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", errors="replace")
    print(f"    HTTP {code}")
    try:
        parsed = json.loads(raw)
        _print_json_snippet("cuerpo JSON", parsed)
        d = parsed.get("data") if isinstance(parsed, dict) else None
        print(f"    data es dict: {isinstance(d, dict)} | message: {parsed.get('message') if isinstance(parsed, dict) else None}")
    except json.JSONDecodeError:
        print(f"    body texto: {raw[:600]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnóstico SM fixture / between (monitor)")
    ap.add_argument(
        "--fixture-id",
        type=int,
        action="append",
        dest="fixture_ids",
        help="Repetible. Default: lista del último log monitor.",
    )
    ap.add_argument(
        "--between-from",
        default="2026-04-17",
        help="Fecha inicio ISO (between), default ventana ±3 desde HOY diagnóstico",
    )
    ap.add_argument(
        "--between-to",
        default="2026-04-23",
        help="Fecha fin ISO (between)",
    )
    args = ap.parse_args()

    key = (os.getenv("SPORTMONKS_API_KEY") or "").strip()
    if not key:
        print("ERROR: SPORTMONKS_API_KEY ausente o vacío en .env")
        sys.exit(2)
    print(f"SPORTMONKS_API_KEY cargada (longitud {len(key)})")

    ids = list(args.fixture_ids) if args.fixture_ids else list(DEFAULT_FIXTURE_IDS)

    # 1) Between (como bulk monitor)
    from datetime import date

    d0 = date.fromisoformat(args.between_from)
    d1 = date.fromisoformat(args.between_to)
    print(f"\n=== BULK between {d0} … {d1} (misma lógica que bt2_sportmonks_bulk) ===")
    bulk_map, notes, nreq = fetch_fixtures_between_dates(d0, d1, key)
    print(f"requests HTTP: {nreq}")
    for n in notes[:8]:
        print(f"  note: {n}")
    print(f"fixtures distintos en mapa: {len(bulk_map)}")
    sample_keys = sorted(bulk_map.keys())[:20]
    print(f"primeros IDs en mapa: {sample_keys}")

    # 2) Por cada ID pedido: ¿está en bulk? + GET crudo mínimo + GET con includes BT2
    inc_short = "sport;league;participants;scores"

    for fid in ids:
        hit = bulk_map.get(fid)
        print(f"\n{'='*60}\nFIXTURE ID {fid}\n{'='*60}")
        print(f"  ¿En mapa bulk?: {'SÍ' if hit else 'NO'}")
        if hit:
            hk = list(hit.keys())[:25]
            print(f"  keys payload bulk: {hk}")

        probe_get_raw(fid, key, include=None)
        probe_get_raw(fid, key, include=inc_short)
        probe_get_raw(fid, key, include=BT2_SM_FIXTURE_INCLUDES)

    # 3) fetch_sportmonks_fixture_dict (perfil full = monitor tras último cambio)
    print("\n=== fetch_sportmonks_fixture_dict (profile=full, con degradación 403) ===")
    from apps.api.bt2_dev_sm_refresh import fetch_sportmonks_fixture_dict

    test_id = ids[0]
    got = fetch_sportmonks_fixture_dict(test_id, key, profile="full")
    print(f"fixture {test_id}: resultado dict={'OK' if isinstance(got, dict) else 'None/ fallo'}")
    if isinstance(got, dict):
        print(f"  keys: {list(got.keys())[:20]}")

    print("\nHecho. Revisá también logs del API: [dev-sm-refresh] y [SM bulk].")


if __name__ == "__main__":
    main()
