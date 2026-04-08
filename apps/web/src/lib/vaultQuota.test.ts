import { describe, expect, it } from 'vitest'
import type { Bt2TakenPickRecord, Bt2VaultPickOut } from '@/lib/bt2Types'
import {
  computeVaultQuota,
  VAULT_DAILY_CAP_PREMIUM,
  VAULT_DAILY_CAP_STANDARD,
} from '@/lib/vaultQuota'

const day = '2026-04-07'

function vpick(id: string, tier: 'standard' | 'premium'): Bt2VaultPickOut {
  return {
    id,
    eventId: 1,
    marketClass: 'h2h',
    marketLabelEs: 'H2H',
    eventLabel: id,
    titulo: '',
    suggestedDecimalOdds: 2,
    edgeBps: 0,
    selectionSummaryEs: 'A',
    traduccionHumana: '',
    curvaEquidad: [],
    accessTier: tier,
    unlockCostDp: tier === 'premium' ? 50 : 0,
    operatingDayKey: day,
    isAvailable: true,
    kickoffUtc: '2026-04-07T20:00:00.000Z',
    eventStatus: 'scheduled',
    externalSearchUrl: '',
    premiumUnlocked: false,
    timeBand: 'evening',
  }
}

function taken(
  vaultPickId: string,
  tier?: 'standard' | 'premium',
  odk?: string,
): Bt2TakenPickRecord {
  return {
    vaultPickId,
    bt2PickId: 1,
    eventId: 1,
    market: 'h2h',
    selection: 'A',
    oddsAccepted: 2,
    stakeUnits: 1,
    openedAt: '2026-04-07T12:00:00.000Z',
    eventLabel: 'X',
    operatingDayKey: odk,
    accessTier: tier,
  }
}

describe('vaultQuota', () => {
  it('cuenta tomas del día con operatingDayKey en registro', () => {
    const api = [vpick('s1', 'standard'), vpick('p1', 'premium')]
    const t = [
      taken('s1', 'standard', day),
      taken('p1', 'premium', day),
    ]
    const q = computeVaultQuota(t, day, api)
    expect(q.standardTaken).toBe(1)
    expect(q.premiumTaken).toBe(1)
    expect(q.standardRemaining).toBe(VAULT_DAILY_CAP_STANDARD - 1)
    expect(q.premiumRemaining).toBe(VAULT_DAILY_CAP_PREMIUM - 1)
  })

  it('ignora registros de otro día operativo', () => {
    const api = [vpick('s1', 'standard')]
    const t = [taken('s1', 'standard', '2026-04-06')]
    const q = computeVaultQuota(t, day, api)
    expect(q.standardTaken).toBe(0)
    expect(q.atStandardCap).toBe(false)
  })

  it('legacy sin tier en registro: infiere desde apiPicks mismo día', () => {
    const api = [vpick('s1', 'standard')]
    const t: Bt2TakenPickRecord[] = [
      {
        vaultPickId: 's1',
        bt2PickId: 9,
        eventId: 1,
        market: 'h2h',
        selection: 'A',
        oddsAccepted: 2,
        stakeUnits: 1,
        openedAt: '2026-04-07T12:00:00.000Z',
        eventLabel: 'X',
      },
    ]
    const q = computeVaultQuota(t, day, api)
    expect(q.standardTaken).toBe(1)
  })

  it('cap flags', () => {
    const api = [
      vpick('a', 'standard'),
      vpick('b', 'standard'),
      vpick('c', 'standard'),
    ]
    const t = [
      taken('a', 'standard', day),
      taken('b', 'standard', day),
      taken('c', 'standard', day),
    ]
    const q = computeVaultQuota(t, day, api)
    expect(q.atStandardCap).toBe(true)
    expect(q.standardRemaining).toBe(0)
  })
})
