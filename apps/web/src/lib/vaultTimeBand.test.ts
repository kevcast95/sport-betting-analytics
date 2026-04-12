import { describe, expect, it } from 'vitest'
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import {
  filterVaultPicksByTab,
  getCurrentVaultTimeBand,
  mixSortCompare,
  reorderVaultPicksForBandCycle,
  selectVisibleFromOrderedPool,
  selectVisibleVaultPicks,
  sortVaultPicksForDisplay,
  timeBandFromLocalMinutes,
} from '@/lib/vaultTimeBand'

function pick(
  id: string,
  band: Bt2VaultPickOut['timeBand'],
  kickoffIso: string,
  slateRank?: number,
  eventNum?: number,
): Bt2VaultPickOut {
  return {
    id,
    eventId: eventNum ?? 1,
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
    ...(slateRank != null ? { slateRank } : {}),
  }
}

describe('vaultTimeBand', () => {
  it('timeBandFromLocalMinutes — bordes D-06-032', () => {
    expect(timeBandFromLocalMinutes(6 * 60)).toBe('morning')
    expect(timeBandFromLocalMinutes(11 * 60 + 59)).toBe('morning')
    expect(timeBandFromLocalMinutes(12 * 60)).toBe('afternoon')
    expect(timeBandFromLocalMinutes(17 * 60 + 59)).toBe('afternoon')
    expect(timeBandFromLocalMinutes(18 * 60)).toBe('evening')
    expect(timeBandFromLocalMinutes(23 * 60 + 59)).toBe('evening')
    expect(timeBandFromLocalMinutes(5 * 60 + 59)).toBe('overnight')
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

  it('reorderVaultPicksForBandCycle — ciclo 0 vs 1 cambia el frente del orden', () => {
    const a = pick('a', 'morning', '2026-04-07T13:00:00.000Z', 1, 101)
    const b = pick('b', 'afternoon', '2026-04-07T18:00:00.000Z', 2, 102)
    const c = pick('c', 'evening', '2026-04-07T23:00:00.000Z', 3, 103)
    const tz = 'UTC'
    const o0 = reorderVaultPicksForBandCycle([a, b, c], tz, 0)
    const o1 = reorderVaultPicksForBandCycle([a, b, c], tz, 1)
    expect(o0[0]?.id).toBe('a')
    expect(o1[0]?.id).toBe('b')
  })

  it('selectVisibleFromOrderedPool — conserva orden del pool ya barajado', () => {
    const ms = Date.parse('2026-04-07T15:00:00.000Z')
    const ordered = [
      pick('second', 'afternoon', '2026-04-07T18:00:00.000Z', 1, 201),
      pick('first', 'morning', '2026-04-07T13:00:00.000Z', 2, 202),
    ]
    const out = selectVisibleFromOrderedPool(ordered, 'America/Bogota', 2, ms)
    expect(out.map((p) => p.id)).toEqual(['first', 'second'])
  })

  it('selectVisibleVaultPicks — prioriza franja local actual y respeta cap', () => {
    const picks = [
      pick('eve', 'evening', '2026-04-07T23:00:00.000Z'),
      pick('morn', 'morning', '2026-04-07T13:00:00.000Z'),
      pick('aft', 'afternoon', '2026-04-07T18:00:00.000Z'),
    ]
    const ms = Date.parse('2026-04-07T15:00:00.000Z')
    const one = selectVisibleVaultPicks(picks, 'mix', 'America/Bogota', 1, ms)
    expect(one).toHaveLength(1)
    expect(one[0]?.id).toBe('morn')
    const two = selectVisibleVaultPicks(picks, 'mix', 'America/Bogota', 2, ms)
    expect(two.map((p) => p.id)).toEqual(['morn', 'aft'])
  })
})
