#!/usr/bin/env python3
"""
render_telegram_payload.py

Lee un JSON con picks ya validados (p. ej. salida estructurada del LLM o generada a mano)
y escribe el mensaje compacto para Telegram (UTF-8, emojis incluidos).

No forma parte del pipeline ingest → select → persist; es un paso OPCIONAL después
de tener el JSON de picks (p. ej. OC escribe telegram_payload.json y ejecuta este job).

Entrada (stdin o --input):
{
  "header": { "title": "Copa Foxkids", "date": "2026-03-21", "daily_run_id": 1, "pick_count": 6 },
  "events": [
    {
      "label": "Como vs Pisa",
      "league": "Serie A",
      "local_time_short": "06:30",
      "event_id": 13981718,
      "picks": [
        {
          "market": "1X2",
          "selection": "1 (Como)",
          "odds": 2.62,
          "edge_pct": 4.15,
          "confianza": "Media",
          "razon": "Mejor volumen ofensivo en temporada y factor local."
        }
      ]
    }
  ],
  "db_1x2_line": "13981718 1 @2.62 | 14065193 1 @1.25"
}

Salida: texto por stdout y opcionalmente -o archivo (para que OC/Telegram lean el mismo contenido).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List


def _load_payload(path: str | None) -> Any:
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def _render(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    divider = "----------------------------------------"
    h = data.get("header") or {}
    title = h.get("title") or "Copa Foxkids"
    date = h.get("date") or ""
    dr = h.get("daily_run_id")
    pc = h.get("pick_count")
    head = f"🎯 {title}"
    if date:
        head += f" | 📅 {date}"
    if dr is not None:
        head += f" | run #{dr}"
    if pc is not None:
        head += f" | {pc} picks"
    lines.append(head)
    lines.append("")

    events = data.get("events") or []
    discarded = 0
    picked_events = 0

    for ev in events:
        label = ev.get("label") or "?"
        league = ev.get("league") or ""
        lt = ev.get("local_time_short") or ""
        eid = ev.get("event_id")
        picks = ev.get("picks") or []
        if not picks:
            discarded += 1
            continue
        picked_events += 1

        sub = f"{divider}\n🔍 **{label}**"
        if league:
            sub += f" | 🏆 {league}"
        if lt:
            sub += f" | ⏰ {lt}"
        if eid is not None:
            sub += f" | id {eid}"
        lines.append(sub)
        lines.append("")

        for i, p in enumerate(picks, start=1):
            n = len(picks)
            prefix = "**PICK**" if n == 1 else f"**PICK {i}**"
            lines.append(prefix)
            lines.append(f"🎯 **MARKET**: {p.get('market', '')}")
            lines.append(f"✅ **SELECTION**: {p.get('selection', '')}")
            if p.get("odds") is not None:
                tag = " (SofaScore)" if p.get("odds_source") == "scraped_sofascore" else ""
                lines.append(f"💰 **ODDS**: {p['odds']}{tag}")
            if p.get("edge_pct") is not None:
                lines.append(f"📈 **EDGE**: {p['edge_pct']}%")
            lines.append(f"📊 **CONFIANZA**: {p.get('confianza', '')}")
            lines.append(f"💡 **RAZÓN**: {p.get('razon', '')}")
            lines.append("")

    if picked_events == 0:
        lines.append(f"{divider}")
        lines.append("ℹ️ **SIN PICKS CON VALOR** en esta ventana.")
        lines.append("")

    if discarded > 0:
        lines.append(f"🧪 **DESCARTADOS**: {discarded} evento(s) sin valor suficiente.")
        lines.append("")

    db_line = data.get("db_1x2_line")
    if db_line:
        lines.append(divider)
        lines.append(f"💾 **DB 1X2**: {db_line}")

    alloc = data.get("allocation") or {}
    singles = alloc.get("singles") or []
    combos = alloc.get("combos") or []
    if singles:
        lines.append("")
        lines.append(divider)
        lines.append(
            f"💼 **PLAN BANKROLL**: ${int(alloc.get('bankroll_cop', 0)):,} COP | exposición {alloc.get('max_exposure_pct', 0)}%"
        )
        for i, s in enumerate(singles[:5], start=1):
            lines.append(
                f"{i}. **${int(s.get('stake_cop', 0)):,}** ({s.get('stake_pct_bankroll', 0)}%) "
                f"→ {s.get('label', '?')} | {s.get('market', '')}={s.get('selection', '')} "
                f"| odds {s.get('odds', '')} | edge {s.get('edge_pct', '')}%"
            )
        if len(singles) > 5:
            lines.append(f"… +{len(singles) - 5} pick(s) adicionales en ranking interno.")

    if combos:
        lines.append("")
        lines.append("🧩 **COMBINADAS SUGERIDAS**")
        for c in combos[:2]:
            lines.append(
                f"- **{c.get('name','Combo')}** | cuota {c.get('odds_total','')} | "
                f"stake ${int(c.get('stake_cop', 0)):,} ({c.get('stake_pct_bankroll', 0)}%)"
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Renderiza mensaje Telegram desde JSON estructurado.")
    p.add_argument("--input", "-i", type=str, default=None, help="JSON entrada (default: stdin)")
    p.add_argument("--output", "-o", type=str, default=None, help="Archivo salida (default: stdout)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    data = _load_payload(args.input)
    if not isinstance(data, dict):
        print("Error: JSON debe ser un objeto.", file=sys.stderr)
        sys.exit(1)
    text = _render(data)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"OK written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
