import { describe, expect, it } from 'vitest'
import { parseBt2DpInsufficientPremiumDetail } from '@/lib/api'

describe('parseBt2DpInsufficientPremiumDetail (D-05-005)', () => {
  it('parsea detail 402 canónico', () => {
    const d = parseBt2DpInsufficientPremiumDetail({
      code: 'dp_insufficient_for_premium_unlock',
      message: 'Saldo insuficiente',
      requiredDp: 50,
      currentDp: 12,
    })
    expect(d).toEqual({
      code: 'dp_insufficient_for_premium_unlock',
      message: 'Saldo insuficiente',
      requiredDp: 50,
      currentDp: 12,
    })
  })

  it('rechaza code incorrecto', () => {
    expect(
      parseBt2DpInsufficientPremiumDetail({
        code: 'other',
        message: 'x',
      }),
    ).toBeNull()
  })
})
