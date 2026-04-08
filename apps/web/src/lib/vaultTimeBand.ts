/**
 * Sprint 05.2 / D-05.2-002 — franjas locales (misma semántica que `bt2_vault_pool.py`).
 * Mañana [08:00,12:00), Tarde [12:00,18:00), Noche [18:00,23:00), overnight resto.
 */
import type { Bt2VaultPickOut, Bt2VaultTimeBand } from '@/lib/bt2Types'

export const VAULT_TIME_BAND_ORDER: readonly Bt2VaultTimeBand[] = [
  'morning',
  'afternoon',
  'evening',
  'overnight',
] as const

/** Pestañas UI (overnight solo en mezcla). */
export type VaultBandTab = 'mix' | 'morning' | 'afternoon' | 'evening'

export const VAULT_BAND_TAB_LABELS_ES: Record<VaultBandTab, string> = {
  mix: 'Mezcla',
  morning: 'Mañana',
  afternoon: 'Tarde',
  evening: 'Noche',
}

export const VAULT_BAND_TABS: VaultBandTab[] = [
  'mix',
  'morning',
  'afternoon',
  'evening',
]

export function timeBandFromLocalMinutes(minutesSinceMidnight: number): Bt2VaultTimeBand {
  if (8 * 60 <= minutesSinceMidnight && minutesSinceMidnight < 12 * 60) {
    return 'morning'
  }
  if (12 * 60 <= minutesSinceMidnight && minutesSinceMidnight < 18 * 60) {
    return 'afternoon'
  }
  if (18 * 60 <= minutesSinceMidnight && minutesSinceMidnight < 23 * 60) {
    return 'evening'
  }
  return 'overnight'
}

/** Hora local del usuario en `timeZone` (IANA). */
export function getCurrentVaultTimeBand(
  timeZone: string,
  nowMs: number = Date.now(),
): Bt2VaultTimeBand {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone,
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
    }).formatToParts(new Date(nowMs))
    const hour = Number(parts.find((p) => p.type === 'hour')?.value ?? 0)
    const minute = Number(parts.find((p) => p.type === 'minute')?.value ?? 0)
    return timeBandFromLocalMinutes(hour * 60 + minute)
  } catch {
    return 'overnight'
  }
}

export function normalizePickTimeBand(b: string | undefined): Bt2VaultTimeBand {
  if (
    b === 'morning' ||
    b === 'afternoon' ||
    b === 'evening' ||
    b === 'overnight'
  ) {
    return b
  }
  return 'overnight'
}

/** Respuestas JSON a veces traen `time_band` (snake) si el alias no aplica. */
function readTimeBandField(p: Bt2VaultPickOut): string | undefined {
  const raw = p as Bt2VaultPickOut & { time_band?: string }
  if (typeof p.timeBand === 'string' && p.timeBand.trim()) return p.timeBand
  if (typeof raw.time_band === 'string' && raw.time_band.trim()) {
    return raw.time_band
  }
  return undefined
}

/**
 * Franja efectiva para filtrar/ordenar: API (`timeBand`) o derivada de `kickoffUtc`
 * en la TZ del usuario (misma lógica que `bt2_vault_pool.py` / “Inicio (tu zona)”).
 */
export function effectiveVaultTimeBand(
  pick: Bt2VaultPickOut,
  timeZone: string,
): Bt2VaultTimeBand {
  const fromApi = readTimeBandField(pick)
  if (
    fromApi === 'morning' ||
    fromApi === 'afternoon' ||
    fromApi === 'evening' ||
    fromApi === 'overnight'
  ) {
    return fromApi
  }
  const k = pick.kickoffUtc
  if (k != null && typeof k === 'string' && k.trim() !== '') {
    const ms = Date.parse(k)
    if (!Number.isNaN(ms)) {
      try {
        const parts = new Intl.DateTimeFormat('en-GB', {
          timeZone,
          hour: 'numeric',
          minute: 'numeric',
          hour12: false,
        }).formatToParts(new Date(ms))
        const hour = Number(parts.find((x) => x.type === 'hour')?.value ?? 0)
        const minute = Number(parts.find((x) => x.type === 'minute')?.value ?? 0)
        return timeBandFromLocalMinutes(hour * 60 + minute)
      } catch {
        /* fallthrough */
      }
    }
  }
  return 'overnight'
}

/**
 * Orden mezcla: franja más cercana “hacia adelante” en el ciclo día, luego kickoff.
 */
export function mixSortCompare(
  a: Bt2VaultPickOut,
  b: Bt2VaultPickOut,
  currentBand: Bt2VaultTimeBand,
  timeZone: string,
): number {
  const ia = VAULT_TIME_BAND_ORDER.indexOf(effectiveVaultTimeBand(a, timeZone))
  const ib = VAULT_TIME_BAND_ORDER.indexOf(effectiveVaultTimeBand(b, timeZone))
  const cur = VAULT_TIME_BAND_ORDER.indexOf(currentBand)
  const da = (ia - cur + 4) % 4
  const db = (ib - cur + 4) % 4
  if (da !== db) return da - db
  const ta = Date.parse(a.kickoffUtc) || 0
  const tb = Date.parse(b.kickoffUtc) || 0
  return ta - tb
}

export function filterVaultPicksByTab(
  picks: Bt2VaultPickOut[],
  tab: VaultBandTab,
  timeZone: string,
): Bt2VaultPickOut[] {
  if (tab === 'mix') return picks
  return picks.filter(
    (p) => effectiveVaultTimeBand(p, timeZone) === tab,
  )
}

export function sortVaultPicksForDisplay(
  picks: Bt2VaultPickOut[],
  tab: VaultBandTab,
  timeZone: string,
  nowMs?: number,
): Bt2VaultPickOut[] {
  const filtered = filterVaultPicksByTab(picks, tab, timeZone)
  if (tab === 'mix') {
    const cur = getCurrentVaultTimeBand(timeZone, nowMs)
    return [...filtered].sort((a, b) =>
      mixSortCompare(a, b, cur, timeZone),
    )
  }
  return [...filtered].sort(
    (a, b) => (Date.parse(a.kickoffUtc) || 0) - (Date.parse(b.kickoffUtc) || 0),
  )
}
