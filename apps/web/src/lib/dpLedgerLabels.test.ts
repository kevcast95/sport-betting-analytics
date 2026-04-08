import { describe, expect, it } from 'vitest'
import { dpLedgerReasonLabelEs } from '@/lib/dpLedgerLabels'

describe('dpLedgerLabels (D-05-003)', () => {
  it('onboarding_welcome y onboarding_phase_a comparten el mismo copy', () => {
    const a = dpLedgerReasonLabelEs('onboarding_welcome')
    const b = dpLedgerReasonLabelEs('onboarding_phase_a')
    expect(a).toBe(b)
    expect(a).toContain('onboarding')
  })

  it('pick_premium_unlock y pick_settle tienen etiquetas distintas', () => {
    expect(dpLedgerReasonLabelEs('pick_premium_unlock')).toContain('premium')
    expect(dpLedgerReasonLabelEs('pick_settle')).toContain('Liquidación')
  })

  it('session_close_discipline tiene etiqueta de cierre de estación', () => {
    expect(dpLedgerReasonLabelEs('session_close_discipline')).toContain('estación')
  })

  it('reason desconocido devuelve la clave', () => {
    expect(dpLedgerReasonLabelEs('future_reason_xyz')).toBe('future_reason_xyz')
  })
})
