import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { DashboardPerformanceChart } from '@/components/DashboardPerformanceChart'
import { PickInboxRow } from '@/components/PickInboxRow'
import { fetchJson } from '@/lib/api'
import { useBarDailyRunId } from '@/hooks/useBarDailyRunId'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import { useUsersQuery } from '@/hooks/useUsersQuery'
import type { DashboardBundleOut } from '@/types/api'
import { formatCOP } from '@/lib/formatDateTime'

export default function DashboardPage() {
  const { userId, setUserId } = useTrackingUser()
  const { runDate, setRunDate, onlyTaken, setOnlyTaken, sport } =
    useDashboardUrlState()
  const usersQ = useUsersQuery()
  const users = useMemo(() => usersQ.data ?? [], [usersQ.data])
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

  useEffect(() => {
    if (users.length === 0) return
    if (userId == null) setUserId(users[0].user_id)
    else if (!users.some((u) => u.user_id === userId)) setUserId(users[0].user_id)
  }, [users, userId, setUserId])

  return (
    <div>
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
        <label className="flex flex-col gap-1 text-xs text-app-muted">
          Usuario
          <select
            className="min-w-[10rem] rounded-md border border-app-line bg-app-card px-3 py-2 text-sm text-app-fg"
            value={userId != null ? String(userId) : ''}
            onChange={(e) => {
              const v = e.target.value
              setUserId(v === '' ? null : Number(v))
            }}
            disabled={usersQ.isLoading || users.length === 0}
          >
            {users.length === 0 ? (
              <option value="">{usersQ.isLoading ? 'Cargando…' : 'Sin usuarios'}</option>
            ) : (
              users.map((u) => (
                <option key={u.user_id} value={String(u.user_id)}>
                  {u.display_name}
                </option>
              ))
            )}
          </select>
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
                <h2 className="text-sm font-semibold">Picks del día</h2>
                <p className="text-xs text-app-muted">
                  Vista bandeja: toca una fila para abrir la ficha con detalle,
                  Telegram-style y seguimiento.
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

            {dashQ.data?.recent.length === 0 ? (
              <p className="rounded-xl border border-dashed border-app-line bg-app-card p-8 text-center text-sm text-app-muted">
                No hay picks para esta fecha
                {onlyTakenForQuery ? ' (con filtro «solo tomados»)' : ''}.
              </p>
            ) : (
              <div className="overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
                {dashQ.data?.recent.map((r, i) => (
                  <PickInboxRow
                    key={r.pick_id}
                    pickId={r.pick_id}
                    href={`/picks/${r.pick_id}`}
                    eventLabel={r.event_label}
                    league={r.league}
                    market={r.market}
                    selection={r.selection}
                    selectionDisplay={r.selection_display}
                    pickedValue={r.picked_value}
                    outcome={r.outcome}
                    userTaken={r.user_taken}
                    ordinal={i + 1}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
