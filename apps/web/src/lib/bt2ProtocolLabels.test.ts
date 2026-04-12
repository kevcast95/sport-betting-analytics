import { describe, expect, it } from 'vitest'
import {
  dsrConfidenceLabelEs,
  dsrSourceDescriptionAdminEs,
  modelPredictionResultEs,
  pickStatusLabelEs,
  vektorModelConfidenceLineEs,
} from '@/lib/bt2ProtocolLabels'

describe('bt2ProtocolLabels', () => {
  it('dsrConfidenceLabelEs', () => {
    expect(dsrConfidenceLabelEs('low')).toBe('Baja')
    expect(dsrConfidenceLabelEs('medium')).toBe('Media')
  })

  it('dsrSourceDescriptionAdminEs', () => {
    expect(dsrSourceDescriptionAdminEs('rules_fallback')).toContain('reglas')
    expect(dsrSourceDescriptionAdminEs('dsr_api')).toContain('razonador')
  })

  it('vektorModelConfidenceLineEs', () => {
    expect(vektorModelConfidenceLineEs('high')).toBe('Confianza del modelo: Alta')
    expect(vektorModelConfidenceLineEs('')).toBe('')
  })

  it('modelPredictionResultEs', () => {
    expect(modelPredictionResultEs('hit')).toBe('Acierto')
    expect(modelPredictionResultEs('n_a')).toBe('N/D')
    expect(modelPredictionResultEs(null)).toBe('—')
  })

  it('pickStatusLabelEs', () => {
    expect(pickStatusLabelEs('won')).toBe('Ganado')
    expect(pickStatusLabelEs('open')).toBe('Abierto')
  })
})
