#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List


CONF_MAP = {"Baja": 0.25, "Media": 0.5, "Media-Alta": 0.75, "Alta": 1.0}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Asigna stake por pick y sugiere combinadas.")
    p.add_argument("-i", "--input", required=True, help="telegram_payload.json")
    p.add_argument("-o", "--output", required=True, help="payload enriquecido")
    p.add_argument("--bankroll-cop", type=float, default=100000.0)
    p.add_argument("--max-exposure-pct", type=float, default=30.0, help="Exposición total en singles")
    return p.parse_args()


def _pick_score(p: Dict[str, Any]) -> float:
    edge = float(p.get("edge_pct") or 0.0)
    conf = CONF_MAP.get(str(p.get("confianza") or "").strip(), 0.4)
    odds = float(p.get("odds") or 1.0)
    # Preferimos edge y confianza; bonus leve por odds no extremas.
    odds_bonus = 1.0 - min(abs(odds - 2.0), 1.5) / 3.0
    return (0.65 * max(edge, 0.0)) + (0.25 * conf * 10.0) + (0.10 * odds_bonus * 10.0)


def _normalize_weights(scores: List[float]) -> List[float]:
    total = sum(max(s, 0.0) for s in scores)
    if total <= 0:
        return [1.0 / len(scores)] * len(scores) if scores else []
    return [max(s, 0.0) / total for s in scores]


def _build_combos(singles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Combos simples y conservadores: mejores 2 y luego 1+3 (si existen)
    combos: List[Dict[str, Any]] = []
    if len(singles) < 2:
        return combos

    def combo_from_indices(name: str, idx_a: int, idx_b: int, stake_pct: float) -> Dict[str, Any]:
        a = singles[idx_a]
        b = singles[idx_b]
        odds_total = round(float(a["odds"]) * float(b["odds"]), 3)
        # proxy de confianza conjunta
        p_joint = max(0.05, min(0.95, float(a["p_real_pct"]) * float(b["p_real_pct"])))
        ev = round((p_joint * (odds_total - 1.0)) - (1 - p_joint), 4)
        return {
            "name": name,
            "legs": [a["short_label"], b["short_label"]],
            "odds_total": odds_total,
            "p_estimada": round(p_joint * 100, 2),
            "ev_proxy": ev,
            "stake_pct_bankroll": stake_pct,
        }

    combos.append(combo_from_indices("Combinada A (Top2)", 0, 1, 3.0))
    if len(singles) >= 3:
        combos.append(combo_from_indices("Combinada B (Top1+Top3)", 0, 2, 2.0))
    return combos


def main() -> None:
    args = parse_args()
    with open(args.input, "r", encoding="utf-8") as f:
        payload = json.load(f)

    events = payload.get("events") or []
    flat: List[Dict[str, Any]] = []
    discarded = 0
    for ev in events:
        label = ev.get("label") or "?"
        eid = ev.get("event_id")
        picks = ev.get("picks") or []
        if not picks:
            discarded += 1
            continue
        for p in picks:
            odds = p.get("odds")
            if not isinstance(odds, (int, float)) or odds <= 1.0:
                continue
            edge = float(p.get("edge_pct") or 0.0)
            p_imp = min(0.99, max(0.01, 1.0 / float(odds)))
            p_real = min(0.99, max(0.01, p_imp + (edge / 100.0)))
            flat.append(
                {
                    "event_id": eid,
                    "label": label,
                    "market": p.get("market", ""),
                    "selection": p.get("selection", ""),
                    "odds": float(odds),
                    "edge_pct": edge,
                    "confianza": p.get("confianza", ""),
                    "razon": p.get("razon", ""),
                    "p_real_pct": p_real,
                }
            )

    flat.sort(key=_pick_score, reverse=True)
    scores = [_pick_score(p) for p in flat]
    weights = _normalize_weights(scores)

    exposure_cop = args.bankroll_cop * (args.max_exposure_pct / 100.0)
    singles: List[Dict[str, Any]] = []
    for p, w in zip(flat, weights):
        stake = round(exposure_cop * w, 0)
        singles.append(
            {
                **p,
                "short_label": f"{p['label']} | {p['market']}={p['selection']}",
                "score": round(_pick_score(p), 3),
                "stake_cop": int(stake),
                "stake_pct_bankroll": round((stake / args.bankroll_cop) * 100.0, 2),
            }
        )

    combos = _build_combos(singles)
    for c in combos:
        c["stake_cop"] = int(round(args.bankroll_cop * (c["stake_pct_bankroll"] / 100.0), 0))

    payload["allocation"] = {
        "bankroll_cop": int(args.bankroll_cop),
        "max_exposure_pct": args.max_exposure_pct,
        "discarded_events": discarded,
        "singles_count": len(singles),
        "singles": singles,
        "combos": combos,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"OK bankroll allocation -> {args.output}")


if __name__ == "__main__":
    main()

