"""
US-DX-001 — Catálogo canónico de razones del ledger y constantes de economía DP.

Ver docs/bettracker2/sprints/sprint-05/US.md § US-DX-001 y DECISIONES D-05-003.
"""

from __future__ import annotations

from typing import Final, Literal

# Coste canónico de desbloqueo premium (D-04-011 / D-05-004). No confundir con “tomar pick”.
DP_PREMIUM_UNLOCK_COST: Final[int] = 50

# Topes diarios de liberación en bóveda (liberar ≠ tomar): 3 libres + 2 premium DP, máx. 5 total.
VAULT_DAILY_UNLOCK_CAP_STANDARD: Final[int] = 3
VAULT_DAILY_UNLOCK_CAP_PREMIUM: Final[int] = 2
VAULT_DAILY_UNLOCK_CAP_TOTAL: Final[int] = 5

# Códigos de error HTTP para contrato FE (D-05-005 en DECISIONES).
BT2_ERR_DP_INSUFFICIENT_PREMIUM: Final[str] = "dp_insufficient_for_premium_unlock"
# D-05.2-001 (estricto kickoff) — POST /bt2/picks cuando ya pasó el inicio.
BT2_ERR_PICK_KICKOFF_ELAPSED: Final[str] = "pick_event_kickoff_elapsed"
# Bankroll: stake descontado al tomar pick; saldo insuficiente.
BT2_ERR_INSUFFICIENT_BANKROLL_STAKE: Final[str] = "insufficient_bankroll_for_stake"

# Razones que pueden aparecer en bt2_dp_ledger.reason (histórico + Sprint 05).
# onboarding_phase_a: usado por el endpoint de onboarding existente (alias de bienvenida).
DpLedgerReason = Literal[
    "pick_settle",
    "pick_settle_reopen",
    "pick_premium_unlock",
    "session_close_discipline",
    "onboarding_welcome",
    "onboarding_phase_a",
    "penalty_station_unclosed",
    "penalty_unsettled_picks",
    "penalty_unsettled_not_applicable",
    "parlay_activation_2l",
    "parlay_activation_3l",
]

REASON_PICK_SETTLE: Final[str] = "pick_settle"
REASON_PICK_SETTLE_REOPEN: Final[str] = "pick_settle_reopen"
REASON_PICK_PREMIUM_UNLOCK: Final[str] = "pick_premium_unlock"
REASON_SESSION_CLOSE_DISCIPLINE: Final[str] = "session_close_discipline"
REASON_PENALTY_STATION_UNCLOSED: Final[str] = "penalty_station_unclosed"
REASON_PENALTY_UNSETTLED_PICKS: Final[str] = "penalty_unsettled_picks"
# Marca idempotente (delta 0): gracia vencida pero sin picks abiertos en el intervalo de esa sesión.
REASON_PENALTY_UNSETTLED_NOT_APPLICABLE: Final[str] = "penalty_unsettled_not_applicable"

# D-05-018 / US-BE-021: recompensa DP al cerrar sesión con protocolo (POST /session/close).
SESSION_CLOSE_DISCIPLINE_REWARD_DP: Final[int] = 20

# US-BE-020 (D-04-011): misma acreditación al liquidar (won / lost / void).
PICK_SETTLE_DP_REWARD: Final[int] = 10

PENALTY_UNSETTLED_DP: Final[int] = -25
PENALTY_STATION_UNCLOSED_DP: Final[int] = -50

# ── Sprint 06 — mercados canónicos (US-DX-002 / US-BE-027) ─────────────────────
MARKET_CANONICAL_FT_1X2: Final[str] = "FT_1X2"
MARKET_CANONICAL_OU_GOALS_2_5: Final[str] = "OU_GOALS_2_5"
MARKET_CANONICAL_UNKNOWN: Final[str] = "UNKNOWN"

# Resultado medición modelo vs marcador (D-06-015)
MODEL_PREDICTION_HIT: Final[str] = "hit"
MODEL_PREDICTION_MISS: Final[str] = "miss"
MODEL_PREDICTION_VOID: Final[str] = "void"
MODEL_PREDICTION_NA: Final[str] = "n_a"
