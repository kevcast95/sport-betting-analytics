"""
Orquestador del Atraco Masivo BT2 — Sprint 02
Ejecutar desde la raíz del repo:

  python scripts/bt2_atraco/run_atraco.py --pass 1 --dry-run
  python scripts/bt2_atraco/run_atraco.py --pass 1
  python scripts/bt2_atraco/run_atraco.py --start 2022-08-01 --end 2024-05-31

Passes predefinidos (plan Pro sin add-on histórico = acceso desde 2023-08-01):
  --pass 1  Tier S × temporadas 2023-24 y 2024-25 — 5 ligas top [RECOMENDADO]
  --pass 2  Tier S × solo temporada 2023-24 (test rápido ~280 días)
  --pass 3  Tier S × solo temporada 2024-25
  --pass 4  Tier A × temporadas 2023-24 y 2024-25 — ligas adicionales

NOTA: Para incluir temporada 2022-23, activar el add-on histórico (€29 one-time)
y reajustar --start a 2022-08-01.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv
load_dotenv(Path(_repo_root) / ".env")

from scripts.bt2_atraco.sportmonks_worker import run_sportmonks
from scripts.bt2_atraco.theoddsapi_worker import run_theoddsapi

RECON_DIR = Path(_repo_root) / "docs" / "bettracker2" / "recon_results"
RECON_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = RECON_DIR

# ── Passes predefinidos ──────────────────────────────────────────────────────

TIER_S_LEAGUES = [8, 82, 301, 384, 564]   # EPL, Bundesliga, Ligue 1, Serie A, La Liga
TIER_A_LEAGUES = [72, 208, 453, 462, 501, 600, 672]  # Eredivisie, Pro League, Ekstraklasa, Liga Portugal, Premiership, Super Lig, BetPlay

TIER_S_SPORTS = [
    "soccer_epl",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_1",
    "soccer_italy_serie_a",
    "soccer_spain_la_liga",
]
TIER_A_SPORTS = [
    "soccer_netherlands_eredivisie",
    "soccer_turkey_super_league",
    "soccer_portugal_primeira_liga",
    "soccer_colombia_primera_a",
]

PASS_CONFIGS = {
    # Sin add-on histórico el acceso empieza en ~2023-08-12 (inicio temporada 2023/24).
    # Seasons disponibles en plan Pro (sin add-on): 2023/24 y 2024/25.
    # Para acceder a 2022/23 se requiere el add-on histórico (€29 one-time).
    1: {
        "start": "2023-08-01",
        "end": "2025-05-31",
        "league_ids": TIER_S_LEAGUES,
        "sport_keys": TIER_S_SPORTS,
        "description": "Tier S — 5 ligas top × temporadas 2023-24 y 2024-25",
    },
    2: {
        "start": "2023-08-01",
        "end": "2024-05-31",
        "league_ids": TIER_S_LEAGUES,
        "sport_keys": TIER_S_SPORTS,
        "description": "Tier S — 5 ligas top × solo temporada 2023-24 (test rápido)",
    },
    3: {
        "start": "2024-08-01",
        "end": "2025-05-31",
        "league_ids": TIER_S_LEAGUES,
        "sport_keys": TIER_S_SPORTS,
        "description": "Tier S — 5 ligas top × solo temporada 2024-25",
    },
    4: {
        "start": "2023-08-01",
        "end": "2025-05-31",
        "league_ids": TIER_A_LEAGUES,
        "sport_keys": TIER_A_SPORTS,
        "description": "Tier A — ligas adicionales × temporadas 2023-24 y 2024-25",
    },
    # Pass 5: todas las ligas del plan sin filtro — correr DESPUÉS de Pass 1.
    # Los fixtures de Tier S ya guardados no se duplican (ON CONFLICT DO NOTHING).
    # Captura las 120 ligas del plan Pro: LATAM, MLS, J1, K League, AFC, etc.
    5: {
        "start": "2023-08-01",
        "end": "2025-05-31",
        "league_ids": None,  # sin filtro — guardar todo
        "sport_keys": TIER_S_SPORTS + TIER_A_SPORTS,
        "description": "Todas las ligas del plan × temporadas 2023-24 y 2024-25 (120 ligas)",
    },
}

# ── Logging ──────────────────────────────────────────────────────────────────

def setup_logging(log_path: Path) -> None:
    fmt = "%(asctime)s  %(levelname)-7s  %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


# ── Reporte final ────────────────────────────────────────────────────────────

def generate_report(
    sm_stats: dict,
    odds_stats: dict,
    start_date: str,
    end_date: str,
    dry_run: bool,
    duration_s: float,
    pass_num: int,
    description: str,
    report_path: Path,
) -> None:
    duration_min = duration_s / 60
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    mode = "DRY-RUN (sin escrituras)" if dry_run else "PRODUCCIÓN"

    sm_errors = "\n".join(f"  - {e}" for e in sm_stats.get("errors", [])) or "  Ninguno"
    odds_errors = "\n".join(f"  - {e}" for e in odds_stats.get("errors", [])) or "  Ninguno"

    content = f"""# Atraco Masivo — Reporte de ejecución

