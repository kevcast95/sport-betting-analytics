import { describe, expect, it } from 'vitest'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'

describe('useSessionStore (US-FE-007)', () => {
  it('cierra estación, reconcilia bankroll y bloquea 24h', () => {
    useBankrollStore.setState({
      confirmedBankrollCop: 500_000,
      selectedStakePct: 2,
      lastCalculatedAt: new Date().toISOString(),
    })
    const res = useSessionStore.getState().closeStationAndFinalizeDay({
      exchangeCop: 500_000,
      projectedCop: 500_000,
      dailyReflection: 'Sesión ordenada, sin desvíos de plan.',
      settlementsTodayCount: 2,
    })
    expect(res.ok).toBe(true)
    if (!res.ok) return
    expect(res.summary.status).toBe('PERFECT_MATCH')
    expect(useSessionStore.getState().isStationLocked()).toBe(true)
    expect(useBankrollStore.getState().confirmedBankrollCop).toBe(500_000)
  })

  it('exige nota si discrepancia > 1%', () => {
    const res = useSessionStore.getState().closeStationAndFinalizeDay({
      exchangeCop: 600_000,
      projectedCop: 500_000,
      dailyReflection: 'Cierre con ajuste externo.',
      settlementsTodayCount: 0,
    })
    expect(res).toEqual({ ok: false, reason: 'note_required_for_discrepancy' })
  })
})
