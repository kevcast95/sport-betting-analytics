import { describe, expect, it, beforeEach } from 'vitest'
import { useBankrollStore } from '@/store/useBankrollStore'
import {
  selectStationLocked,
  useSessionStore,
} from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import { graceExpiresIso } from '@/lib/operatingDay'
import type { Bt2TakenPickRecord } from '@/lib/bt2Types'

beforeEach(() => {
  useSessionStore.getState().reset()
  useBankrollStore.setState({
    confirmedBankrollCop: 500_000,
    selectedStakePct: 2,
    lastCalculatedAt: new Date().toISOString(),
  })
})

describe('useSessionStore (US-FE-007)', () => {
  it('cierra estación, reconcilia bankroll y bloquea 24h', () => {
    // Inicializar día operativo
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)

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
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    const res = useSessionStore.getState().closeStationAndFinalizeDay({
      exchangeCop: 600_000,
      projectedCop: 500_000,
      dailyReflection: 'Cierre con ajuste externo.',
      settlementsTodayCount: 0,
    })
    expect(res).toEqual({ ok: false, reason: 'note_required_for_discrepancy' })
  })
})

describe('useSessionStore (US-FE-012): día operativo y gracia', () => {
  it('inicializa operatingDayKey en el primer checkDayBoundary', () => {
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    expect(useSessionStore.getState().operatingDayKey).toBe('2026-04-05')
  })

  it('detecta cambio de día y registra pendiente STATION_UNCLOSED solo si hubo picks API', () => {
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    const dk = useSessionStore.getState().operatingDayKey!
    const samplePick: Bt2TakenPickRecord = {
      vaultPickId: 'dp-1',
      bt2PickId: 1,
      eventId: 1,
      market: '1X2',
      selection: '1',
      oddsAccepted: 2,
      stakeUnits: 1,
      openedAt: `${dk}T15:00:00.000Z`,
      eventLabel: 'A vs B',
      operatingDayKey: dk,
    }
    useSessionStore.getState().checkDayBoundary('2026-04-06T08:00:00.000Z', false, [samplePick])

    const state = useSessionStore.getState()
    expect(state.operatingDayKey).toBe('2026-04-06')
    expect(state.previousDayPendingItems).toContain('STATION_UNCLOSED')
    expect(state.graceActiveUntilIso).not.toBeNull()
  })

  it('sin picks tomados, cambio de día no marca STATION_UNCLOSED', () => {
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    useSessionStore.getState().checkDayBoundary('2026-04-06T08:00:00.000Z', false, [])

    expect(useSessionStore.getState().previousDayPendingItems).not.toContain('STATION_UNCLOSED')
  })

  it('detecta UNSETTLED_PICK cuando hay picks sin liquidar al cambiar de día', () => {
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    // Día siguiente con picks sin liquidar
    useSessionStore.getState().checkDayBoundary('2026-04-06T08:00:00.000Z', true)

    const state = useSessionStore.getState()
    expect(state.previousDayPendingItems).toContain('UNSETTLED_PICK')
  })

  it('aplica penalización si la gracia expiró y hay estación sin cerrar', () => {
    useUserStore.getState().reset()
    const dpBefore = useUserStore.getState().disciplinePoints

    // Día 5 como referencia: usar un día suficientemente en el pasado fijo
    const dayKey5 = '2026-04-05'

    // Inicializar en el día 5
    useSessionStore.getState().checkDayBoundary(`${dayKey5}T10:00:00.000Z`, false)

    // La gracia del día 5 expira a medianoche local del día 7.
    // Avanzar al día 7 DESPUÉS de medianoche (gracia expirada) — usamos +12h sobre la expiry
    const graceEnd5 = new Date(graceExpiresIso(dayKey5)).getTime()
    const afterGrace = new Date(graceEnd5 + 12 * 60 * 60 * 1000).toISOString()

    const dk5 = useSessionStore.getState().operatingDayKey!
    const pickDay5: Bt2TakenPickRecord = {
      vaultPickId: 'dp-1',
      bt2PickId: 1,
      eventId: 1,
      market: '1X2',
      selection: '1',
      oddsAccepted: 2,
      stakeUnits: 1,
      openedAt: `${dk5}T12:00:00.000Z`,
      eventLabel: 'A vs B',
      operatingDayKey: dk5,
    }
    // checkDayBoundary detectará: cambio de día 5→(día7) + gracia expirada → penalización
    useSessionStore.getState().checkDayBoundary(afterGrace, false, [pickDay5])

    const state = useSessionStore.getState()
    expect(state.penaltiesApplied.length).toBeGreaterThan(0)
    expect(state.penaltiesApplied[0].reason).toBe('grace_expired_station_unclosed')
    // Sprint 05: −50/−25 DP solo en servidor (session/open); el cliente no simula el cargo.
    expect(useUserStore.getState().disciplinePoints).toBe(dpBefore)
  })

  it('no registra pendientes si la estación se cerró correctamente el día anterior', () => {
    // Día 5, cerrar estación correctamente
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    useSessionStore.getState().closeStationAndFinalizeDay({
      exchangeCop: 500_000,
      projectedCop: 500_000,
      dailyReflection: 'Sin novedades, todo en orden.',
      settlementsTodayCount: 1,
    })

    // Día siguiente
    useSessionStore.getState().checkDayBoundary('2026-04-06T08:00:00.000Z', false)

    const state = useSessionStore.getState()
    expect(state.operatingDayKey).toBe('2026-04-06')
    expect(state.previousDayPendingItems).toHaveLength(0)
    expect(state.graceActiveUntilIso).toBeNull()
  })
})

describe('selectStationLocked (US-FE-014): coherencia con día calendario', () => {
  it('bloquea la estación si se cerró en el mismo día operativo', () => {
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    useSessionStore.getState().closeStationAndFinalizeDay({
      exchangeCop: 500_000,
      projectedCop: 500_000,
      dailyReflection: 'Sesión cerrada correctamente.',
      settlementsTodayCount: 1,
    })

    const state = useSessionStore.getState()
    expect(selectStationLocked(state)).toBe(true)
  })

  it('NO bloquea si el día operativo cambió (día siguiente)', () => {
    // Cerrar estación en día 5
    useSessionStore.getState().checkDayBoundary('2026-04-05T10:00:00.000Z', false)
    useSessionStore.getState().closeStationAndFinalizeDay({
      exchangeCop: 500_000,
      projectedCop: 500_000,
      dailyReflection: 'Sesión cerrada en día 5.',
      settlementsTodayCount: 1,
    })

    // Avanzar al día 6
    useSessionStore.getState().checkDayBoundary('2026-04-06T08:00:00.000Z', false)

    const state = useSessionStore.getState()
    // La bóveda del nuevo día no está bloqueada por el cierre del día anterior
    expect(selectStationLocked(state)).toBe(false)
  })

  it('NO bloquea si stationLockedUntilIso ya venció', () => {
    useSessionStore.setState({
      stationLockedUntilIso: new Date(Date.now() - 1000).toISOString(),
      operatingDayKey: '2026-04-05',
      closedForDayKey: '2026-04-05',
    })
    const state = useSessionStore.getState()
    expect(selectStationLocked(state)).toBe(false)
  })
})