**Fecha:** {now}
**Modo:** {mode}
**Pass:** {pass_num} — {description}
**Rango:** {start_date} → {end_date}
**Duración:** {duration_min:.1f} minutos

---

## Sportmonks

| Métrica | Valor |
|---------|-------|
| Días procesados | {sm_stats.get("dates_processed", 0):,} |
| Días con fixtures | {sm_stats.get("dates_with_fixtures", 0):,} |
| Fixtures fetched | {sm_stats.get("fixtures_fetched", 0):,} |
| Fixtures stored | {sm_stats.get("fixtures_stored", 0):,} |
| Errores | {len(sm_stats.get("errors", []))} |

**Errores:**
{sm_errors}

---

## The-Odds-API

"""

    if odds_stats.get("skipped"):
        content += f"⚠️ Worker omitido — {odds_stats.get('reason', 'sin key')}\n"
    else:
        content += f"""| Métrica | Valor |
|---------|-------|
| Requests hechos | {odds_stats.get("requests_made", 0):,} |
| Cache hits | {odds_stats.get("cache_hits", 0):,} |
| Snapshots fetched | {odds_stats.get("snapshots_fetched", 0):,} |
| Snapshots stored | {odds_stats.get("snapshots_stored", 0):,} |
| Requests restantes | {odds_stats.get("requests_remaining", "n/d")} |
| Errores | {len(odds_stats.get("errors", []))} |

**Errores:**
{odds_errors}
"""

    content += f"""
---

## Resumen

- **Total fixtures en BD:** {sm_stats.get("fixtures_stored", 0):,}
- **Total snapshots odds en BD:** {odds_stats.get("snapshots_stored", 0) if not odds_stats.get("skipped") else "n/a"}
- **Modo:** {mode}
- **Siguiente paso:** {"Verificar datos y lanzar en producción" if dry_run else "Verificar conteos en PostgreSQL"}

