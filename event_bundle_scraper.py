#!/usr/bin/env python3
"""
Wrapper de compatibilidad.

La lógica real se encuentra en:
  core/event_bundle_scraper.py
"""

import asyncio

from core.event_bundle_scraper import _cli_main, parse_args


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(_cli_main(args))

