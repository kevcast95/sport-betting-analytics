import { describe, expect, it } from 'vitest'
import {
  equitySeriesFromLedger,
  ledgerAggregateMetrics,
  protocolWinRate,
} from '@/lib/ledgerAnalytics'
import type { LedgerRow } from '@/store/useTradeStore'

const sample: LedgerRow[] = [
  {
    pickId: 'a',
    marketClass: 'ML',
    titulo: 't1',
    outcome: 'PROFIT',
    reflection: 'x'.repeat(12),
    pnlCop: 100,
    stakeCop: 1000,
    decimalCuota: 1.1,
    settledAt: '2026-04-01T10:00:00.000Z',
    earnedDp: 25,
  },
  {
    pickId: 'b',
    marketClass: 'ML',
    titulo: 't2',
    outcome: 'LOSS',
    reflection: 'y'.repeat(12),
    pnlCop: -500,
    stakeCop: 500,
    decimalCuota: 2,
    settledAt: '2026-04-01T12:00:00.000Z',
    earnedDp: 25,
  },
]

describe('ledgerAnalytics', () => {
  it('acumula equity en orden temporal', () => {
    const s = equitySeriesFromLedger(sample)
    expect(s).toHaveLength(2)
    expect(s[1].cumulativePnl).toBe(-400)
  })

  it('agrega métricas', () => {
    const m = ledgerAggregateMetrics(sample)
    expect(m.netPnlCop).toBe(-400)
    expect(m.winRatePct).toBe(50)
    expect(m.disciplineDpFromSettlements).toBe(50)
  })

  it('protocolWinRate', () => {
    expect(protocolWinRate(sample, 'ML')).toBe(50)
  })
})
