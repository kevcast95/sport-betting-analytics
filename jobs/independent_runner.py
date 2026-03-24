#!/usr/bin/env python3
"""
independent_runner.py

Orquestador local (sin OpenClaw/Gateway) para ejecutar:
  - Midnight: ingest + select + aviso Telegram de conteo.
  - Window: event_splitter + split batches + DeepSeek + merge + render + Telegram.
  - full_day: mismos pasos que window pero --slot full_day (todos los candidatos del día) y persiste picks en DB.

Pensado para cron diario en America/Bogota.

Artefactos multi-deporte: con --sport distinto de football se añade sufijo al nombre
(p. ej. candidates_{DATE}_tennis_select.json, payload_{DATE}_exec_08h_tennis_part01.json)
para no pisar el pipeline de fútbol el mismo día.
"""

from __future__ import annotations

import argparse
import glob
import os
import sqlite3
import subprocess
import sys
import json
from datetime import datetime
from zoneinfo import ZoneInfo


def _run(cmd: list[str], *, dry_run: bool = False) -> None:
    print("$", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def _today_str(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _db_path(db_arg: str | None) -> str:
    if db_arg:
        return os.path.abspath(db_arg)
    env_db = os.environ.get("DB_PATH")
    if env_db:
        return os.path.abspath(env_db)
    return os.path.abspath(os.path.join(_repo_root(), "db", "sport-tracker.sqlite3"))


def _get_daily_run_id(db: str, run_date: str, sport: str) -> int:
    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "SELECT daily_run_id FROM daily_runs WHERE run_date = ? AND sport = ? ORDER BY daily_run_id DESC LIMIT 1",
            (run_date, sport),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"No existe daily_run para date={run_date} sport={sport}")
        return int(row[0])
    finally:
        conn.close()


def _run_tag(sport: str) -> str:
    s = (sport or "football").strip().lower()
    return "" if s == "football" else f"_{s}"


def _count_run_events(db: str, daily_run_id: int) -> int:
    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "SELECT created_at_utc, sport FROM daily_runs WHERE daily_run_id = ?",
            (daily_run_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"daily_run_id no existe: {daily_run_id}")
        captured = str(row[0])
        sport = str(row[1] or "football").strip().lower()
        cur2 = conn.execute(
            "SELECT COUNT(*) FROM event_features WHERE captured_at_utc = ? AND sport = ?",
            (captured, sport),
        )
        return int(cur2.fetchone()[0])
    finally:
        conn.close()


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Runner independiente DeepSeek+Telegram (sin OpenClaw).")
    p.add_argument("--mode", choices=["midnight", "window", "full_day"], required=True)
    p.add_argument(
        "--slot",
        choices=["morning", "afternoon"],
        default=None,
        help="Requerido en mode=window",
    )
    p.add_argument(
        "--persist-picks",
        action="store_true",
        help="Tras el merge, persistir picks desde telegram_payload.json (modo window; full_day lo hace por defecto).",
    )
    p.add_argument(
        "--skip-persist",
        action="store_true",
        help="En full_day: no escribir picks en SQLite.",
    )
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: hoy en --timezone)")
    p.add_argument("--timezone", default=os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota"))
    p.add_argument("--sport", default="football")
    p.add_argument("--db", default=None)
    p.add_argument("--limit-ingest", type=int, default=None)
    p.add_argument("--limit-select", type=int, default=20)
    p.add_argument("--chunk-size", type=int, default=4)
    # Separación explícita de roles:
    # - chat model: interacciones ligeras/operativas
    # - analysis model: picks (por defecto reasoner)
    p.add_argument("--ds-chat-model", default=os.environ.get("DS_CHAT_MODEL", "deepseek-chat"))
    p.add_argument(
        "--ds-analysis-model",
        default=os.environ.get("DS_ANALYSIS_MODEL", os.environ.get("DS_MODEL", "deepseek-reasoner")),
    )
    p.add_argument("--ds-max-tokens", type=int, default=int(os.environ.get("DS_MAX_TOKENS", "1200")))
    p.add_argument(
        "--ds-timeout-sec",
        type=int,
        default=int(os.environ.get("DS_TIMEOUT_SEC", "420")),
        help="Por defecto 420s: deepseek-reasoner suele superar 180s por lote.",
    )
    p.add_argument("--ds-max-retries", type=int, default=int(os.environ.get("DS_MAX_RETRIES", "1")))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-telegram", action="store_true")
    p.add_argument("--bankroll-cop", type=float, default=float(os.environ.get("BANKROLL_COP", "100000")))
    p.add_argument(
        "--max-exposure-pct",
        type=float,
        default=float(os.environ.get("MAX_EXPOSURE_PCT", "30")),
    )
    return p.parse_args()


def _midnight(args: argparse.Namespace, *, repo: str, db: str, date_str: str) -> None:
    ingest_cmd = [
        sys.executable,
        os.path.join(repo, "jobs", "ingest_daily_events.py"),
        "--sport",
        args.sport,
        "--date",
        date_str,
        "--db",
        db,
    ]
    if args.limit_ingest is not None:
        ingest_cmd += ["--limit", str(args.limit_ingest)]
    _run(ingest_cmd, dry_run=args.dry_run)

    if args.dry_run:
        print("DRY RUN: omitiendo query daily_run_id y conteo.")
        return

    daily_run_id = _get_daily_run_id(db, date_str, args.sport)
    tag = _run_tag(args.sport)
    select_out = os.path.join(repo, "out", f"candidates_{date_str}{tag}_select.json")
    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "select_candidates.py"),
            "--db",
            db,
            "--daily-run-id",
            str(daily_run_id),
            "--limit",
            str(args.limit_select),
            "-o",
            select_out,
        ],
        dry_run=False,
    )

    total_events = _count_run_events(db, daily_run_id)
    msg = (
        "✅ Ingest ejecutado correctamente\n"
        f"🔄 DR: {daily_run_id}\n"
        f"📅 Fecha: {date_str}\n"
        f"📊 Total partidos: {total_events}\n"
    )
    message_file = os.path.join(repo, "out", "telegram_message.txt")
    _write_text(message_file, msg)
    print(f"OK message written: {message_file}")

    if not args.skip_telegram:
        _run(
            [sys.executable, os.path.join(repo, "jobs", "send_telegram_message.py"), "--message-file", message_file],
            dry_run=False,
        )


