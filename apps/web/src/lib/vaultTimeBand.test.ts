import { describe, expect, it } from 'vitest'
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import {
  filterVaultPicksByTab,
  getCurrentVaultTimeBand,
  mixSortCompare,
  sortVaultPicksForDisplay,
  timeBandFromLocalMinutes,
} from '@/lib/vaultTimeBand'

function pick(
  id: string,
  band: Bt2VaultPickOut['timeBand'],
  kickoffIso: string,
): Bt2VaultPickOut {
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
    accessTier: 'standard',
    unlockCostDp: 0,
    operatingDayKey: '2026-04-07',
    isAvailable: true,
    kickoffUtc: kickoffIso,
    eventStatus: 'scheduled',
    externalSearchUrl: '',
    premiumUnlocked: false,
    timeBand: band,
  }
}

describe('vaultTimeBand', () => {
  it('timeBandFromLocalMinutes — bordes D-05.2-002', () => {
    expect(timeBandFromLocalMinutes(8 * 60)).toBe('morning')
    expect(timeBandFromLocalMinutes(11 * 60 + 59)).toBe('morning')
    expect(timeBandFromLocalMinutes(12 * 60)).toBe('afternoon')
    expect(timeBandFromLocalMinutes(17 * 60 + 59)).toBe('afternoon')
    expect(timeBandFromLocalMinutes(18 * 60)).toBe('evening')
    expect(timeBandFromLocalMinutes(22 * 60 + 59)).toBe('evening')
    expect(timeBandFromLocalMinutes(23 * 60)).toBe('overnight')
    expect(timeBandFromLocalMinutes(7 * 60 + 59)).toBe('overnight')
  })

  it('filterVaultPicksByTab — overnight solo en mezcla', () => {
    const picks = [
      pick('a', 'morning', '2026-04-07T13:00:00.000Z'),
      pick('b', 'overnight', '2026-04-07T06:00:00.000Z'),
    ]
    expect(filterVaultPicksByTab(picks, 'mix', 'UTC')).toHaveLength(2)
    expect(filterVaultPicksByTab(picks, 'morning', 'UTC')).toHaveLength(1)
    expect(filterVaultPicksByTab(picks, 'morning', 'UTC')[0]?.id).toBe('a')
    expect(filterVaultPicksByTab(picks, 'evening', 'UTC')).toHaveLength(0)
  })

  it('effectiveVaultTimeBand — sin timeBand útil: deriva de kickoffUtc + TZ', () => {
    const p = pick('n', 'morning', '2026-04-08T15:00:00.000Z')
    ;(p as { timeBand?: string }).timeBand = ''
    const bogota = filterVaultPicksByTab([p], 'morning', 'America/Bogota')
    expect(bogota).toHaveLength(1)
  })

  it('filterVaultPicksByTab — lee time_band (snake) si existe', () => {
    const raw = {
      ...pick('s', 'morning', '2026-04-07T20:00:00.000Z'),
      timeBand: undefined as unknown as Bt2VaultPickOut['timeBand'],
      time_band: 'afternoon',
    } as Bt2VaultPickOut & { time_band: string }
    expect(filterVaultPicksByTab([raw], 'afternoon', 'UTC')).toHaveLength(1)
    expect(filterVaultPicksByTab([raw], 'morning', 'UTC')).toHaveLength(0)
  })

  it('mixSortCompare — prioriza franja actual', () => {
    const morning = pick('m', 'morning', '2026-04-07T14:00:00.000Z')
    const evening = pick('e', 'evening', '2026-04-07T23:00:00.000Z')
    expect(mixSortCompare(morning, evening, 'morning', 'UTC')).toBeLessThan(0)
    expect(mixSortCompare(evening, morning, 'morning', 'UTC')).toBeGreaterThan(0)
  })

  it('sortVaultPicksForDisplay — mezcla sin mutar origen', () => {
    const picks = [
      pick('z', 'evening', '2026-04-07T20:00:00.000Z'),
      pick('m', 'morning', '2026-04-07T14:00:00.000Z'),
    ]
    const sorted = sortVaultPicksForDisplay(
      picks,
      'mix',
      'UTC',
      Date.parse('2026-04-07T10:00:00.000Z'),
    )
    expect(picks[0]?.id).toBe('z')
    expect(sorted[0]?.id).toBe('m')
  })

  it('getCurrentVaultTimeBand — TZ válida', () => {
    const b = getCurrentVaultTimeBand('UTC', Date.parse('2026-04-07T10:30:00.000Z'))
    expect(['morning', 'afternoon', 'evening', 'overnight']).toContain(b)
  })
})
