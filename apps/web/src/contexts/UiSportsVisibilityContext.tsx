import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { DashboardSport } from '@/hooks/useDashboardUrlState'
import {
  type UiSportsVisibleMap,
  dashboardSportFromRunSlug,
  loadUiSportsVisibleFromStorage,
  saveUiSportsVisibleToStorage,
} from '@/lib/uiSportsVisibility'

type Ctx = {
  visible: UiSportsVisibleMap
  setSportVisible: (sport: DashboardSport, on: boolean) => void
  /** Deporte visible según slug del run (football|tennis); desconocido → true */
  isRunSportVisible: (runSportSlug: string) => boolean
}

const UiSportsVisibilityContext = createContext<Ctx | null>(null)

export function UiSportsVisibilityProvider({ children }: { children: ReactNode }) {
  const [visible, setVisible] = useState<UiSportsVisibleMap>(() =>
    loadUiSportsVisibleFromStorage(),
  )

  const setSportVisible = useCallback((sport: DashboardSport, on: boolean) => {
    setVisible((prev) => {
      const next = { ...prev, [sport]: on }
      if (!next.football && !next.tennis) {
        return prev
      }
      saveUiSportsVisibleToStorage(next)
      return next
    })
  }, [])

  const isRunSportVisible = useCallback(
    (runSportSlug: string) => {
      const sp = dashboardSportFromRunSlug(runSportSlug)
      if (sp == null) return true
      return visible[sp]
    },
    [visible],
  )

  const v = useMemo(
    () => ({ visible, setSportVisible, isRunSportVisible }),
    [visible, setSportVisible, isRunSportVisible],
  )

  return (
    <UiSportsVisibilityContext.Provider value={v}>
      {children}
    </UiSportsVisibilityContext.Provider>
  )
}

export function useUiSportsVisibility() {
  const x = useContext(UiSportsVisibilityContext)
  if (!x) {
    throw new Error('useUiSportsVisibility debe usarse dentro de UiSportsVisibilityProvider')
  }
  return x
}
