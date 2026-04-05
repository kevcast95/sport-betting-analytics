import type { LedgerRow } from '@/store/useTradeStore'

export type EquityPoint = { t: string; cumulativePnl: number }

/** Serie acumulada de PnL ordenada por fecha de liquidación. */
export function equitySeriesFromLedger(ledger: LedgerRow[]): EquityPoint[] {
  const sorted = [...ledger].sort(
    (a, b) => new Date(a.settledAt).getTime() - new Date(b.settledAt).getTime(),
  )
  let acc = 0
  return sorted.map((r) => {
    acc += r.pnlCop
    return { t: r.settledAt, cumulativePnl: acc }
  })
}

export function ledgerAggregateMetrics(ledger: LedgerRow[]): {
  roiPct: number
  winRatePct: number
  maxDrawdownCop: number
  disciplineDpFromSettlements: number
  totalStakeCop: number
  netPnlCop: number
} {
  if (ledger.length === 0) {
    return {
      roiPct: 0,
      winRatePct: 0,
      maxDrawdownCop: 0,
      disciplineDpFromSettlements: 0,
      totalStakeCop: 0,
      netPnlCop: 0,
    }
  }
  let totalStakeCop = 0
  let netPnlCop = 0
  let wins = 0
  let disciplineDpFromSettlements = 0
  for (const r of ledger) {
    totalStakeCop += r.stakeCop
    netPnlCop += r.pnlCop
    if (r.outcome === 'PROFIT') wins += 1
    disciplineDpFromSettlements += r.earnedDp ?? 25
  }
  const roiPct = totalStakeCop > 0 ? (netPnlCop / totalStakeCop) * 100 : 0
  const winRatePct = (wins / ledger.length) * 100

  const series = equitySeriesFromLedger(ledger)
  let peak = 0
  let maxDd = 0
  for (const p of series) {
    if (p.cumulativePnl > peak) peak = p.cumulativePnl
    const dd = p.cumulativePnl - peak
    if (dd < maxDd) maxDd = dd
  }

  return {
    roiPct,
    winRatePct,
    maxDrawdownCop: maxDd,
    disciplineDpFromSettlements,
    totalStakeCop,
    netPnlCop,
  }
}

export function protocolWinRate(
  ledger: LedgerRow[],
  marketClass: string,
): number {
  const rows = ledger.filter((r) => (r.marketClass ?? '') === marketClass)
  if (rows.length === 0) return 0
  const w = rows.filter((r) => r.outcome === 'PROFIT').length
  return (w / rows.length) * 100
}
