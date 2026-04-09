import { describe, expect, it } from 'vitest'
import {
  RULES_FALLBACK_MODEL_COPY_ES,
  isGenericCdmTraduccionEs,
  unifiedApiModelReading,
} from '@/lib/vaultModelReading'

describe('vaultModelReading', () => {
  it('isGenericCdmTraduccionEs detecta placeholder CDM', () => {
    expect(
      isGenericCdmTraduccionEs(
        'Selección basada en datos CDM BT2 — modelo en construcción.',
      ),
    ).toBe(true)
    expect(isGenericCdmTraduccionEs('Análisis concreto del partido y cuotas.')).toBe(
      false,
    )
  })

  it('unifiedApiModelReading: DSR gana sobre traducción genérica', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: 'Narrativa DSR breve.',
      traduccionHumana: 'Selección basada en datos CDM BT2 — modelo en construcción.',
    })
    expect(u.body).toBe('Narrativa DSR breve.')
    expect(u.title).toContain('DSR')
  })

  it('unifiedApiModelReading: sin DSR, placeholder CDM → solo fallback reglas', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Selección basada en datos CDM BT2 — modelo en construcción.',
    })
    expect(u.body).toBe(RULES_FALLBACK_MODEL_COPY_ES)
    expect(u.title).toContain('DSR')
  })

  it('unifiedApiModelReading: sin DSR, lectura CDM útil', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Contenido analítico real.',
    })
    expect(u.body).toBe('Contenido analítico real.')
    expect(u.title).toBe('Lectura del modelo')
  })
})
