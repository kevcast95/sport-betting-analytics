#!/usr/bin/env python3
"""
Wrapper de compatibilidad.

La lógica real se encuentra en:
  core/validate_1x2.py
"""

import asyncio

from core.validate_1x2 import _cli_main, parse_args


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(_cli_main(args))

