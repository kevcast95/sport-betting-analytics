import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ListPagination } from '@/components/ListPagination'
import { Link } from 'react-router-dom'
import { DashboardPerformanceChart } from '@/components/DashboardPerformanceChart'
import { PickInboxRow } from '@/components/PickInboxRow'
import { ViewContextBar } from '@/components/ViewContextBar'
import { fetchJson } from '@/lib/api'
import { usePickOutcomeQuickMutation } from '@/hooks/usePickOutcomeQuickMutation'
import { usePickOutcomeAutoQuickMutation } from '@/hooks/usePickOutcomeAutoQuickMutation'
import { useBarDailyRunId } from '@/hooks/useBarDailyRunId'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { useListPageSize } from '@/hooks/useListPageSize'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { DashboardBundleOut } from '@/types/api'
import { formatCOP } from '@/lib/formatDateTime'

type OddsRef = Record<string, unknown> | null | undefined

function refStr(ref: OddsRef, key: string): string | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = (ref as Record<string, unknown>)[key]
  if (v == null) return undefined
  return String(v)
}

export default function DashboardPage() {
  const { userId } = useTrackingUser()
  const { runDate, setRunDate, onlyTaken, setOnlyTaken, sport } =
    useDashboardUrlState()
  const onlyTakenForQuery = userId != null && onlyTaken
  const quickOutcomeM = usePickOutcomeQuickMutation(userId)
  const quickAutoOutcomeM = usePickOutcomeAutoQuickMutation(userId)
  const [recentListPage, setRecentListPage] = useState(0)
  const { pageSize: recentPageSize, setPageSize: setRecentPageSize } =
    useListPageSize()

  useEffect(() => {
    setRecentListPage(0)
  }, [runDate, onlyTakenForQuery, sport, userId, recentPageSize])

  const dashQ = useQuery({
    queryKey: [
      'dashboard',
      runDate,
      userId,
      onlyTakenForQuery,
      sport,
      recentListPage,
      recentPageSize,
    ],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', String(recentPageSize))
      sp.set('recent_page', String(recentListPage))
      if (userId != null) sp.set('user_id', String(userId))
      if (onlyTakenForQuery) sp.set('only_taken', 'true')
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })

  const s = dashQ.data?.summary

  useEffect(() => {
    const t = dashQ.data?.recent_total
    if (t === undefined) return
    const maxP =
      t <= 0 ? 0 : Math.max(0, Math.ceil(t / recentPageSize) - 1)
    if (recentListPage > maxP) setRecentListPage(maxP)
  }, [dashQ.data?.recent_total, recentPageSize, recentListPage])

  const { barRunId } = useBarDailyRunId({
    runDate,
    sport,
    primaryDailyRunId: s?.primary_daily_run_id,
  })

  return (
    <div>
      <ViewContextBar crumbs={[{ label: 'Inicio', to: '/' }, { label: 'Dashboard' }]} />
      <div className="mb-8 flex flex-wrap items-start gap-4 border-b border-app-line pb-6">
        <label className="flex flex-col gap-1 text-xs text-app-muted">
          Fecha del run (picks con este día)
          <input
            type="date"
            value={runDate}
            onChange={(e) => setRunDate(e.target.value)}
            className="rounded-md border border-app-line bg-app-card px-3 py-2 text-sm text-app-fg"
          />
        </label>
        {userId != null && (
          <label className="flex cursor-pointer items-center gap-2 text-xs text-app-fg">
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

      {dashQ.isError && (
        <p className="mb-4 text-sm text-app-danger whitespace-pre-wrap">
          {(dashQ.error as Error).message}
        </p>
      )}

      {dashQ.isLoading && (
        <p className="text-sm text-app-muted">Cargando resumen…</p>
      )}

      {s && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-app-line border-l-4 border-l-violet-500 bg-app-card p-4 shadow-sm">
              <p className="text-xs font-medium text-app-muted">
                Picks modelo · {runDate}
              </p>
              <p className="mt-2 text-2xl font-semibold tabular-nums">
                {s.picks_total}
              </p>
              <p className="mt-1 text-xs text-app-muted">
                {s.outcome_wins} ganados · {s.outcome_losses} perdidos ·{' '}
                {s.outcome_pending} pendientes (todos)
              </p>
            </div>
            <div className="rounded-xl border border-app-line border-l-4 border-l-sky-500 bg-app-card p-4 shadow-sm">
              <p className="text-xs font-medium text-app-muted">
                Tomados · resultado
              </p>
              <p className="mt-2 text-2xl font-semibold tabular-nums">
                {userId != null ? s.picks_taken_count : '—'}
              </p>
              <p className="mt-1 text-xs text-app-muted">
                {userId != null
                  ? `${s.taken_outcome_wins} gan. · ${s.taken_outcome_losses} perd. · ${s.taken_outcome_pending} pend.`
                  : 'Elige usuario'}
              </p>
            </div>
            <div className="rounded-xl border border-app-line border-l-4 border-l-emerald-500 bg-app-card p-4 shadow-sm">
              <p className="text-xs font-medium text-app-muted">
                Bankroll · saldo neto
              </p>
              <p
                className={`mt-2 text-2xl font-semibold tabular-nums ${
                  s.bankroll_cop != null && s.bankroll_cop >= 0
                    ? 'text-app-success'
                    : s.bankroll_cop != null
                      ? 'text-app-danger'
                      : ''
                }`}
              >
                {userId != null && s.bankroll_cop != null
                  ? formatCOP(s.bankroll_cop)
                  : '—'}
              </p>
              <p className="mt-1 text-xs text-app-muted">
                {userId != null
                  ? 'Persistido en servidor: sube con cada pick tomado que ganas y baja si pierdes.'
                  : 'Elige usuario'}
              </p>
              {userId != null &&
                s.has_stake_data &&
                s.net_pl_estimate != null && (
                  <p className="mt-2 border-t border-app-line pt-2 text-[10px] leading-relaxed text-app-muted">
                    P/L del día (solo referencia, picks de esta fecha):{' '}
                    <span
                      className={`font-mono font-medium tabular-nums ${
                        s.net_pl_estimate >= 0
                          ? 'text-emerald-800'
                          : 'text-red-800'
                      }`}
                    >
                      {s.net_pl_estimate >= 0 ? '+' : ''}
                      {formatCOP(s.net_pl_estimate)}
                    </span>
                  </p>
                )}
            </div>
          </div>

          <div className="mt-8">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Rendimiento</h2>
              <p className="mt-0.5 text-xs text-app-muted">
                Proporción ganadas / perdidas / pendientes: total del día, tomados
                y no tomados (resultado efectivo).
              </p>
              <div className="mt-6">
                <DashboardPerformanceChart
                  performance={s.performance}
                  hasUser={userId != null}
                />
              </div>
            </div>
          </div>

          <div className="mt-10">
            <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-sm font-semibold">Picks del día (vista previa)</h2>
                <p className="text-xs text-app-muted">
                  Misma fila que el tablero del run: a la derecha puedes marcar{' '}
                  <strong className="text-app-fg">Gané / Perdí / Pend.</strong> sin abrir la ficha.
                  Los botones del header (fecha) llevan a picks y eventos sin pasar por el historial
                  de runs.
                </p>
                {userId != null && s.bankroll_cop != null && (
                  <p className="mt-1 font-mono text-[11px] font-semibold tabular-nums text-violet-900">
                    Bankroll actual: {formatCOP(s.bankroll_cop)}
                  </p>
                )}
              </div>
              {barRunId != null && (
                <Link
                  to={`/runs/${barRunId}/picks`}
                  className="text-xs font-medium text-app-fg underline decoration-app-line underline-offset-2"
                >
                  Abrir tablero completo del run →
                </Link>
              )}
            </div>

            {(dashQ.data?.recent_total ?? 0) === 0 ? (
              <p className="rounded-xl border border-dashed border-app-line bg-app-card p-8 text-center text-sm text-app-muted">
                No hay picks para esta fecha
                {onlyTakenForQuery ? ' (con filtro «solo tomados»)' : ''}.
              </p>
            ) : (
              <>
              <ListPagination
                className="mb-2"
                idPrefix="dash-recent"
                page={recentListPage}
                pageSize={recentPageSize}
                total={dashQ.data?.recent_total ?? 0}
                onPageChange={setRecentListPage}
                onPageSizeChange={setRecentPageSize}
              />
              <div className="overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
                {dashQ.data?.recent.map((r, i) => (
                  <PickInboxRow
                    key={r.pick_id}
                    pickId={r.pick_id}
                    eventId={r.event_id}
                    href={`/picks/${r.pick_id}`}
                    eventLabel={r.event_label}
                    league={r.league}
                    market={r.market}
                    selection={r.selection}
                    selectionDisplay={r.selection_display}
                    pickedValue={r.picked_value}
                    kickoffDisplay={r.kickoff_display ?? null}
                    confidence={refStr(r.odds_reference as OddsRef, 'confianza') ?? null}
                    outcome={r.outcome}
                    userTaken={r.user_taken}
                    ordinal={recentListPage * recentPageSize + i + 1}
                    onQuickOutcome={
                      userId != null
                        ? (o) =>
                            quickOutcomeM.mutate({
                              pickId: r.pick_id,
                              dailyRunId: r.daily_run_id,
                              taken: r.user_taken ?? false,
                              outcome: o,
                            })
                        : undefined
                    }
                    quickOutcomePending={
                      quickOutcomeM.isPending &&
                      quickOutcomeM.variables?.pickId === r.pick_id
                    }
                    onQuickAutoOutcome={
                      userId != null
                        ? () =>
                            quickAutoOutcomeM.mutate({
                              pickId: r.pick_id,
                              dailyRunId: r.daily_run_id,
                              taken: r.user_taken ?? false,
                            })
                        : undefined
                    }
                    quickAutoOutcomePending={
                      quickAutoOutcomeM.isPending &&
                      quickAutoOutcomeM.variables?.pickId === r.pick_id
                    }
                  />
                ))}
              </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
