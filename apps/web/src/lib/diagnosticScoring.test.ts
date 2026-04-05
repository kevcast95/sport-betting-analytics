import { describe, expect, it } from 'vitest'
import {
  DIAGNOSTIC_INITIAL_INTEGRITY,
  computeOperatorProfile,
  disciplinePointsPreview,
  integrityAfterAnswer,
} from '@/lib/diagnosticScoring'

describe('diagnosticScoring', () => {
  it('aplica deltas A +0.04, B 0, C −0.06 y acota a [0,1]', () => {
    let v = DIAGNOSTIC_INITIAL_INTEGRITY
    v = integrityAfterAnswer(v, 0)
    expect(v).toBeCloseTo(DIAGNOSTIC_INITIAL_INTEGRITY + 0.04, 4)
    v = integrityAfterAnswer(v, 1)
    expect(v).toBeCloseTo(DIAGNOSTIC_INITIAL_INTEGRITY + 0.04, 4)
    v = integrityAfterAnswer(v, 2)
    expect(v).toBeCloseTo(DIAGNOSTIC_INITIAL_INTEGRITY + 0.04 - 0.06, 4)
  })

  it('asigna perfil por mayoría A vs C (empate → francotirador)', () => {
    expect(computeOperatorProfile([0, 0, 0, 0, 0])).toBe('THE_GUARDIAN')
    expect(computeOperatorProfile([2, 2, 2, 2, 2])).toBe('THE_VOLATILE')
    expect(computeOperatorProfile([0, 2, 1, 1, 1])).toBe('THE_SNIPER')
    expect(computeOperatorProfile([0, 2, 0, 2, 1])).toBe('THE_SNIPER')
  })

  it('disciplinePointsPreview reacciona a la integridad', () => {
    const base = 1000
    const atInit = disciplinePointsPreview(base, DIAGNOSTIC_INITIAL_INTEGRITY)
    const higher = disciplinePointsPreview(base, DIAGNOSTIC_INITIAL_INTEGRITY + 0.1)
    expect(higher).toBeGreaterThan(atInit)
  })
})
