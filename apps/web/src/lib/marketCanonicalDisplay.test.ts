import { describe, expect, it } from 'vitest'
import { displayMarketLabelEs } from '@/lib/marketCanonicalDisplay'

describe('displayMarketLabelEs', () => {
  it('prioriza marketCanonicalLabelEs', () => {
    expect(
      displayMarketLabelEs({
        marketCanonicalLabelEs: 'Más / menos 2.5 goles',
        marketLabelEs: 'Otro',
        marketClass: 'ML_TOTAL_OVER',
      }),
    ).toBe('Más / menos 2.5 goles')
  })

  it('usa marketLabelEs si no hay canónico', () => {
    expect(
      displayMarketLabelEs({
        marketLabelEs: 'Etiqueta CDM',
        marketClass: 'X',
      }),
    ).toBe('Etiqueta CDM')
  })

  it('cae en getMarketLabelEs por marketClass', () => {
    expect(
      displayMarketLabelEs({
        marketClass: 'ML_SIDE',
      }),
    ).toBe('Ganador del partido')
  })

  it('devuelve — si no hay datos', () => {
    expect(displayMarketLabelEs({})).toBe('—')
  })
})
