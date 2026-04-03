import type { DashboardSport } from '@/hooks/useDashboardUrlState'

const STORAGE_KEY = 'altea:ui:sports-visible'

export type UiSportsVisibleMap = Record<DashboardSport, boolean>

export const UI_SPORTS_DEFAULT_VISIBLE: UiSportsVisibleMap = {
  football: true,
  tennis: true,
}

export function dashboardSportFromRunSlug(raw: string): DashboardSport | null {
  const x = String(raw || '')
    .trim()
    .toLowerCase()
  if (x === 'tennis') return 'tennis'
  if (x === 'football') return 'football'
  return null
}

export function loadUiSportsVisibleFromStorage(): UiSportsVisibleMap {
  try {
    const t = localStorage.getItem(STORAGE_KEY)
    if (!t) return { ...UI_SPORTS_DEFAULT_VISIBLE }
    const p = JSON.parse(t) as Partial<UiSportsVisibleMap>
    return {
      football: p.football !== false,
      tennis: p.tennis !== false,
    }
  } catch {
    return { ...UI_SPORTS_DEFAULT_VISIBLE }
  }
}

export function saveUiSportsVisibleToStorage(v: UiSportsVisibleMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(v))
  } catch {
    /* ignore */
  }
}

export function firstVisibleSport(v: UiSportsVisibleMap): DashboardSport {
  if (v.football) return 'football'
  if (v.tennis) return 'tennis'
  return 'football'
}
