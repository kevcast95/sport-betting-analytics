import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { todayISO } from '@/lib/dashboardUtils'

export type DashboardSport = 'football' | 'tennis'

/**
 * Estado en URL: fecha / solo tomados / deporte (dashboard + lista de runs).
 */
export function useDashboardUrlState() {
  const [searchParams, setSearchParams] = useSearchParams()

  const runDate = useMemo(
    () => searchParams.get('run_date') ?? todayISO(),
    [searchParams],
  )
  const onlyTaken = useMemo(
    () => searchParams.get('only_taken') === '1',
    [searchParams],
  )
  const sport: DashboardSport = useMemo(
    () => (searchParams.get('sport') === 'tennis' ? 'tennis' : 'football'),
    [searchParams],
  )

  const setRunDate = useCallback((d: string) => {
    setSearchParams(
      (prev) => {
        const n = new URLSearchParams(prev)
        const t = todayISO()
        if (d === t) n.delete('run_date')
        else n.set('run_date', d)
        return n
      },
      { replace: true },
    )
  }, [setSearchParams])

  const setOnlyTaken = useCallback(
    (v: boolean) => {
      setSearchParams(
        (prev) => {
          const n = new URLSearchParams(prev)
          if (v) n.set('only_taken', '1')
          else n.delete('only_taken')
          return n
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const setSport = useCallback(
    (next: DashboardSport) => {
      setSearchParams(
        (prev) => {
          const n = new URLSearchParams(prev)
          if (next === 'football') n.delete('sport')
          else n.set('sport', 'tennis')
          return n
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  return { runDate, setRunDate, onlyTaken, setOnlyTaken, sport, setSport }
}