def _run_windowed_analysis(
    args: argparse.Namespace,
    *,
    repo: str,
    db: str,
    date_str: str,
    splitter_slot: str,
    exec_id: str,
    block_label: str,
    persist_picks: bool,
) -> None:
    tag = _run_tag(args.sport)
    exec_composite = f"{exec_id}{tag}"
    title_base = "Tenis" if tag == "_tennis" else "Copa Foxkids"
    select_in = os.path.join(repo, "out", f"candidates_{date_str}{tag}_select.json")
    split_out = os.path.join(repo, "out", f"candidates_{date_str}{tag}_{exec_id}.json")
    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "event_splitter.py"),
            "-i",
            select_in,
            "-o",
            split_out,
            "--date",
            date_str,
            "--slot",
            splitter_slot,
            "--timezone",
            args.timezone,
        ],
        dry_run=args.dry_run,
    )

    batch_prefix = os.path.join(repo, "out", "batches", f"candidates_{date_str}{tag}_{exec_id}")
    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "split_ds_batches.py"),
            "-i",
            split_out,
            "-o",
            batch_prefix,
            "--chunk-size",
            str(args.chunk_size),
            "--slim",
        ],
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("DRY RUN: omitiendo llamadas a DeepSeek/merge/render/telegram/persist.")
        return

    batch_glob = f"{batch_prefix}_batch*.json"
    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "deepseek_batches_to_telegram_payload_parts.py"),
            "--input-glob",
            batch_glob,
            "--date",
            date_str,
            "--exec-id",
            exec_composite,
            "--title",
            f"{title_base} — {block_label}",
            "--model",
            args.ds_analysis_model,
            "--max-tokens",
            str(args.ds_max_tokens),
            "--timeout-sec",
            str(args.ds_timeout_sec),
            "--max-retries",
            str(args.ds_max_retries),
        ],
        dry_run=False,
    )

    parts = sorted(glob.glob(os.path.join(repo, "out", f"payload_{date_str}_{exec_composite}_part*.json")))
    if not parts:
        raise RuntimeError("No se generaron payload parts desde DeepSeek.")

    telegram_payload = os.path.join(repo, "out", "telegram_payload.json")
    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "merge_telegram_payload_parts.py"),
            "-i",
            *parts,
            "-o",
            telegram_payload,
        ],
        dry_run=False,
    )

    telegram_text = os.path.join(repo, "out", "telegram_message.txt")
    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "allocate_bankroll.py"),
            "-i",
            telegram_payload,
            "-o",
            telegram_payload,
            "--bankroll-cop",
            str(args.bankroll_cop),
            "--max-exposure-pct",
            str(args.max_exposure_pct),
        ],
        dry_run=False,
    )

    _run(
        [
            sys.executable,
            os.path.join(repo, "jobs", "render_telegram_payload.py"),
            "-i",
            telegram_payload,
            "-o",
            telegram_text,
        ],
        dry_run=False,
    )

    if persist_picks:
        _run(
            [
                sys.executable,
                os.path.join(repo, "jobs", "persist_picks.py"),
                "--db",
                db,
                "--telegram-payload",
                telegram_payload,
            ],
            dry_run=False,
        )

    # Si el análisis no produjo picks, enviamos mensaje corto de estado del bloque
    payload = _read_json(telegram_payload)
    header = payload.get("header") or {}
    pick_count = int(header.get("pick_count") or 0)
    if pick_count == 0:
        daily_run_id = header.get("daily_run_id", "?")
        _write_text(
            telegram_text,
            (
                f"ℹ️ {block_label} ejecutado\n"
                f"📅 Fecha: {date_str}\n"
                f"🔄 DR: {daily_run_id}\n"
                "📭 No se encontraron picks válidos en esta ventana.\n"
            ),
        )

    if not args.skip_telegram:
        _run(
            [sys.executable, os.path.join(repo, "jobs", "send_telegram_message.py"), "--message-file", telegram_text],
            dry_run=False,
        )


