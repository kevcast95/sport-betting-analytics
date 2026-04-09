/**
 * D-05-003 — Catálogo reason → copy UI (US-DX-001).
 * onboarding_welcome y onboarding_phase_a comparten la misma etiqueta.
 */
import type { Bt2DpLedgerReason } from '@/lib/bt2Types'

const ONBOARDING_PHASE_A_LABEL = 'Bienvenida — onboarding fase A'

const REASON_LABEL_ES: Record<Bt2DpLedgerReason, string> = {
  pick_settle: 'Liquidación de pick',
  pick_premium_unlock: 'Desbloqueo pick premium',
  session_close_discipline: 'Recompensa por cerrar la estación',
  onboarding_welcome: ONBOARDING_PHASE_A_LABEL,
  onboarding_phase_a: ONBOARDING_PHASE_A_LABEL,
  penalty_station_unclosed: 'Penalización: estación sin cerrar',
  penalty_unsettled_picks: 'Penalización: picks sin liquidar (tras gracia)',
  parlay_activation_2l: 'Activación parlay 2 eventos (reservado)',
  parlay_activation_3l: 'Activación parlay 3 eventos (reservado)',
}

export function dpLedgerReasonLabelEs(reason: string): string {
  if (reason in REASON_LABEL_ES) {
    return REASON_LABEL_ES[reason as Bt2DpLedgerReason]
  }
  return reason
}