```sql
SELECT COUNT(*), MIN(fixture_date), MAX(fixture_date) FROM raw_sportmonks_fixtures;
SELECT COUNT(*), MIN(commence_time), MAX(commence_time) FROM raw_theoddsapi_snapshots;
```
"""

    report_path.write_text(content, encoding="utf-8")
    logging.getLogger("atraco").info("Reporte guardado: %s", report_path)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    import os
    from sqlalchemy.ext.asyncio import create_async_engine

    # Resolver configuración de pass o fechas manuales
    if args.pass_num is not None:
        cfg = PASS_CONFIGS.get(args.pass_num)
        if not cfg:
            print(f"Pass {args.pass_num} no definido. Disponibles: {list(PASS_CONFIGS.keys())}")
            sys.exit(1)
        start_str = cfg["start"]
        end_str = cfg["end"]
        league_ids = cfg["league_ids"]
        sport_keys = cfg["sport_keys"]
        description = cfg["description"]
    else:
        start_str = args.start
        end_str = args.end
        league_ids = [int(x) for x in args.leagues.split(",")] if args.leagues else TIER_S_LEAGUES
        sport_keys = args.sports.split(",") if args.sports else TIER_S_SPORTS
        description = f"Manual — {start_str} a {end_str}"

    start_date = date.fromisoformat(start_str)
    end_date = date.fromisoformat(end_str)
    pass_num = args.pass_num or 0

    # Logging con archivo
    log_filename = f"atraco_p{pass_num}_{start_str}_{end_str}{'_dry' if args.dry_run else ''}.log"
    log_path = LOG_DIR / log_filename
    setup_logging(log_path)
    logger = logging.getLogger("atraco")

    logger.info("=" * 60)
    logger.info("ATRACO MASIVO BT2 — %s", "DRY-RUN" if args.dry_run else "PRODUCCIÓN")
    logger.info("Pass: %d — %s", pass_num, description)
    logger.info("Rango: %s → %s", start_str, end_str)
    logger.info("Ligas SM: %s", league_ids)
    logger.info("Sports ODDS: %s", sport_keys)
    logger.info("=" * 60)

    # API keys
    sm_key = os.getenv("SPORTMONKS_API_KEY", "")
    odds_key = "" if args.no_odds else os.getenv("THEODDSAPI_KEY", "")

    if not sm_key:
        logger.error("SPORTMONKS_API_KEY vacío — abortando")
        sys.exit(1)

    logger.info("SPORTMONKS_KEY: %s...  THEODDSAPI_KEY: %s",
                sm_key[:8], "presente" if odds_key else "vacío (worker omitido)")

    # Engine async
    db_url = os.getenv("BT2_DATABASE_URL", "")
    if not db_url:
        logger.error("BT2_DATABASE_URL vacío — abortando")
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)

    t0 = time.time()

    # Lanzar workers en paralelo
    sm_task = run_sportmonks(
        start_date, end_date, league_ids, sm_key, engine, dry_run=args.dry_run
    )
    odds_task = run_theoddsapi(
        start_date, end_date, sport_keys, odds_key, engine, dry_run=args.dry_run
    )

    sm_stats, odds_stats = await asyncio.gather(sm_task, odds_task)

    duration_s = time.time() - t0
    await engine.dispose()

    # Reporte
    report_filename = f"atraco_{start_str}_{end_str}{'_dry' if args.dry_run else ''}.md"
    report_path = RECON_DIR / report_filename
    generate_report(
        sm_stats, odds_stats,
        start_str, end_str,
        args.dry_run, duration_s,
        pass_num, description,
        report_path,
    )

    logger.info("=" * 60)
    logger.info("ATRACO COMPLETADO en %.1f min", duration_s / 60)
    logger.info("Fixtures stored: %d", sm_stats.get("fixtures_stored", 0))
    if not odds_stats.get("skipped"):
        logger.info("Snapshots stored: %d", odds_stats.get("snapshots_stored", 0))
    logger.info("Log: %s", log_path)
    logger.info("Reporte: %s", report_path)
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atraco Masivo BT2 — ingesta histórica de fixtures y odds")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--pass", dest="pass_num", type=int, metavar="N",
        help="Pass predefinido (1=Tier S 2022-24, 2=Tier S 2021-22, 3=Tier S 2024-25, 4=Tier A 2022-24)",
    )
    group.add_argument("--start", type=str, metavar="YYYY-MM-DD", help="Fecha inicio (requiere --end)")

    parser.add_argument("--end", type=str, metavar="YYYY-MM-DD", help="Fecha fin")
    parser.add_argument("--leagues", type=str, help="IDs de ligas SM separados por coma (default: Tier S)")
    parser.add_argument("--sports", type=str, help="sport_keys ODDS separados por coma (default: Tier S)")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir en BD")
    parser.add_argument("--no-odds", action="store_true", help="Omite el worker de The-Odds-API completamente")

    args = parser.parse_args()

    if args.pass_num is None and args.start is None:
        parser.error("Indica --pass N o --start/--end")
    if args.start and not args.end:
        parser.error("--start requiere --end")

    asyncio.run(main(args))