def _window(args: argparse.Namespace, *, repo: str, db: str, date_str: str) -> None:
    if not args.slot:
        raise RuntimeError("mode=window requiere --slot morning|afternoon")
    exec_id = "exec_08h" if args.slot == "morning" else "exec_16h"
    block_label = "Bloque 1 (08:00)" if args.slot == "morning" else "Bloque 2 (16:00)"
    _run_windowed_analysis(
        args,
        repo=repo,
        db=db,
        date_str=date_str,
        splitter_slot=args.slot,
        exec_id=exec_id,
        block_label=block_label,
        persist_picks=bool(args.persist_picks),
    )


def _full_day(args: argparse.Namespace, *, repo: str, db: str, date_str: str) -> None:
    persist = not bool(args.skip_persist)
    _run_windowed_analysis(
        args,
        repo=repo,
        db=db,
        date_str=date_str,
        splitter_slot="full_day",
        exec_id="exec_full_day",
        block_label="Día completo (análisis)",
        persist_picks=persist,
    )


def main() -> None:
    args = parse_args()
    repo = _repo_root()
    db = _db_path(args.db)
    date_str = args.date or _today_str(args.timezone)

    if args.mode == "midnight":
        _midnight(args, repo=repo, db=db, date_str=date_str)
    elif args.mode == "window":
        _window(args, repo=repo, db=db, date_str=date_str)
    else:
        _full_day(args, repo=repo, db=db, date_str=date_str)


if __name__ == "__main__":
    main()

