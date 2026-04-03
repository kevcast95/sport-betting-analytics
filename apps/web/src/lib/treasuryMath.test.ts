import { describe, expect, it } from 'vitest'
import {
  STAKE_PCT_MAX,
  STAKE_PCT_MIN,
  computeUnitValue,
  parseCopIntegerInput,
} from './treasuryMath'

describe('computeUnitValue', () => {
  it('calcula 2% de N como N * 0.02', () => {
    expect(computeUnitValue(1_000_000, 2)).toBe(20_000)
  })

  it('respeta 0,25% y 5%', () => {
    expect(computeUnitValue(400_000, 0.25)).toBe(1_000)
    expect(computeUnitValue(200_000, STAKE_PCT_MAX)).toBe(10_000)
    expect(computeUnitValue(200_000, STAKE_PCT_MIN)).toBe(500)
  })

  it('devuelve NaN con entradas no finitas', () => {
    expect(Number.isNaN(computeUnitValue(Number.NaN, 2))).toBe(true)
  })
})

describe('parseCopIntegerInput', () => {
  it('extrae dígitos', () => {
    expect(parseCopIntegerInput('5.000.000')).toBe(5000000)
    expect(parseCopIntegerInput('abc')).toBeNaN()
  })
})
