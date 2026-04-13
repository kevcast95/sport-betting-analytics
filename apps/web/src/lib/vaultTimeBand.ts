/**
 * D-06-032 / US-BE-044 — misma semántica que `apps/api/bt2_vault_pool.py`.
 * Mañana [06:00,12:00), Tarde [12:00,18:00), Noche [18:00,24:00), overnight [00:00,06:00).
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
  if (6 * 60 <= minutesSinceMidnight && minutesSinceMidnight < 12 * 60) {
    return 'morning'
  }
  if (12 * 60 <= minutesSinceMidnight && minutesSinceMidnight < 18 * 60) {
    return 'afternoon'
  }
  if (18 * 60 <= minutesSinceMidnight && minutesSinceMidnight < 24 * 60) {
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

/** Alineado a `bt2_vault_pool.VAULT_VALUE_POOL_UNIVERSE_MAX`. */
export const VAULT_LOCAL_UNIVERSE_MAX = 20

const VAULT_LOCAL_MAX_PER_BAND = 5

function rotatedBandOrderForCycle(cycleOffset: number): Bt2VaultTimeBand[] {
  const bo = [...VAULT_TIME_BAND_ORDER]
  const k = ((cycleOffset % bo.length) + bo.length) % bo.length
  return [...bo.slice(k), ...bo.slice(0, k)]
}

/**
 * Reordena el pool ya cargado (misma semántica de barrido por franja que `compose_vault_daily_picks`
 * en servidor, sin tiers sintéticos: solo orden de los mismos objetos pick).
 */
export function reorderVaultPicksForBandCycle(
  picks: Bt2VaultPickOut[],
  timeZone: string,
  bandCycleOffset: number,
): Bt2VaultPickOut[] {
  if (picks.length === 0) return []
  const sorted = [...picks].sort((a, b) => {
    const ra = a.slateRank ?? 9999
    const rb = b.slateRank ?? 9999
    if (ra !== rb) return ra - rb
    return a.id.localeCompare(b.id)
  })

  const buckets: Record<Bt2VaultTimeBand, Bt2VaultPickOut[]> = {
    morning: [],
    afternoon: [],
    evening: [],
    overnight: [],
  }
  const seenInBuckets = new Set<number>()
  for (const p of sorted) {
    if (seenInBuckets.has(p.eventId)) continue
    seenInBuckets.add(p.eventId)
    const band = effectiveVaultTimeBand(p, timeZone)
    buckets[band].push(p)
  }

  const chosen: Bt2VaultPickOut[] = []
  const chosenIds = new Set<number>()
  const bandOrder = rotatedBandOrderForCycle(bandCycleOffset)

  for (const band of bandOrder) {
    let slot = 0
    for (const p of buckets[band]) {
      if (chosen.length >= VAULT_LOCAL_UNIVERSE_MAX) return chosen
      if (slot >= VAULT_LOCAL_MAX_PER_BAND) break
      if (chosenIds.has(p.eventId)) continue
      chosen.push(p)
      chosenIds.add(p.eventId)
      slot += 1
    }
  }

  for (const p of sorted) {
    if (chosen.length >= VAULT_LOCAL_UNIVERSE_MAX) break
    if (chosenIds.has(p.eventId)) continue
    chosen.push(p)
    chosenIds.add(p.eventId)
  }

  return chosen
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

/**
 * Elige hasta `visibleCap` picks para la grilla: primero la franja local actual, luego el resto
 * en el orden de `sortVaultPicksForDisplay` (mezcla).
 */
export function selectVisibleVaultPicks(
  picks: Bt2VaultPickOut[],
  tab: VaultBandTab,
  timeZone: string,
  visibleCap: number,
  nowMs: number = Date.now(),
): Bt2VaultPickOut[] {
  const cap = Math.max(0, Math.floor(visibleCap))
  if (cap === 0 || picks.length === 0) return []
  const curBand = getCurrentVaultTimeBand(timeZone, nowMs)
  const sorted = sortVaultPicksForDisplay(picks, tab, timeZone, nowMs)
  const inBand = sorted.filter((p) => effectiveVaultTimeBand(p, timeZone) === curBand)
  const rest = sorted.filter((p) => effectiveVaultTimeBand(p, timeZone) !== curBand)
  const out: Bt2VaultPickOut[] = []
  const seen = new Set<string>()
  for (const p of [...inBand, ...rest]) {
    if (out.length >= cap) break
    if (seen.has(p.id)) continue
    seen.add(p.id)
    out.push(p)
  }
  return out
}

/**
 * Como `selectVisibleVaultPicks` pero **respeta el orden** de `orderedPicks` (p. ej. tras
 * `reorderVaultPicksForBandCycle`): primero los de la franja local actual, luego el resto
 * en ese mismo orden — sin volver a mezclar con `mixSortCompare`.
 *
 * `slateCycleOffset` (0–3, alineado a «Regenerar cartelera»): desplaza una ventana circular de
 * `visibleCap` ítems sobre esa lista priorizada. Sin esto, si hay muchos partidos en la misma
 * franja, los visibles serían siempre los mismos 5 aunque cambie el orden global del pool.
 */
export function selectVisibleFromOrderedPool(
  orderedPicks: Bt2VaultPickOut[],
  timeZone: string,
  visibleCap: number,
  nowMs: number = Date.now(),
  slateCycleOffset: number = 0,
): Bt2VaultPickOut[] {
  const cap = Math.max(0, Math.floor(visibleCap))
  if (cap === 0 || orderedPicks.length === 0) return []
  const curBand = getCurrentVaultTimeBand(timeZone, nowMs)
  const inBand = orderedPicks.filter((p) => effectiveVaultTimeBand(p, timeZone) === curBand)
  const rest = orderedPicks.filter((p) => effectiveVaultTimeBand(p, timeZone) !== curBand)
  const primary = [...inBand, ...rest]
  const n = primary.length
  if (n <= cap) {
    const short: Bt2VaultPickOut[] = []
    const seenShort = new Set<string>()
    for (const p of primary) {
      if (seenShort.has(p.id)) continue
      seenShort.add(p.id)
      short.push(p)
      if (short.length >= cap) break
    }
    return short
  }
  const c = ((Math.floor(Number(slateCycleOffset)) % 4) + 4) % 4
  const start = (c * cap) % n
  const out: Bt2VaultPickOut[] = []
  const seen = new Set<string>()
  for (let i = 0; i < n && out.length < cap; i++) {
    const p = primary[(start + i) % n]!
    if (seen.has(p.id)) continue
    seen.add(p.id)
    out.push(p)
  }
  return out
}
