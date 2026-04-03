import { useEffect } from 'react'
import { useUiSportsVisibility } from '@/contexts/UiSportsVisibilityContext'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { firstVisibleSport } from '@/lib/uiSportsVisibility'

/**
 * Si la URL apunta a un deporte oculto en Configuración, corrige a un deporte visible (replace).
 */
export function SportUrlSync() {
  const { visible } = useUiSportsVisibility()
  const { sport, setSport } = useDashboardUrlState()

  useEffect(() => {
    if (visible[sport]) return
    setSport(firstVisibleSport(visible))
  }, [visible, sport, setSport])

  return null
}
