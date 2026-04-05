export type SettlementOutcome = 'PROFIT' | 'LOSS' | 'PUSH'

/**
 * US-FE-006: PnL en COP para una unidad de stake y cuota decimal europea.
 * Profit: stake × (cuota − 1) · Loss: −stake · Push: 0 (capital devuelto).
 */
export function computeSettlementPnlCop(
  stakeCop: number,
  decimalCuota: number,
  outcome: SettlementOutcome,
): number {
  if (!Number.isFinite(stakeCop) || stakeCop < 0) return Number.NaN
  if (!Number.isFinite(decimalCuota) || decimalCuota < 1) return Number.NaN
  if (outcome === 'PUSH') return 0
  if (outcome === 'LOSS') return -stakeCop
  return stakeCop * (decimalCuota - 1)
}

export function potentialProfitCop(
  stakeCop: number,
  decimalCuota: number,
): number {
  return computeSettlementPnlCop(stakeCop, decimalCuota, 'PROFIT')
}
