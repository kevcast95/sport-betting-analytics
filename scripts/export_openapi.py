#!/usr/bin/env python3
"""Escribe openapi.json en stdout. Uso: PYTHONPATH=. python3 scripts/export_openapi.py > apps/web/openapi.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app  # noqa: E402

json.dump(app.openapi(), sys.stdout, indent=2)
sys.stdout.write("\n")
