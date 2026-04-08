import { describe, expect, it } from 'vitest'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

describe('useTradeStore (US-FE-006)', () => {
  it('liquida pick desbloqueado: ledger, bankroll, +10 DP (D-05-012)', () => {
    useUserStore.setState({ disciplinePoints: 1000 })
    useBankrollStore.setState({
      confirmedBankrollCop: 100_000,
      selectedStakePct: 2,
      lastCalculatedAt: new Date().toISOString(),
    })
    useVaultStore.setState({ unlockedPickIds: ['v2-p-001'] })

    const dpBefore = useUserStore.getState().disciplinePoints
    const brBefore = useBankrollStore.getState().confirmedBankrollCop

    const res = useTradeStore.getState().finalizeSettlement({
      pickId: 'v2-p-001',
      outcome: 'PROFIT',
      reflection: 'Mantuve el tamaño pese al ruido del live.',
      stakeCop: 2000,
      decimalCuota: 1.9,
    })

    expect(res).toMatchObject({ ok: true, earnedDp: 10 })
    expect(useTradeStore.getState().isSettled('v2-p-001')).toBe(true)
    expect(useTradeStore.getState().ledger).toHaveLength(1)
    expect(useUserStore.getState().disciplinePoints).toBe(dpBefore + 10)
    expect(useBankrollStore.getState().confirmedBankrollCop).toBe(
      brBefore + 2000 * (1.9 - 1),
    )
  })

  it('rechaza reflexión corta y pick no desbloqueado', () => {
    useVaultStore.setState({ unlockedPickIds: [] })
    const r1 = useTradeStore.getState().finalizeSettlement({
      pickId: 'v2-p-001',
      outcome: 'LOSS',
      reflection: 'corto',
      stakeCop: 1000,
      decimalCuota: 2,
    })
    expect(r1).toEqual({ ok: false, reason: 'invalid_reflection' })

    useVaultStore.setState({ unlockedPickIds: ['v2-p-002'] })
    useTradeStore.getState().finalizeSettlement({
      pickId: 'v2-p-002',
      outcome: 'PUSH',
      reflection: 'Texto largo suficiente para validar.',
      stakeCop: 1000,
      decimalCuota: 2,
    })
    const r2 = useTradeStore.getState().finalizeSettlement({
      pickId: 'v2-p-002',
      outcome: 'LOSS',
      reflection: 'Otra reflexión válida aquí.',
      stakeCop: 1000,
      decimalCuota: 2,
    })
    expect(r2).toEqual({ ok: false, reason: 'already_settled' })
  })

  it('rechaza liquidación con estación cerrada', () => {
    useUserStore.setState({ disciplinePoints: 800 })
    useBankrollStore.setState({
      confirmedBankrollCop: 50_000,
      selectedStakePct: 2,
      lastCalculatedAt: new Date().toISOString(),
    })
    useVaultStore.setState({ unlockedPickIds: ['v2-p-003'] })
    useSessionStore.setState({
      stationLockedUntilIso: new Date(Date.now() + 60_000).toISOString(),
      lastCloseSummary: null,
    })
    const r = useTradeStore.getState().finalizeSettlement({
      pickId: 'v2-p-003',
      outcome: 'LOSS',
      reflection: 'Bloqueo de estación activo en prueba.',
      stakeCop: 1000,
      decimalCuota: 2,
    })
    expect(r).toEqual({ ok: false, reason: 'station_locked' })
  })
})
