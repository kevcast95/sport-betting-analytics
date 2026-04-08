import { describe, expect, it } from 'vitest'
import { isKickoffUtcInPast } from '@/lib/vaultKickoff'

describe('isKickoffUtcInPast', () => {
  it('false sin ISO o inválido', () => {
    expect(isKickoffUtcInPast(undefined)).toBe(false)
    expect(isKickoffUtcInPast('')).toBe(false)
    expect(isKickoffUtcInPast('not-a-date')).toBe(false)
  })

  it('true cuando now >= kickoff', () => {
    const past = '2020-01-01T12:00:00.000Z'
    expect(isKickoffUtcInPast(past, Date.parse('2025-01-01T00:00:00.000Z'))).toBe(
      true,
    )
  })

  it('false antes del kickoff', () => {
    const future = '2099-06-15T18:00:00.000Z'
    expect(isKickoffUtcInPast(future, Date.parse('2026-01-01T00:00:00.000Z'))).toBe(
      false,
    )
  })
})
