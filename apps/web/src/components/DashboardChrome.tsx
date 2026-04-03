import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchJson } from '@/lib/api'
import { rejectReasonLabelEs } from '@/lib/dashboardUtils'
import { formatCalendarDateEs } from '@/lib/formatDateTime'
import { SportPillTabs } from '@/components/SportPillTabs'
import { useBarDailyRunId } from '@/hooks/useBarDailyRunId'
import { useBankrollCOP } from '@/hooks/useBankrollCOP'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { DashboardBundleOut } from '@/types/api'

/**
 * Cabecera del dashboard: permanece fija mientras solo el <main> hace scroll
 * (ver AppLayout). Comparte query con DashboardPage vía React Query (misma queryKey).
 */
export function DashboardChrome() {
  const { runDate, setRunDate, sport } = useDashboardUrlState()
  const { userId } = useTrackingUser()
  const { bankrollCOP, setBankrollCOP, isBankrollSaving } = useBankrollCOP(userId)

  const dashQ = useQuery({
    queryKey: ['dashboard', runDate, userId, sport],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', '1')
      sp.set('recent_page', '0')
      if (userId != null) sp.set('user_id', String(userId))
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })

  const s = dashQ.data?.summary
  const bankrollDraft = bankrollCOP != null ? String(Math.round(bankrollCOP)) : ''
  const shiftRunDate = (days: number) => {
    const [y, m, d] = runDate.split('-').map((v) => Number(v))
    if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return
    const dt = new Date(Date.UTC(y, m - 1, d))
    if (Number.isNaN(dt.getTime())) return
    dt.setUTCDate(dt.getUTCDate() + days)
    setRunDate(dt.toISOString().slice(0, 10))
  }
  const { barRunId } = useBarDailyRunId({
    runDate,
    sport,
    primaryDailyRunId: s?.primary_daily_run_id,
  })

  return (
    <header className="z-20 shrink-0 border-b border-app-accent-line bg-gradient-to-b from-app-accent-soft/90 via-white to-white shadow-[0_1px_0_0_rgba(76,29,149,0.04)]">
      <div className="mx-auto max-w-5xl px-3 py-3 sm:px-4 md:px-8 md:py-4">
        <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <SportPillTabs className="max-w-md" />
          {barRunId != null && (
            <div className="flex shrink-0 flex-wrap items-end gap-2">
              <Link
                to={`/runs/${barRunId}/events`}
                className="inline-flex items-center justify-center rounded-md border border-violet-200/80 bg-white px-3 py-2 text-xs font-medium text-violet-950 shadow-sm hover:border-violet-300 hover:bg-violet-50/80"
              >
                Eventos del día
              </Link>
              <button
                type="button"
                onClick={() => shiftRunDate(-1)}
                className="rounded-md border border-violet-200/70 bg-white px-2 py-2 text-xs text-violet-950 shadow-sm hover:bg-violet-50/70"
                title="Día anterior"
              >
                ←
              </button>
              <label className="flex flex-col gap-1 text-[11px] text-app-muted">
                Fecha
                <input
                  type="date"
                  value={runDate}
                  onChange={(e) => setRunDate(e.target.value)}
                  className="rounded-md border border-violet-200/70 bg-white px-2 py-1.5 text-xs text-app-fg shadow-sm focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-300/50"
                />
              </label>
              <button
                type="button"
                onClick={() => shiftRunDate(1)}
                className="rounded-md border border-violet-200/70 bg-white px-2 py-2 text-xs text-violet-950 shadow-sm hover:bg-violet-50/70"
                title="Día siguiente"
              >
                →
              </button>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-3">
          <div className="min-w-0">
            <h1 className="font-serif text-2xl font-normal tracking-tight text-violet-950 md:text-3xl">
              Dashboard
            </h1>
            <p className="mt-1 text-sm text-app-muted">
              <span className="font-medium text-app-fg">
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
              <details className="mt-3 rounded-md border border-violet-200/60 bg-white/80 text-xs text-app-muted shadow-sm backdrop-blur-[2px]">
                <summary className="cursor-pointer select-none px-3 py-2 font-medium leading-snug text-violet-950">
                  Pre-filtro del modelo: run{' '}
                  <span className="font-mono text-app-fg">#{barRunId ?? '—'}</span>
                  {' · '}
                  <span className="font-mono text-app-fg">{s.selection_rejected}</span> descartados
                  {' · '}
                  <span className="font-mono text-app-fg">{s.selection_analyzed_without_pick}</span> sin pick
                  tras análisis
                  <span className="block pt-0.5 text-[10px] font-normal text-app-muted">
                    Ampliar para ver motivos (no confundir con picks operativos vs análisis del tablero).
                  </span>
                </summary>
                <div className="space-y-2 border-t border-violet-100 px-3 py-2.5 leading-relaxed">
                  <p className="text-[11px] text-app-muted">
                    Esto ocurre <strong className="text-app-fg">antes</strong> de generar picks: cuántos eventos ni
                    siquiera llegan al modelo por filtros, y cuántos se analizaron pero no produjeron pick por falta
                    de valor.
                  </p>
                  <p>
                    •{' '}
                    <span className="text-app-fg">{s.selection_rejected}</span>{' '}
                    eventos descartados por filtros previos (principalmente{' '}
                    {rejectReasonLabelEs(s.selection_top_reject_reason)}).
                  </p>
                  <p>
                    •{' '}
                    <span className="text-app-fg">
                      {s.selection_analyzed_without_pick}
                    </span>{' '}
                    eventos pasaron análisis pero no terminaron en pick por falta de valor suficiente.
                  </p>
                </div>
              </details>
            )}
          </div>
          <div className="flex w-full items-center justify-between gap-3 rounded-lg border border-violet-200/70 bg-gradient-to-r from-violet-50/95 via-white to-violet-50/50 px-3 py-2.5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.7)]">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-800/80">
                Bankroll (COP)
              </p>
              <p className="font-mono text-sm tabular-nums text-violet-950">
                {bankrollCOP != null && bankrollCOP > 0
                  ? new Intl.NumberFormat('es-CO', {
                      style: 'currency',
                      currency: 'COP',
                      maximumFractionDigits: 0,
                    }).format(bankrollCOP)
                  : 'Sin monto'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                inputMode="numeric"
                defaultValue={bankrollDraft}
                placeholder="Recargar"
                className="w-28 rounded-md border border-violet-200/80 bg-white/90 px-2 py-1.5 font-mono text-xs text-violet-950 tabular-nums shadow-sm focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-300/40"
                disabled={userId == null || isBankrollSaving}
                onBlur={(e) => {
                  const raw = e.target.value.trim()
                  if (raw === '') {
                    setBankrollCOP(null)
                    return
                  }
                  const n = Number.parseInt(raw, 10)
                  if (!Number.isNaN(n) && n >= 0) setBankrollCOP(n)
                }}
                onChange={(e) => {
                  e.target.value = e.target.value.replace(/[^\d]/g, '')
                }}
              />
              <button
                type="button"
                className="rounded-md border border-violet-300/60 bg-white px-2.5 py-1.5 text-xs font-medium text-violet-900 shadow-sm hover:bg-violet-100/80 disabled:opacity-40"
                disabled={userId == null || isBankrollSaving}
                onClick={(e) => {
                  const input = (e.currentTarget.previousElementSibling as HTMLInputElement | null)
                  const raw = input?.value.trim() ?? ''
                  if (raw === '') {
                    setBankrollCOP(null)
                    return
                  }
                  const n = Number.parseInt(raw, 10)
                  if (!Number.isNaN(n) && n >= 0) setBankrollCOP(n)
                }}
              >
                Editar
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
