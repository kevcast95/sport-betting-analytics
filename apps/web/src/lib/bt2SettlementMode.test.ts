/**
 * US-FE-013: tests unitarios para el modo de verificación de liquidación.
 */
import { describe, expect, it } from 'vitest'
import {
  SETTLEMENT_MODE_LABEL_ES,
  SETTLEMENT_VERIFICATION_MODE,
} from '@/lib/bt2SettlementMode'

describe('bt2SettlementMode (US-FE-013)', () => {
  it('el modo activo es "trust"', () => {
    expect(SETTLEMENT_VERIFICATION_MODE).toBe('trust')
  })

  it('la etiqueta en español del modo trust existe y no está vacía', () => {
    const label = SETTLEMENT_MODE_LABEL_ES[SETTLEMENT_VERIFICATION_MODE]
    expect(typeof label).toBe('string')
    expect(label.length).toBeGreaterThan(10)
  })

  it('la etiqueta menciona "autodeclarada" o "autodeclarado"', () => {
    const label = SETTLEMENT_MODE_LABEL_ES['trust']
    expect(label.toLowerCase()).toContain('autodeclar')
  })
})
