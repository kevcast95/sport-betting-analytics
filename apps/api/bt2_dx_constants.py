"""
US-DX-001 — Catálogo canónico de razones del ledger y constantes de economía DP.

Ver docs/bettracker2/sprints/sprint-05/US.md § US-DX-001 y DECISIONES D-05-003.
"""

from __future__ import annotations

from typing import Final, Literal

# Coste canónico de desbloqueo premium (D-04-011 / D-05-004). No confundir con “tomar pick”.
DP_PREMIUM_UNLOCK_COST: Final[int] = 50

# Códigos de error HTTP para contrato FE (D-05-005 en DECISIONES).
BT2_ERR_DP_INSUFFICIENT_PREMIUM: Final[str] = "dp_insufficient_for_premium_unlock"

# Razones que pueden aparecer en bt2_dp_ledger.reason (histórico + Sprint 05).
# onboarding_phase_a: usado por el endpoint de onboarding existente (alias de bienvenida).
DpLedgerReason = Literal[
    "pick_settle",
    "pick_premium_unlock",
    "onboarding_welcome",
    "onboarding_phase_a",
    "penalty_station_unclosed",
    "penalty_unsettled_picks",
    "parlay_activation_2l",
    "parlay_activation_3l",
]

REASON_PICK_SETTLE: Final[str] = "pick_settle"
REASON_PICK_PREMIUM_UNLOCK: Final[str] = "pick_premium_unlock"
REASON_PENALTY_STATION_UNCLOSED: Final[str] = "penalty_station_unclosed"
REASON_PENALTY_UNSETTLED_PICKS: Final[str] = "penalty_unsettled_picks"

PENALTY_UNSETTLED_DP: Final[int] = -25
PENALTY_STATION_UNCLOSED_DP: Final[int] = -50
