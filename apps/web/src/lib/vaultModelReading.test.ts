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
    expect(
      isGenericCdmTraduccionEs(
        'Señal basada en reglas CDM — sin narrativa DSR extendida para este ítem.',
      ),
    ).toBe(true)
  })

  it('unifiedApiModelReading: DSR API + narrativa', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: 'Narrativa DSR breve.',
      traduccionHumana: 'Selección basada en datos CDM BT2 — modelo en construcción.',
      dsrSource: 'dsr_api',
    })
    expect(u.body).toBe('Narrativa DSR breve.')
    expect(u.title).toContain('razonador')
  })

  it('unifiedApiModelReading: DSR API + sin narrativa + placeholder CDM → sin mezclar con ingesta', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Señal basada en reglas CDM — sin narrativa DSR extendida para este ítem.',
      dsrSource: 'dsr_api',
    })
    expect(u.title).toContain('Sin narrativa DSR')
    expect(u.body).toMatch(/fallo de ingesta/)
  })

  it('unifiedApiModelReading: reglas/fallback + placeholder → copy alternativo', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Selección basada en datos CDM BT2 — modelo en construcción.',
      dsrSource: 'rules_fallback',
    })
    expect(u.body).toBe(RULES_FALLBACK_MODEL_COPY_ES)
    expect(u.title).toContain('alternativa')
  })

  it('unifiedApiModelReading: sin dsr_api + lectura CDM útil', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Contenido analítico real.',
      dsrSource: 'rules_fallback',
    })
    expect(u.body).toBe('Contenido analítico real.')
    expect(u.title).toContain('CDM')
  })

  it('unifiedApiModelReading: origen vacío no implica razonador en vivo', () => {
    const u = unifiedApiModelReading({
      dsrNarrativeEs: '',
      traduccionHumana: '',
      dsrSource: '',
    })
    expect(u.title).toContain('alternativa')
    expect(u.body).toBe(RULES_FALLBACK_MODEL_COPY_ES)
  })
})
