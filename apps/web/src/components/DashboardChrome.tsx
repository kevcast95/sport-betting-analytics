import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchJson } from '@/lib/api'
import { rejectReasonLabelEs } from '@/lib/dashboardUtils'
import { formatCalendarDateEs } from '@/lib/formatDateTime'
import { SportPillTabs } from '@/components/SportPillTabs'
import { useBarDailyRunId } from '@/hooks/useBarDailyRunId'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { DashboardBundleOut } from '@/types/api'

/**
 * Barra superior del dashboard (fuera del scroll principal del contenido).
 * Comparte query con DashboardPage vía React Query (misma queryKey).
 */
export function DashboardChrome() {
  const { runDate, onlyTaken, sport } = useDashboardUrlState()
  const { userId } = useTrackingUser()
  const onlyTakenForQuery = userId != null && onlyTaken

  const dashQ = useQuery({
    queryKey: ['dashboard', runDate, userId, onlyTakenForQuery, sport],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      if (userId != null) sp.set('user_id', String(userId))
      if (onlyTakenForQuery) sp.set('only_taken', 'true')
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })

  const s = dashQ.data?.summary
  const { barRunId } = useBarDailyRunId({
    runDate,
    sport,
    primaryDailyRunId: s?.primary_daily_run_id,
  })

  return (
    <header className="shrink-0 border-b border-app-line bg-app-card/95 backdrop-blur-sm">
      <div className="mx-auto max-w-5xl px-3 py-4 sm:px-4 md:px-8 md:py-5">
        <SportPillTabs className="mb-4 max-w-md" />
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between md:gap-6">
          <div className="min-w-0 md:max-w-[min(100%,42rem)]">
            <h1 className="text-2xl font-semibold tracking-tight text-app-fg md:text-3xl">
              Dashboard
            </h1>
            <p className="mt-1 text-sm text-app-muted">
              <span className="font-medium text-violet-900">
                {formatCalendarDateEs(runDate)}
              </span>
              <span className="mx-1 text-app-line">·</span>
              <span className="font-mono text-xs tabular-nums">{runDate}</span>
              {' — '}
              {s
                ? `${s.events_total} eventos totales · ${s.picks_total} picks del modelo`
                : dashQ.isLoading
                  ? 'Cargando resumen…'
                  : 'eventos y picks del modelo'}
            </p>
            {s && (
              <details className="mt-3 rounded-md border border-app-line bg-white/60 text-xs text-app-muted open:bg-white/80">
                <summary className="cursor-pointer select-none px-3 py-2 font-medium text-app-fg marker:text-violet-700">
                  Filtrado previo al modelo (por qué entraron o no los eventos)
                </summary>
                <div className="space-y-2 border-t border-app-line px-3 py-2.5 leading-relaxed">
                  <p>
                    •{' '}
                    <span className="text-app-fg">{s.selection_rejected}</span>{' '}
                    eventos se descartaron por filtros previos (principalmente{' '}
                    {rejectReasonLabelEs(s.selection_top_reject_reason)}).
                  </p>
                  <p>
                    •{' '}
                    <span className="text-app-fg">
                      {s.selection_analyzed_without_pick}
                    </span>{' '}
                    eventos sí pasaron análisis, pero no terminaron en pick por
                    falta de valor suficiente.
                  </p>
                </div>
              </details>
            )}
          </div>
          {barRunId != null && (
            <div className="flex shrink-0 flex-wrap gap-2 md:pt-1">
              <Link
                to={`/runs/${barRunId}/events`}
                className="inline-flex items-center justify-center rounded-lg border border-app-line bg-white px-3 py-2 text-xs font-medium text-app-fg shadow-sm hover:bg-violet-50/60"
              >
                Eventos del día
              </Link>
              <Link
                to={`/runs/${barRunId}/picks`}
                className="inline-flex items-center justify-center rounded-lg border border-app-line bg-white px-3 py-2 text-xs font-medium text-app-fg shadow-sm hover:bg-violet-50/60"
              >
                Tablero picks
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
