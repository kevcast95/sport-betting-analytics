import type { LedgerRow } from '@/store/useTradeStore'

function localDayPrefix(d = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function ledgerRowsForLocalDay(
  ledger: LedgerRow[],
  d = new Date(),
): LedgerRow[] {
  const prefix = localDayPrefix(d)
  return ledger.filter((r) => r.settledAt.startsWith(prefix))
}

export function todaySessionPnlAndStake(ledger: LedgerRow[]): {
  netPnlCop: number
  totalStakeCop: number
  count: number
} {
  const rows = ledgerRowsForLocalDay(ledger)
  let netPnlCop = 0
  let totalStakeCop = 0
  for (const r of rows) {
    netPnlCop += r.pnlCop
    totalStakeCop += r.stakeCop
  }
  return { netPnlCop, totalStakeCop, count: rows.length }
}

export function todayRoiPercent(ledger: LedgerRow[]): number {
  const { netPnlCop, totalStakeCop } = todaySessionPnlAndStake(ledger)
  if (totalStakeCop <= 0) return 0
  return (netPnlCop / totalStakeCop) * 100
}
