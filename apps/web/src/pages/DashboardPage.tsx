import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { DashboardPerformanceChart } from '@/components/DashboardPerformanceChart'
import { PickTelegramCard, type PickCardData } from '@/components/PickTelegramCard'
import { fetchJson } from '@/lib/api'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import { useUsersQuery } from '@/hooks/useUsersQuery'
import type { DashboardBundleOut, DashboardRecentPick } from '@/types/api'
import { formatCalendarDateEs, formatCOP } from '@/lib/formatDateTime'

function todayISO() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function recentToCard(r: DashboardRecentPick): PickCardData {
  return {
    pick_id: r.pick_id,
    daily_run_id: r.daily_run_id,
    event_id: r.event_id,
    market: r.market,
    selection: r.selection,
    picked_value: r.picked_value,
    odds_reference: r.odds_reference,
    event_label: r.event_label,
    league: r.league,
    kickoff_display: r.kickoff_display,
    kickoff_at_utc: r.kickoff_at_utc,
    created_at_utc: r.created_at_utc,
    user_outcome: r.user_outcome ?? undefined,
    system_outcome: r.outcome_system ?? undefined,
    result: null,
    user_taken: r.user_taken,
    decision_origin: r.decision_origin,
    stake_amount: r.stake_amount,
    selection_display: r.selection_display ?? undefined,
  }
}

function rejectReasonLabelEs(reason: string | null | undefined): string {
  const x = String(reason ?? '').trim().toLowerCase()
  if (x === 'lineups_not_ok') return 'alineaciones o datos base incompletos'
  if (x === 'h2h_not_ok') return 'historial H2H insuficiente'
  if (x === 'match_finished') return 'partido ya finalizado'
  return x ? `criterio técnico (${x})` : 'criterios técnicos'
}

export default function DashboardPage() {
  const { userId, setUserId } = useTrackingUser()
  const usersQ = useUsersQuery()
  const users = useMemo(() => usersQ.data ?? [], [usersQ.data])
  const [runDate, setRunDate] = useState(todayISO)
  const [onlyTaken, setOnlyTaken] = useState(false)
  if (userId == null && onlyTaken) {
    setOnlyTaken(false)
  }

  const dashQ = useQuery({
    queryKey: ['dashboard', runDate, userId, onlyTaken],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate })
      if (userId != null) sp.set('user_id', String(userId))
      if (onlyTaken) sp.set('only_taken', 'true')
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })

  const s = dashQ.data?.summary

  useEffect(() => {
    if (users.length === 0) return
    if (userId == null) setUserId(users[0].user_id)
    else if (!users.some((u) => u.user_id === userId)) setUserId(users[0].user_id)
  }, [users, userId, setUserId])

  return (
    <div>
      <div className="mb-2 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-app-fg md:text-3xl">
            Dashboard
          </h1>
          <p className="mt-1 max-w-xl text-sm text-app-muted">
            <span className="font-medium text-violet-900">
              {formatCalendarDateEs(runDate)}
            </span>
            <span className="mx-1 text-app-line">·</span>
            <span className="font-mono text-xs tabular-nums">{runDate}</span>
            {' — '}
            {s
              ? `${s.events_total} eventos totales · ${s.picks_total} picks del modelo`
              : 'eventos y picks del modelo'}
          </p>
          {s && (s.selection_passed_filters > 0 || s.selection_rejected > 0) && (
            <div className="mt-2 space-y-1 text-xs text-app-muted">
              <p>
                • <span className="text-app-fg">{s.selection_rejected}</span> eventos
                se descartaron por filtros previos (principalmente{' '}
                {rejectReasonLabelEs(s.selection_top_reject_reason)}).
              </p>
              <p>
                • <span className="text-app-fg">{s.selection_analyzed_without_pick}</span>{' '}
                eventos sí pasaron análisis, pero no terminaron en pick por falta de
                valor suficiente.
              </p>
            </div>
          )}
        </div>
        <Link
          to="/runs"
          className="inline-flex shrink-0 items-center justify-center rounded-lg bg-app-accent px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:opacity-90"
        >
          Ver runs
        </Link>
      </div>

      <div className="mb-8 mt-6 flex flex-wrap items-start gap-4 border-b border-app-line pb-6">
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
                  Tarjetas alineadas al mensaje de Telegram · desliza en móvil
                </p>
                {userId != null && s.bankroll_cop != null && (
                  <p className="mt-1 font-mono text-[11px] font-semibold tabular-nums text-violet-900">
                    Bankroll actual: {formatCOP(s.bankroll_cop)}
                  </p>
                )}
              </div>
              {dashQ.data?.recent[0] && (
                <Link
                  to={`/runs/${dashQ.data.recent[0].daily_run_id}/picks`}
                  className="text-xs font-medium text-app-fg underline decoration-app-line underline-offset-2"
                >
                  Abrir tablero del run →
                </Link>
              )}
            </div>

            {dashQ.data?.recent.length === 0 ? (
              <p className="rounded-xl border border-dashed border-app-line bg-app-card p-8 text-center text-sm text-app-muted">
                No hay picks para esta fecha
                {onlyTaken ? ' (con filtro «solo tomados»)' : ''}.
              </p>
            ) : (
              <div className="-mx-1 flex gap-4 overflow-x-auto pb-4 pt-1 snap-x snap-mandatory">
                {dashQ.data?.recent.map((r, i) => (
                  <PickTelegramCard
                    key={r.pick_id}
                    p={recentToCard(r)}
                    runDate={runDate}
                    pickOrdinal={i + 1}
                    detailHref={`/picks/${r.pick_id}`}
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
