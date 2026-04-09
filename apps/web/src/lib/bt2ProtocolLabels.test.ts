import { describe, expect, it } from 'vitest'
import {
  dsrConfidenceLabelEs,
  dsrSourceDescriptionEs,
  modelPredictionResultEs,
  pickStatusLabelEs,
} from '@/lib/bt2ProtocolLabels'

describe('bt2ProtocolLabels', () => {
  it('dsrConfidenceLabelEs', () => {
    expect(dsrConfidenceLabelEs('low')).toBe('Baja')
    expect(dsrConfidenceLabelEs('medium')).toBe('Media')
  })

  it('dsrSourceDescriptionEs', () => {
    expect(dsrSourceDescriptionEs('rules_fallback')).toContain('reglas')
    expect(dsrSourceDescriptionEs('dsr_api')).toContain('razonador')
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
