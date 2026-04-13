import { describe, expect, it } from 'vitest'
import {
  MODEL_WHY_FALLBACK_DSR_MISSING_ES,
  MODEL_WHY_FALLBACK_RULES_ES,
  MODEL_WHY_TITLE_ES,
  isGenericCdmTraduccionEs,
  modelWhyReading,
  unifiedApiModelReading,
} from '@/lib/vaultModelReading'

describe('vaultModelReading', () => {
  it('isGenericCdmTraduccionEs detecta placeholder legacy', () => {
    expect(
      isGenericCdmTraduccionEs(
        'Selección basada en datos CDM BT2 — modelo en construcción.',
      ),
    ).toBe(true)
    expect(isGenericCdmTraduccionEs('Mejor volumen ofensivo y factor local.')).toBe(
      false,
    )
  })

  it('modelWhyReading: narrativa DSR gana (como razon v1)', () => {
    const m = modelWhyReading({
      dsrNarrativeEs:
        'Las rachas recientes muestran tendencia a partidos con menos de 2.5 goles.',
      traduccionHumana: 'Selección basada en datos CDM BT2 — modelo en construcción.',
      dsrSource: 'dsr_api',
    })
    expect(m.title).toBe(MODEL_WHY_TITLE_ES)
    expect(m.body).toContain('2.5 goles')
  })

  it('modelWhyReading: DSR API sin narrativa + placeholder → copy corto', () => {
    const m = modelWhyReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Señal basada en reglas CDM — sin narrativa DSR extendida para este ítem.',
      dsrSource: 'dsr_api',
    })
    expect(m.body).toBe(MODEL_WHY_FALLBACK_DSR_MISSING_ES)
  })

  it('modelWhyReading: rules_fallback + placeholder → copy mercado (sin jerga)', () => {
    const m = modelWhyReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Selección basada en datos CDM BT2 — modelo en construcción.',
      dsrSource: 'rules_fallback',
    })
    expect(m.body).toBe(MODEL_WHY_FALLBACK_RULES_ES)
  })

  it('modelWhyReading: rules_fallback + texto útil (estilo razon telegram)', () => {
    const m = modelWhyReading({
      dsrNarrativeEs: '',
      traduccionHumana: 'Mejor volumen ofensivo en temporada y factor local.',
      dsrSource: 'rules_fallback',
    })
    expect(m.body).toBe('Mejor volumen ofensivo en temporada y factor local.')
  })

  it('modelWhyReading: ignora narrativas con jerga CDM/DSR persistidas (evita doble bloque)', () => {
    const junk =
      'En Premier League, Chelsea frente a Manchester City, la línea 1X2 del CDM inclina la lectura hacia el visitante. Esta fila no incluye narrativa extendida del análisis DSR; sigue criterios del protocolo sobre las cuotas disponibles.'
    const m = modelWhyReading({
      dsrNarrativeEs: junk,
      traduccionHumana: junk,
      dsrSource: 'rules_fallback',
    })
    expect(m.body).toBe(MODEL_WHY_FALLBACK_RULES_ES)
  })

  it('unifiedApiModelReading coincide con modelWhyReading', () => {
    expect(
      unifiedApiModelReading({
        dsrNarrativeEs: 'X',
        traduccionHumana: '',
        dsrSource: 'dsr_api',
      }),
    ).toEqual(modelWhyReading({
      dsrNarrativeEs: 'X',
      traduccionHumana: '',
      dsrSource: 'dsr_api',
    }))
  })
})
