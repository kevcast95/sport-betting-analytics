#!/usr/bin/env python3
"""
send_telegram_message.py

Envía el contenido de un archivo de texto como cuerpo de un mensaje a Telegram.

Uso:
  python3 jobs/send_telegram_message.py --message-file out/telegram_message.txt

Variables de entorno (requeridas o via flags):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Envía mensaje a Telegram (Bot API).")
    p.add_argument("--message-file", "-m", default="out/telegram_message.txt", help="Texto a enviar (UTF-8).")
    p.add_argument("--bot-token-env", default="TELEGRAM_BOT_TOKEN", help="Env var para token.")
    p.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID", help="Env var para chat_id.")
    p.add_argument("--chat-id", type=str, default=None, help="Override chat_id.")
    p.add_argument("--bot-token", type=str, default=None, help="Override bot_token.")
    p.add_argument("--parse-mode", type=str, default="Markdown", help="Markdown/HTML o vacio.")
    p.add_argument("--disable-web-page-preview", action="store_true", help="Desactiva preview.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    bot_token = args.bot_token or os.environ.get(args.bot_token_env)
    chat_id = args.chat_id or os.environ.get(args.chat_id_env)
    if not bot_token:
        print(f"Error: falta bot token (env {args.bot_token_env}).", file=sys.stderr)
        sys.exit(2)
    if not chat_id:
        print(f"Error: falta chat_id (env {args.chat_id_env}).", file=sys.stderr)
        sys.exit(2)

    with open(args.message_file, "r", encoding="utf-8") as f:
        text = f.read()

    params: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if args.parse_mode:
        params["parse_mode"] = args.parse_mode
    if args.disable_web_page_preview:
        params["disable_web_page_preview"] = True

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({k: str(v) for k, v in params.items()}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    try:
        j = json.loads(raw)
    except Exception:
        print(raw)
        sys.exit(1)

    if not j.get("ok"):
        print("Error Telegram:", raw, file=sys.stderr)
        sys.exit(1)

    print(f"OK Telegram message_id={j.get('result', {}).get('message_id')}")


if __name__ == "__main__":
    main()

