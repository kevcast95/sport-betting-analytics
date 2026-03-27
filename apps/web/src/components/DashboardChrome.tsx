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
 * Barra superior del dashboard (fuera del scroll principal del contenido).
 * Comparte query con DashboardPage vía React Query (misma queryKey).
 */
export function DashboardChrome() {
  const { runDate, setRunDate, onlyTaken, setOnlyTaken, sport } = useDashboardUrlState()
  const { userId } = useTrackingUser()
  const onlyTakenForQuery = userId != null && onlyTaken
  const { bankrollCOP, setBankrollCOP, isBankrollSaving } = useBankrollCOP(userId)

  const dashQ = useQuery({
    queryKey: ['dashboard', runDate, userId, onlyTakenForQuery, sport],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', '1')
      sp.set('recent_page', '0')
      if (userId != null) sp.set('user_id', String(userId))
      if (onlyTakenForQuery) sp.set('only_taken', 'true')
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
    <header className="shrink-0 border-b border-app-line bg-app-card/95 backdrop-blur-sm">
      <div className="mx-auto max-w-5xl px-3 py-4 sm:px-4 md:px-8 md:py-5">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <SportPillTabs className="max-w-md" />
          {barRunId != null && (
            <div className="flex shrink-0 flex-wrap items-end gap-2">
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
              <button
                type="button"
                onClick={() => shiftRunDate(-1)}
                className="rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm hover:bg-violet-50/60"
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
                  className="rounded-md border border-app-line bg-white px-2 py-1.5 text-xs text-app-fg"
                />
              </label>
              <button
                type="button"
                onClick={() => shiftRunDate(1)}
                className="rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm hover:bg-violet-50/60"
                title="Día siguiente"
              >
                →
              </button>
              {userId != null && (
                <label className="mb-1 flex cursor-pointer items-center gap-2 text-xs text-app-fg">
                  <input
                    type="checkbox"
                    className="rounded border-app-line"
                    checked={onlyTaken}
                    onChange={(e) => setOnlyTaken(e.target.checked)}
                  />
                  Solo picks que tomé
                </label>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span className="rounded border border-app-line bg-white px-2 py-1 font-mono text-app-fg">
              Run #{barRunId ?? '—'}
            </span>
            <span className="rounded border border-app-line bg-white px-2 py-1 text-app-muted">
              Rechazados filtro: <span className="font-mono text-app-fg">{s?.selection_rejected ?? '—'}</span>
            </span>
            <span className="rounded border border-app-line bg-white px-2 py-1 text-app-muted">
              Sin pick tras análisis: <span className="font-mono text-app-fg">{s?.selection_analyzed_without_pick ?? '—'}</span>
            </span>
          </div>
          <div className="min-w-0">
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
          <div className="flex w-full items-center justify-between gap-3 rounded-lg border border-app-line bg-app-card px-3 py-2">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                Bankroll (COP)
              </p>
              <p className="font-mono text-sm tabular-nums text-violet-900">
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
                className="w-28 rounded-md border border-violet-200 bg-white px-2 py-1.5 font-mono text-xs text-app-fg tabular-nums shadow-sm"
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
                className="rounded-md border border-app-line bg-white px-2.5 py-1.5 text-xs text-app-fg shadow-sm disabled:opacity-40"
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
