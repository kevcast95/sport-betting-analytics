import { describe, expect, it } from 'vitest'
import {
  computeSettlementPnlCop,
  potentialProfitCop,
} from '@/lib/settlementPnL'

describe('settlementPnL', () => {
  it('profit: stake × (cuota − 1)', () => {
    expect(computeSettlementPnlCop(10000, 1.9, 'PROFIT')).toBeCloseTo(9000, 5)
  })

  it('loss: −stake', () => {
    expect(computeSettlementPnlCop(10000, 1.9, 'LOSS')).toBe(-10000)
  })

  it('push: 0', () => {
    expect(computeSettlementPnlCop(10000, 1.9, 'PUSH')).toBe(0)
  })

  it('cuota decimal 2.05', () => {
    expect(potentialProfitCop(5000, 2.05)).toBeCloseTo(5250, 5)
  })

  it('rechaza entradas no finitas', () => {
    expect(Number.isNaN(computeSettlementPnlCop(NaN, 2, 'PROFIT'))).toBe(true)
    expect(Number.isNaN(computeSettlementPnlCop(100, 0.5, 'PROFIT'))).toBe(
      true,
    )
  })
})
