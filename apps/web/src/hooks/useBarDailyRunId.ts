import { useQuery } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'
import type { DashboardSport } from '@/hooks/useDashboardUrlState'
import type { DailyRunPage } from '@/types/api'

/**
 * ID del run del día para enlaces «Eventos» / «Picks»: prioriza `primary_daily_run_id`
 * del resumen; si aún no viene (carga o null en API), pide /daily-runs en paralelo
 * para no ocultar los botones al cambiar de pestaña (nueva queryKey del dashboard).
 */
export function useBarDailyRunId(opts: {
  runDate: string
  sport: DashboardSport
  primaryDailyRunId: number | null | undefined
}) {
  const hintQ = useQuery({
    queryKey: ['daily-runs-bar', opts.runDate, opts.sport],
    // Mientras no hay ID definitivo del resumen (undefined en carga, o null si no hay run en summary).
    enabled: opts.primaryDailyRunId == null,
    queryFn: async () => {
      const sp = new URLSearchParams({
        run_date: opts.runDate,
        sport: opts.sport,
        limit: '1',
      })
      return fetchJson<DailyRunPage>(`/daily-runs?${sp}`)
    },
  })

  const barRunId =
    opts.primaryDailyRunId != null
      ? opts.primaryDailyRunId
      : (hintQ.data?.items[0]?.daily_run_id ?? null)

  return { barRunId, hintLoading: hintQ.isLoading }
}
