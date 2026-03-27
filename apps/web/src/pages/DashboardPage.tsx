import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { DashboardPerformanceChart } from '@/components/DashboardPerformanceChart'
import { PickInboxRow } from '@/components/PickInboxRow'
import { fetchJson } from '@/lib/api'
import { useBarDailyRunId } from '@/hooks/useBarDailyRunId'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { DashboardBundleOut } from '@/types/api'
import { formatCOP } from '@/lib/formatDateTime'

function pct(v: number | null | undefined, digits = 1): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`
}

function pctPlain(v: number | null | undefined, digits = 1): string {
  if (v == null) return '—'
  return `${(v * 100).toFixed(digits)}%`
}

function confidenceFromOddsReference(raw: unknown): string | null {
  if (!raw || typeof raw !== 'object') return null
  const obj = raw as Record<string, unknown>
  const direct = obj.confidence ?? obj.confianza
  if (typeof direct === 'string' && direct.trim().length > 0) return direct.trim()
  return null
}

function confidenceRank(bucket: string): number | null {
  const b = bucket.trim().toLowerCase()
  if (b === 'baja') return 1
  if (b === 'media') return 2
  if (b === 'media-alta' || b === 'media alta') return 3
  if (b === 'alta') return 4
  return null
}

export default function DashboardPage() {
  const { userId } = useTrackingUser()
  const { runDate, setRunDate, onlyTaken, setOnlyTaken, sport } =
    useDashboardUrlState()
  const onlyTakenForQuery = userId != null && onlyTaken
  const previewLimit = 5
  const [activeTab, setActiveTab] = useState<'operacion' | 'analitica'>(
    'operacion'
  )

  const dashQ = useQuery({
    queryKey: [
      'dashboard',
      runDate,
      userId,
      onlyTakenForQuery,
      sport,
    ],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', String(previewLimit))
      sp.set('recent_page', '0')
      if (userId != null) sp.set('user_id', String(userId))
      if (onlyTakenForQuery) sp.set('only_taken', 'true')
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })
  const takenTodayQ = useQuery({
    queryKey: ['dashboard-taken-today', runDate, userId, sport],
    enabled: userId != null,
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', '20')
      sp.set('recent_page', '0')
      sp.set('only_taken', 'true')
      sp.set('user_id', String(userId))
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })

  const s = dashQ.data?.summary
  const selectedSportRolling = (dashQ.data?.rolling_by_sport ?? []).find(
    (r) => r.sport === sport
  )
  const roi100 = selectedSportRolling?.roi_tradable_100 ?? null
  const dd30 = selectedSportRolling?.drawdown_units_30d ?? null
  const trend = dashQ.data?.calibration?.daily_trend ?? []
  const lastDay = trend.length > 0 ? trend[trend.length - 1] : null
  const prevDay = trend.length > 1 ? trend[trend.length - 2] : null
  const twoRedDays =
    lastDay != null &&
    prevDay != null &&
    (lastDay.roi_unit ?? 0) < 0 &&
    (prevDay.roi_unit ?? 0) < 0
  const mode: 'subir' | 'mantener' | 'bajar' =
    twoRedDays || (roi100 != null && roi100 < 0) || (dd30 != null && dd30 > 10)
      ? 'bajar'
      : roi100 != null && roi100 > 0.1 && (dd30 == null || dd30 <= 6)
        ? 'subir'
        : 'mantener'
  const modeLabel =
    mode === 'subir'
      ? 'SUBIR EXPOSICION (con cuidado)'
      : mode === 'bajar'
        ? 'BAJAR EXPOSICION'
        : 'MANTENER EXPOSICION'
  const modeTone =
    mode === 'subir'
      ? 'text-emerald-700 border-emerald-200'
      : mode === 'bajar'
        ? 'text-red-700 border-red-200'
        : 'text-amber-700 border-amber-200'
  const modeCardTone =
    mode === 'subir'
      ? 'border-emerald-200 bg-emerald-50/60'
      : mode === 'bajar'
        ? 'border-red-200 bg-red-50/60'
        : 'border-amber-200 bg-amber-50/60'
  const minBucketSample = 30
  const confidenceRows = dashQ.data?.calibration?.by_confidence ?? []
  const confidenceRowsKnown = confidenceRows
    .map((r) => ({ ...r, rank: confidenceRank(r.bucket) }))
    .filter((r) => r.rank != null)
    .sort((a, b) => (a.rank as number) - (b.rank as number))
  const sufficientSample = confidenceRowsKnown.every((r) => r.settled >= minBucketSample)
  let monotonicOk = true
  for (let i = 1; i < confidenceRowsKnown.length; i += 1) {
    const prev = confidenceRowsKnown[i - 1].hit_rate ?? -1
    const curr = confidenceRowsKnown[i].hit_rate ?? -1
    if (curr < prev) {
      monotonicOk = false
      break
    }
  }
  const calibrationLabel = !sufficientSample
    ? 'Muestra insuficiente'
    : monotonicOk
      ? 'Calibración estable'
      : 'Calibración inestable'
  const calibrationTone = !sufficientSample
    ? 'text-amber-700 border-amber-200'
    : monotonicOk
      ? 'text-emerald-700 border-emerald-200'
      : 'text-red-700 border-red-200'

  const { barRunId } = useBarDailyRunId({
    runDate,
    sport,
    primaryDailyRunId: s?.primary_daily_run_id,
  })
  const systemStatus =
    mode === 'subir'
      ? 'AGRESIVO CONTROLADO'
      : mode === 'bajar'
        ? 'DEFENSIVO'
        : 'NEUTRAL'
  const recommendedAction =
    mode === 'subir'
      ? 'Subir stake +10% y mantener límites diarios.'
      : mode === 'bajar'
        ? 'Reducir exposición y bajar stake al 50%.'
        : 'Mantener stake y reevaluar al cierre del día.'
  const topPicksPreview = (dashQ.data?.recent ?? []).slice(0, 5)
  const todayProfitLoss = s?.net_pl_estimate ?? null

  return (
    <div>
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
          <section className="mb-6 rounded-2xl border border-app-line bg-app-card p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-app-muted">
              Daily Summary
            </p>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs text-app-muted">Bankroll actual</p>
                <p className="font-mono text-2xl font-semibold tabular-nums text-violet-900">
                  {userId != null && s.bankroll_cop != null ? formatCOP(s.bankroll_cop) : '—'}
                </p>
                <p className="text-xs text-app-muted">
                  Hoy:{' '}
                  <span
                    className={`font-mono ${
                      todayProfitLoss == null
                        ? 'text-app-muted'
                        : todayProfitLoss >= 0
                          ? 'text-emerald-700'
                          : 'text-red-700'
                    }`}
                  >
                    {todayProfitLoss == null
                      ? '—'
                      : `${todayProfitLoss >= 0 ? '+' : ''}${formatCOP(todayProfitLoss)}`}
                  </span>
                </p>
                <p className={`inline-flex rounded border px-2 py-1 text-[11px] font-semibold ${modeTone}`}>
                  Estado: {systemStatus}
                </p>
              </div>
              <div className={`rounded-lg border p-3 ${modeCardTone}`}>
                <p className="text-xs font-semibold text-app-fg">Acción recomendada</p>
                <p className="mt-2 text-sm font-semibold text-app-fg">{modeLabel}</p>
                <p className="mt-2 text-xs text-app-muted">
                  Motivo: ROI100 {pct(roi100, 1)} · caída máxima 30d {dd30 ?? '—'}u
                  {twoRedDays ? ' · 2 días rojos seguidos' : ''}.
                </p>
                <p className="mt-1 text-xs text-app-muted">Acción sugerida: {recommendedAction}</p>
              </div>
            </div>
          </section>

          <section className="mb-6 rounded-xl border border-app-line bg-app-card p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-app-fg">Top Picks Preview</p>
              {barRunId != null && (
                <Link
                  to={`/runs/${barRunId}/picks`}
                  className="text-xs text-app-fg underline decoration-app-line underline-offset-2"
                >
                  View all picks
                </Link>
              )}
            </div>
            {topPicksPreview.length === 0 ? (
              <p className="text-xs text-app-muted">No hay picks recientes para mostrar en este corte.</p>
            ) : (
              <div className="overflow-hidden rounded-xl border border-app-line bg-app-card">
                {topPicksPreview.map((r, i) => (
                  <PickInboxRow
                    key={`hero-top-${r.pick_id}`}
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
                    executionSlotLabelEs={r.execution_slot_label_es ?? null}
                    confidence={confidenceFromOddsReference(r.odds_reference) ?? 'N/D'}
                    outcome={r.outcome}
                    userTaken={r.user_taken}
                    ordinal={i + 1}
                  />
                ))}
              </div>
            )}
          </section>

          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
              <p className="mt-2 border-t border-app-line pt-2 text-[10px] text-app-muted">
                Settled (ventana del día):{' '}
                <span className="font-mono text-app-fg">{s.settled_count}</span>
                {' · '}
                ROI total:{' '}
                <span
                  className={`font-mono ${
                    s.roi_unit != null
                      ? s.roi_unit >= 0
                        ? 'text-emerald-800'
                        : 'text-red-800'
                      : 'text-app-muted'
                  }`}
                >
                  {s.roi_unit != null
                    ? `${s.roi_unit >= 0 ? '+' : ''}${(s.roi_unit * 100).toFixed(2)}%`
                    : '—'}
                </span>
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
            </div>
          </div>
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('operacion')}
              className={`rounded-md border px-3 py-1.5 text-xs ${
                activeTab === 'operacion'
                  ? 'border-app-fg bg-app-card text-app-fg'
                  : 'border-app-line bg-transparent text-app-muted'
              }`}
            >
              Operación diaria
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('analitica')}
              className={`rounded-md border px-3 py-1.5 text-xs ${
                activeTab === 'analitica'
                  ? 'border-app-fg bg-app-card text-app-fg'
                  : 'border-app-line bg-transparent text-app-muted'
              }`}
            >
              Rendimiento & calibración
            </button>
            <details className="ml-auto rounded-md border border-app-line bg-app-card px-2 py-1 text-[11px] text-app-muted">
              <summary className="cursor-pointer select-none">Glosario rápido</summary>
              <div className="mt-2 space-y-1 leading-relaxed">
                <p>
                  <strong className="text-app-fg">Tasa de acierto:</strong> de cada 10 picks, cuántos salen bien.
                </p>
                <p>
                  <strong className="text-app-fg">Rendimiento:</strong> cuánto ganas o pierdes por cada 1 unidad.
                </p>
                <p>
                  <strong className="text-app-fg">Caída máxima:</strong> peor racha acumulada de pérdidas.
                </p>
              </div>
            </details>
          </div>
          {activeTab === 'operacion' && (
            <>
              <div className="mb-4 rounded-xl border border-app-line bg-app-card p-4">
                <p className="text-xs font-semibold text-app-fg">
                  Widget: picks escogidos por dia ({sport})
                </p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  {(dashQ.data?.issued_daily ?? []).slice(-4).map((d) => (
                    <div key={d.run_date} className="rounded-md border border-app-line p-2">
                      <p className="text-[10px] text-app-muted">{d.run_date}</p>
                      <p className="mt-1 text-xs text-app-fg">
                        Modelo: <span className="font-mono">{d.picks_total}</span>
                      </p>
                      <p className="text-xs text-app-muted">
                        Tradables: <span className="font-mono">{d.picks_tradable}</span>
                      </p>
                      {d.picks_taken != null && (
                        <p className="text-xs text-app-muted">
                          Tomados: <span className="font-mono">{d.picks_taken}</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
          <div className="mt-8">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Mis selecciones de hoy</h2>
              <p className="mt-0.5 text-xs text-app-muted">
                Estado de los picks que marcaste como tomados para esta fecha.
              </p>
              {userId == null ? (
                <p className="mt-4 text-xs text-app-muted">
                  Selecciona usuario para ver tus selecciones de hoy.
                </p>
              ) : (
                <>
                  {(takenTodayQ.data?.recent_total ?? 0) === 0 ? (
                    <p className="mt-4 text-xs text-app-muted">
                      Aun no tienes picks tomados hoy.
                    </p>
                  ) : (
                    <div className="mt-4 overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
                      {(takenTodayQ.data?.recent ?? []).map((r, i) => (
                        <PickInboxRow
                          key={`taken-${r.pick_id}`}
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
                          executionSlotLabelEs={r.execution_slot_label_es ?? null}
                          outcome={r.outcome}
                          userTaken={r.user_taken}
                          ordinal={i + 1}
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="mt-8">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Rendimiento del día</h2>
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
              <div className="mt-6 rounded-lg border border-app-line bg-app-bg p-3 text-xs text-app-muted">
                <p>
                  <strong className="text-app-fg">Cómo leer esto:</strong> si hoy hay más verde (ganadas) que rojo
                  (perdidas), vas bien en ejecución diaria.
                </p>
                <p className="mt-1">
                  <strong className="text-app-fg">Qué hacer:</strong> si aparecen 2 días seguidos en rojo, reduce stake
                  al 50% mañana.
                </p>
              </div>
            </div>
          </div>
          <div className="mt-8">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Aciertos vs nivel de confianza</h2>
              <p className="mt-0.5 text-xs text-app-muted">
                Universo total del modelo (tradable): compara aciertos por nivel de confianza.
              </p>
              <div className="mt-4 space-y-2">
                {(dashQ.data?.calibration?.by_confidence ?? []).map((r) => {
                  const hit = r.hit_rate ?? 0
                  const loss = Math.max(0, 1 - hit)
                  return (
                    <div key={r.bucket}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <span className="font-mono text-app-fg">{r.bucket}</span>
                        <span className="text-app-muted">
                          {r.settled} picks cerrados · aciertos {pctPlain(r.hit_rate, 1)}
                        </span>
                      </div>
                      <div className="flex h-2 overflow-hidden rounded border border-app-line">
                        <div
                          className="bg-emerald-500/80"
                          style={{ width: `${Math.max(0, Math.min(100, hit * 100))}%` }}
                        />
                        <div
                          className="bg-red-500/60"
                          style={{ width: `${Math.max(0, Math.min(100, loss * 100))}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-6 rounded-lg border border-app-line bg-app-bg p-3 text-xs text-app-muted">
                <p>
                  <strong className="text-app-fg">Lectura rápida:</strong> “Alta” debería tener mejor hit-rate que “Media”
                  y “Baja”.
                </p>
                <p className="mt-1">
                  <strong className="text-app-fg">Si no pasa:</strong> la etiqueta de confianza está mal calibrada y no
                  debes usarla para aumentar stake.
                </p>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Aciertos vs nivel de confianza (picks tomados)</h2>
              <p className="mt-0.5 text-xs text-app-muted">
                Solo picks que marcaste como tomados.
              </p>
              {userId == null ? (
                <p className="mt-4 text-xs text-app-muted">
                  Selecciona usuario para ver esta vista.
                </p>
              ) : (dashQ.data?.calibration?.by_confidence_taken?.length ?? 0) === 0 ? (
                <p className="mt-4 text-xs text-app-muted">
                  Aun no hay picks tomados cerrados para esta comparativa.
                </p>
              ) : (
                <div className="mt-4 space-y-2">
                  {(dashQ.data?.calibration?.by_confidence_taken ?? []).map((r) => {
                    const hit = r.hit_rate ?? 0
                    const loss = Math.max(0, 1 - hit)
                    return (
                      <div key={`taken-${r.bucket}`}>
                        <div className="mb-1 flex items-center justify-between text-[11px]">
                          <span className="font-mono text-app-fg">{r.bucket}</span>
                          <span className="text-app-muted">
                            {r.settled} picks cerrados · aciertos {pctPlain(r.hit_rate, 1)}
                          </span>
                        </div>
                        <div className="flex h-2 overflow-hidden rounded border border-app-line">
                          <div
                            className="bg-emerald-500/80"
                            style={{ width: `${Math.max(0, Math.min(100, hit * 100))}%` }}
                          />
                          <div
                            className="bg-red-500/60"
                            style={{ width: `${Math.max(0, Math.min(100, loss * 100))}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
            </>
          )}

          {activeTab === 'analitica' && (
            <div className="mt-2 space-y-4">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Tendencia diaria (tradable)</h2>
              <p className="mt-0.5 text-xs text-app-muted">
                Rendimiento y tasa de acierto por dia (ultimos 14 cortes).
              </p>
              <div className="mt-4 space-y-2">
                {(dashQ.data?.calibration?.daily_trend ?? []).map((d) => {
                  const roi = d.roi_unit ?? 0
                  const w = Math.max(0, Math.min(100, Math.abs(roi) * 100))
                  return (
                    <div key={d.run_date} className="grid grid-cols-[5.5rem_1fr] items-center gap-3">
                      <div className="text-[11px] text-app-muted">{d.run_date.slice(5)}</div>
                      <div>
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 rounded border border-app-line bg-neutral-900">
                            <div
                              className={`h-full ${roi >= 0 ? 'bg-emerald-500/80' : 'bg-red-500/80'}`}
                              style={{ width: `${w}%` }}
                            />
                          </div>
                          <span className="w-20 text-right font-mono text-[11px] text-app-fg">
                            {pct(d.roi_unit, 1)}
                          </span>
                        </div>
                        <p className="mt-0.5 text-[10px] text-app-muted">
                          aciertos {pctPlain(d.hit_rate, 1)} · picks cerrados {d.settled}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-6 rounded-lg border border-app-line bg-app-bg p-3 text-xs text-app-muted">
                <p>
                  <strong className="text-app-fg">Qué significa:</strong> cada fila es un día. Verde = día rentable,
                  rojo = día malo.
                </p>
                <p className="mt-1">
                  <strong className="text-app-fg">Regla simple:</strong> {twoRedDays
                    ? 'hay 2 días rojos seguidos: modo defensivo recomendado.'
                    : 'si encadenas 2 rojos seguidos, entra en modo defensivo.'}
                </p>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Histórico rolling ({sport})</h2>
              <div className="mt-4 space-y-3">
                {selectedSportRolling ? (
                  <div className="rounded-lg border border-app-line p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-app-muted">
                      {selectedSportRolling.sport}
                    </p>
                    <p className="mt-1 text-xs text-app-muted">
                      Settled tradable: {selectedSportRolling.settled_tradable} / total: {selectedSportRolling.settled_total}
                    </p>
                    <p className="mt-2 text-xs text-app-muted">
                      ROI50:{' '}
                      <span className="font-mono text-app-fg">
                        {pct(selectedSportRolling.roi_tradable_50, 2)}
                      </span>
                      {' · '}ROI100:{' '}
                      <span className="font-mono text-app-fg">
                        {pct(selectedSportRolling.roi_tradable_100, 2)}
                      </span>
                    </p>
                    <div className="mt-2 flex h-2 overflow-hidden rounded border border-app-line">
                      <div
                        className="bg-emerald-500/80"
                        style={{
                          width: `${Math.max(
                            0,
                            Math.min(100, (selectedSportRolling.hit_rate_tradable_100 ?? 0) * 100)
                          )}%`,
                        }}
                      />
                      <div
                        className="bg-red-500/60"
                        style={{
                          width: `${Math.max(
                            0,
                            100 - Math.min(100, (selectedSportRolling.hit_rate_tradable_100 ?? 0) * 100)
                          )}%`,
                        }}
                      />
                    </div>
                    <p className="mt-1 text-[10px] text-app-muted">
                      Tasa de acierto (100 picks): {pctPlain(selectedSportRolling.hit_rate_tradable_100, 1)} · Caida maxima (30d):{' '}
                      <span className="font-mono">{selectedSportRolling.drawdown_units_30d ?? '—'}u</span>
                    </p>
                    <p className="mt-2 text-[11px] text-app-muted">
                      Interpretación: {roi100 != null && roi100 > 0 ? 'tendencia positiva' : 'tendencia frágil o negativa'}
                      {' · '}
                      riesgo: {dd30 != null && dd30 <= 6 ? 'controlado' : 'alto'}.
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-app-muted">Sin histórico suficiente para este deporte.</p>
                )}
              </div>
            </div>
            <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="text-sm font-semibold">Calibración del modelo ({sport})</h2>
              <p className="mt-0.5 text-xs text-app-muted">
                Solo picks tradables por cuota minima.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-[11px] font-semibold text-app-muted">Confianza</p>
                  <div className={`mt-2 inline-flex rounded border px-2 py-1 text-[10px] font-semibold ${calibrationTone}`}>
                    {calibrationLabel}
                  </div>
                  <div className="mt-2 space-y-1">
                    {(dashQ.data?.calibration?.by_confidence ?? []).map((r) => (
                      <p key={r.bucket} className="text-xs text-app-fg">
                        <span className="font-mono">{r.bucket}</span> · {r.settled} picks · rendimiento{' '}
                        <span className="font-mono">
                          {pct(r.roi_unit, 1)}
                        </span>
                        {r.settled < minBucketSample && (
                          <span className="ml-2 text-[10px] text-amber-700">(muestra chica)</span>
                        )}
                      </p>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-app-muted">Edge</p>
                  <div className="mt-2 space-y-1">
                    {(dashQ.data?.calibration?.by_edge ?? []).map((r) => (
                      <p key={r.bucket} className="text-xs text-app-fg">
                        <span className="font-mono">{r.bucket}</span> · {r.settled} picks · rendimiento{' '}
                        <span className="font-mono">
                          {pct(r.roi_unit, 1)}
                        </span>
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>
          )}

          {activeTab === 'operacion' && (
            <div className="mt-10">
            <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-sm font-semibold">Tablero operativo</h2>
                <p className="text-xs text-app-muted">
                  Gestión detallada de picks, cierres y ejecución.
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
          </div>
          )}
        </>
      )}
    </div>
  )
}
