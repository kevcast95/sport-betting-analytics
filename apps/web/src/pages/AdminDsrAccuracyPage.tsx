import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  Legend,
} from 'recharts'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import { fetchBt2AdminBacktestReplay, postBt2AdminRefreshCdmSmForBacktestWindow } from '@/lib/api'
import type { Bt2AdminBacktestReplayOut } from '@/lib/bt2Types'

/**
 * Dependencia sugerida: npm i recharts (gráficas).
 */

const STORAGE_UI_KEY = 'bt2.admin.backtestReplay.ui.v1'
const STORAGE_CACHE_PREFIX = 'bt2.admin.backtestReplay.cache.v1:'

function cacheStorageKey(from: string, to: string): string {
  return `${STORAGE_CACHE_PREFIX}${from}|${to}`
}

type ReplayPreset = 'today' | '7d' | '30d' | 'range'
type ReplayOutcome = 'si' | 'no' | 'pendiente' | 'void' | 'ne'
type TierFilter = 'all' | 'free' | 'premium' | 'blocked'
type OutcomeFilter = 'all' | ReplayOutcome

type PersistedReplayUi = {
  preset?: ReplayPreset
  rangeFrom?: string
  rangeTo?: string
  marketFilter?: string
  tierFilter?: string
  outcomeFilter?: string
  leagueFilter?: string
  search?: string
  page?: number
  smRefreshOnlyPendingCdm?: boolean
}

function readPersistedUi(): PersistedReplayUi {
  if (typeof window === 'undefined') return {}
  try {
    const raw = localStorage.getItem(STORAGE_UI_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as PersistedReplayUi
  } catch {
    return {}
  }
}

function readCachedReplay(from: string, to: string): Bt2AdminBacktestReplayOut | undefined {
  if (typeof window === 'undefined') return undefined
  try {
    const raw = localStorage.getItem(cacheStorageKey(from, to))
    if (!raw) return undefined
    return JSON.parse(raw) as Bt2AdminBacktestReplayOut
  } catch {
    return undefined
  }
}

const PAGE_SIZE = 12

function todayIsoBogota(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function addDaysIso(isoDay: string, delta: number): string {
  const [y, m, d] = isoDay.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() + delta)
  const yy = dt.getUTCFullYear()
  const mm = String(dt.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(dt.getUTCDate()).padStart(2, '0')
  return `${yy}-${mm}-${dd}`
}

function operatingRangeForPreset(
  preset: ReplayPreset,
  rangeFrom: string,
  rangeTo: string,
): { from: string; to: string } {
  const t = todayIsoBogota()
  switch (preset) {
    case 'today':
      return { from: t, to: t }
    case '7d':
      return { from: addDaysIso(t, -6), to: t }
    case '30d':
      return { from: addDaysIso(t, -29), to: t }
    case 'range':
      return { from: rangeFrom, to: rangeTo }
    default:
      return { from: t, to: t }
  }
}

function outcomeLabel(o: ReplayOutcome): string {
  switch (o) {
    case 'si':
      return 'Acierto'
    case 'no':
      return 'Fallo'
    case 'pendiente':
      return 'Pendiente'
    case 'void':
      return 'Void'
    case 'ne':
      return 'N.E.'
    default:
      return '—'
  }
}

function outcomeClass(o: ReplayOutcome): string {
  switch (o) {
    case 'si':
      return 'border-[#8B5CF6]/35 bg-[#f5f3ff] text-[#6d28d9]'
    case 'no':
      return 'border-[#ea580c]/25 bg-[#fff7ed] text-[#c2410c]'
    case 'pendiente':
      return 'border-[#a4b4be]/40 bg-white text-[#52616a]'
    case 'void':
      return 'border-[#a4b4be]/35 bg-[#f8fafc] text-[#64748b]'
    case 'ne':
      return 'border-[#a4b4be]/35 bg-[#f1f5f9] text-[#64748b]'
    default:
      return 'border-[#a4b4be]/35 bg-[#f8fafc] text-[#64748b]'
  }
}

function actionTierLabel(v: string): string {
  switch (v) {
    case 'free':
      return 'Libre'
    case 'premium':
      return 'Premium'
    case 'blocked':
      return 'Bloqueado'
    default:
      return v || '—'
  }
}

function actionTierClass(v: string): string {
  switch (v) {
    case 'premium':
      return 'border-[#8B5CF6]/35 bg-[#f5f3ff] text-[#6d28d9]'
    case 'free':
      return 'border-[#a4b4be]/35 bg-white text-[#26343d]'
    case 'blocked':
      return 'border-[#a4b4be]/35 bg-[#f1f5f9] text-[#64748b]'
    default:
      return 'border-[#a4b4be]/35 bg-[#f8fafc] text-[#64748b]'
  }
}

function metricCopy(value: number | null | undefined, suffix = ''): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value}${suffix}`
}

function MetricCard(props: { title: string; value: string; subtitle?: string; accent?: boolean }) {
  return (
    <section className="rounded-2xl border border-[#E2E8F0] bg-white px-5 py-4">
      <p className={[
        'text-[10px] font-bold uppercase tracking-[0.22em]',
        props.accent ? 'text-[#8B5CF6]' : 'text-[#52616a]',
      ].join(' ')}>
        {props.title}
      </p>
      <div className="mt-3 flex items-end gap-2">
        <p className="font-['Geist_Mono',monospace] text-[42px] leading-none text-[#26343d]">{props.value}</p>
      </div>
      {props.subtitle ? <p className="mt-2 text-sm text-[#52616a]">{props.subtitle}</p> : null}
    </section>
  )
}

function ChartCard(props: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-[#E2E8F0] bg-white px-5 py-4">
      <div className="mb-4">
        <h3 className="text-sm font-semibold tracking-[0.02em] text-[#26343d]">{props.title}</h3>
        {props.subtitle ? <p className="mt-1 text-xs text-[#52616a]">{props.subtitle}</p> : null}
      </div>
      <div className="h-[260px] w-full">{props.children}</div>
    </section>
  )
}

const PRESETS: ReplayPreset[] = ['today', '7d', '30d', 'range']

export default function BacktestReplayPage() {
  const t0 = todayIsoBogota()
  const persisted = readPersistedUi()
  const initialPreset = PRESETS.includes(persisted.preset as ReplayPreset)
    ? (persisted.preset as ReplayPreset)
    : '7d'

  const [preset, setPreset] = useState<ReplayPreset>(initialPreset)
  const [rangeFrom, setRangeFrom] = useState(() => persisted.rangeFrom ?? addDaysIso(t0, -6))
  const [rangeTo, setRangeTo] = useState(() => persisted.rangeTo ?? t0)
  const [marketFilter, setMarketFilter] = useState(() => persisted.marketFilter ?? 'all')
  const [tierFilter, setTierFilter] = useState<TierFilter>(() => {
    const x = persisted.tierFilter
    return x === 'free' || x === 'premium' || x === 'blocked' ? x : 'all'
  })
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>(() => {
    const x = persisted.outcomeFilter
    const ok: OutcomeFilter[] = ['all', 'si', 'no', 'pendiente', 'void', 'ne']
    return ok.includes(x as OutcomeFilter) ? (x as OutcomeFilter) : 'all'
  })
  const [leagueFilter, setLeagueFilter] = useState(() => persisted.leagueFilter ?? 'all')
  const [search, setSearch] = useState(() => persisted.search ?? '')
  const [page, setPage] = useState(() =>
    typeof persisted.page === 'number' && persisted.page >= 1 ? persisted.page : 1,
  )
  /** POST SM → CDM: solo eventos sin marcador completo en bt2_events (ahorra cuota). */
  const [smRefreshOnlyPendingCdm, setSmRefreshOnlyPendingCdm] = useState(
    () => persisted.smRefreshOnlyPendingCdm !== false,
  )

  const rangeKeys = useMemo(
    () => operatingRangeForPreset(preset, rangeFrom, rangeTo),
    [preset, rangeFrom, rangeTo],
  )

  const cachedReplayInitial = useMemo(
    () => readCachedReplay(rangeKeys.from, rangeKeys.to),
    [rangeKeys.from, rangeKeys.to],
  )

  const {
    data,
    isFetching,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ['bt2-admin-backtest-replay', rangeKeys.from, rangeKeys.to],
    queryFn: () => fetchBt2AdminBacktestReplay(rangeKeys.from, rangeKeys.to),
    staleTime: Infinity,
    gcTime: 1000 * 60 * 60 * 24 * 7,
    enabled: false,
    initialData: cachedReplayInitial,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  useEffect(() => {
    if (!data) return
    try {
      localStorage.setItem(cacheStorageKey(rangeKeys.from, rangeKeys.to), JSON.stringify(data))
    } catch (e) {
      console.warn('[BT2] No se pudo persistir backtest-replay en localStorage:', e)
    }
  }, [data, rangeKeys.from, rangeKeys.to])

  useEffect(() => {
    try {
      const payload: PersistedReplayUi = {
        preset,
        rangeFrom,
        rangeTo,
        marketFilter,
        tierFilter,
        outcomeFilter,
        leagueFilter,
        search,
        page,
        smRefreshOnlyPendingCdm,
      }
      localStorage.setItem(STORAGE_UI_KEY, JSON.stringify(payload))
    } catch {
      /* noop */
    }
  }, [
    preset,
    rangeFrom,
    rangeTo,
    marketFilter,
    tierFilter,
    outcomeFilter,
    leagueFilter,
    search,
    page,
    smRefreshOnlyPendingCdm,
  ])

  const smRefreshMutation = useMutation({
    mutationFn: () =>
      postBt2AdminRefreshCdmSmForBacktestWindow(rangeKeys.from, rangeKeys.to, {
        onlyPendingCdm: smRefreshOnlyPendingCdm ? undefined : false,
      }),
  })

  const error =
    queryError instanceof Error
      ? queryError.message.length > 260
        ? `${queryError.message.slice(0, 260)}…`
        : queryError.message
      : queryError
        ? String(queryError).length > 260
          ? `${String(queryError).slice(0, 260)}…`
          : String(queryError)
        : null

  useEffect(() => {
    smRefreshMutation.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset al cambiar ventana solamente
  }, [rangeKeys.from, rangeKeys.to])

  useEffect(() => {
    setPage(1)
  }, [
    preset,
    rangeFrom,
    rangeTo,
    marketFilter,
    tierFilter,
    outcomeFilter,
    leagueFilter,
    search,
  ])

  const summary = data?.summary

  const leagues = useMemo(() => {
    const set = new Set<string>()
    for (const row of data?.rows ?? []) {
      if (row.leagueLabel) set.add(row.leagueLabel)
    }
    return ['all', ...Array.from(set).sort((a, b) => a.localeCompare(b))]
  }, [data?.rows])

  const markets = useMemo(() => {
    const set = new Set<string>()
    for (const row of data?.rows ?? []) set.add(row.marketLabelEs)
    return ['all', ...Array.from(set).sort((a, b) => a.localeCompare(b))]
  }, [data?.rows])

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (data?.rows ?? []).filter((row) => {
      if (marketFilter !== 'all' && row.marketLabelEs !== marketFilter) return false
      if (tierFilter !== 'all' && row.actionTier !== tierFilter) return false
      if (outcomeFilter !== 'all' && (row.outcome as ReplayOutcome) !== outcomeFilter)
        return false
      if (leagueFilter !== 'all' && (row.leagueLabel ?? '—') !== leagueFilter) return false
      if (!q) return true
      const haystack = [row.eventLabel, row.marketLabelEs, row.selectionSummaryEs, row.leagueLabel ?? '']
        .join(' ')
        .toLowerCase()
      return haystack.includes(q)
    })
  }, [data?.rows, leagueFilter, marketFilter, outcomeFilter, search, tierFilter])

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pagedRows = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return filteredRows.slice(start, start + PAGE_SIZE)
  }, [currentPage, filteredRows])

  const chartDaily = useMemo(
    () =>
      (data?.daily ?? []).map((d) => ({
        day: d.operatingDayKey.slice(5),
        operatingDayKey: d.operatingDayKey,
        hitRate: d.hitRatePct ?? 0,
        aciertos: d.hits,
        fallos: d.misses,
        pendientes: d.pending,
        candidatos: d.candidateEvents,
        elegibles: d.eligibleEvents,
        utilesInput: d.usefulInputEvents,
        scored: d.scoredPicks,
        picks: d.totalPicks,
      })),
    [data?.daily],
  )

  const chartMarket = useMemo(
    () =>
      (data?.distribution.byMarket ?? []).map((r) => ({
        label: r.market ?? '—',
        picks: r.picks,
        aciertos: r.hits,
        fallos: r.misses,
      })),
    [data?.distribution.byMarket],
  )

  const chartTier = useMemo(
    () =>
      (data?.distribution.byActionTier ?? []).map((r) => ({
        label: actionTierLabel(r.actionTier ?? '—'),
        picks: r.picks,
        aciertos: r.hits,
        fallos: r.misses,
      })),
    [data?.distribution.byActionTier],
  )

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#26343d]">
      <div className="mx-auto max-w-[1400px] px-4 py-6 md:px-6 md:py-8">
        <BunkerViewHeader
          title="Backtest / Replay"
          subtitle="Replay DSR sobre Postgres (cuotas al corte por día). CDM desde SportMonks es un paso aparte — no mezcla con el cálculo del replay."
          rightActions={
            <div className="flex flex-wrap items-center justify-end gap-2">
              <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-[10px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                <input
                  type="checkbox"
                  checked={smRefreshOnlyPendingCdm}
                  onChange={(e) => setSmRefreshOnlyPendingCdm(e.target.checked)}
                  className="rounded border-[#a4b4be]/50 text-[#8B5CF6] focus:ring-[#8B5CF6]/40"
                />
                SM solo sin marcador
              </label>
              <button
                type="button"
                onClick={() => void smRefreshMutation.mutateAsync()}
                disabled={smRefreshMutation.isPending || isFetching}
                className="rounded-xl border border-[#0f766e]/25 bg-white px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#0f766e] transition hover:bg-teal-50 disabled:opacity-50"
              >
                {smRefreshMutation.isPending ? 'SM…' : 'Refrescar CDM (SM)'}
              </button>
              <button
                type="button"
                onClick={() => void refetch()}
                disabled={isFetching || smRefreshMutation.isPending}
                className="rounded-xl border border-[#8B5CF6]/20 bg-white px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#8B5CF6] transition hover:bg-[#f5f3ff] disabled:opacity-50"
              >
                {isFetching ? 'Replay…' : 'Ejecutar replay'}
              </button>
            </div>
          }
        />

        <p className="mt-4 max-w-4xl text-xs leading-relaxed text-[#52616a]">
          <strong className="text-[#26343d]">Por qué ves «pendiente» aunque en admin los picks estén cerrados:</strong>{' '}
          el backtest no es la lista de picks del día: arma un <span className="font-mono text-[11px]">pool</span> de
          eventos por ventana de kickoff (y tope por día) y puntúa cada fila contra{' '}
          <span className="font-mono text-[11px]">bt2_events</span> en ese momento. La vista de picks usa evaluación
          oficial sobre filas materializadas; pueden ser conjuntos distintos. «Pendiente» aquí = para ese{' '}
          <span className="font-mono text-[11px]">event_id</span> del pool replay faltaba marcador CDM (
          <span className="font-mono text-[11px]">result_home/result_away</span>) o el estado no permitía cerrar — no
          el mismo criterio que «pick cerrado» en otra pantalla.
        </p>

        {smRefreshMutation.isError ? (
          <div
            className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900"
            role="alert"
          >
            <strong className="font-semibold">Refresco SM:</strong>{' '}
            {smRefreshMutation.error instanceof Error
              ? smRefreshMutation.error.message
              : String(smRefreshMutation.error)}
          </div>
        ) : null}

        {smRefreshMutation.isSuccess && smRefreshMutation.data?.messageEs ? (
          <div
            className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${
              smRefreshMutation.data.ok
                ? 'border-emerald-200 bg-emerald-50/95 text-emerald-950'
                : 'border-amber-200 bg-amber-50/95 text-amber-950'
            }`}
            role="status"
          >
            <strong className="font-semibold">SportMonks → CDM (pool backtest):</strong>{' '}
            {smRefreshMutation.data.messageEs}
            <span className="mt-1 block font-mono text-[11px] opacity-90">
              Pool: {smRefreshMutation.data.replayPoolEventCount} · pendiente CDM:{' '}
              {smRefreshMutation.data.pendingCdmEventCount} · SM OK: {smRefreshMutation.data.smFetchOk} · CDM OK:{' '}
              {smRefreshMutation.data.cdmNormalizedOk}
            </span>
          </div>
        ) : null}

        <section className="mt-5 rounded-2xl border border-[#E2E8F0] bg-white px-4 py-3 md:px-5">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#52616a]">Rango de análisis</p>
              <p className="mt-1 text-sm text-[#52616a]">
                Replay honesto sobre Postgres · TZ {data?.timezoneLabel ?? 'America/Bogota'}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-1.5">
              {([
                ['today', 'Hoy'],
                ['7d', '7D'],
                ['30d', '30D'],
                ['range', 'Rango'],
              ] as const).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setPreset(key)}
                  className={[
                    'rounded-xl px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] transition-colors',
                    preset === key ? 'bg-white text-[#8B5CF6] shadow-sm' : 'text-[#52616a] hover:text-[#26343d]',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {preset === 'range' ? (
            <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-[#52616a]">
              <label className="flex items-center gap-2">
                <span>Desde</span>
                <input
                  type="date"
                  value={rangeFrom}
                  onChange={(e) => setRangeFrom(e.target.value)}
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 font-['Geist_Mono',monospace] text-xs text-[#26343d]"
                />
              </label>
              <label className="flex items-center gap-2">
                <span>Hasta</span>
                <input
                  type="date"
                  value={rangeTo}
                  onChange={(e) => setRangeTo(e.target.value)}
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 font-['Geist_Mono',monospace] text-xs text-[#26343d]"
                />
              </label>
            </div>
          ) : null}

          <p className="mt-4 text-xs text-[#52616a]">
            Rango API: <span className="font-['Geist_Mono',monospace]">{rangeKeys.from}</span> …{' '}
            <span className="font-['Geist_Mono',monospace]">{rangeKeys.to}</span>
            {data?.summaryHumanEs ? <span> · {data.summaryHumanEs}</span> : null}
          </p>
        </section>

        {error ? (
          <div className="mt-5 rounded-2xl border border-[#fca5a5] bg-[#fef2f2] px-4 py-3 text-sm text-[#991b1b]">
            {error}
          </div>
        ) : null}

        {!error && !data && !isFetching ? (
          <div
            className="mt-5 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] px-4 py-3 text-sm text-[#52616a]"
            role="status"
          >
            <strong className="font-semibold text-[#26343d]">Replay no ejecutado en esta sesión.</strong>{' '}
            Si ya guardaste un resultado antes, elegí el mismo rango para verlo desde el navegador; si no, pulsá{' '}
            <span className="font-semibold text-[#6d28d9]">Ejecutar replay</span> cuando quieras llamar al API (no se
            lanza al abrir la página).
          </div>
        ) : null}

        <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <MetricCard
            title="Hit rate"
            accent
            value={summary?.hitRatePct != null ? `${summary.hitRatePct.toFixed(1)}%` : '—'}
            subtitle={`${metricCopy(summary?.hits)} aciertos · ${metricCopy(summary?.misses)} fallos`}
          />
          <MetricCard
            title="Picks generados"
            value={metricCopy(summary?.totalPicks)}
            subtitle={`${metricCopy(summary?.evaluatedScored)} scored · ${metricCopy(summary?.pending)} pendientes`}
          />
          <MetricCard
            title="Cobertura útil"
            value={
              summary
                ? `${summary.usefulInputEvents}/${summary.eligibleEvents} (${summary.candidateEvents} cand.)`
                : '—'
            }
            subtitle="Input ≥ umbral / elegibles pool valor / candidatos calendario"
          />
        </section>

        <section className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <MetricCard
            title="Evaluados (A / F)"
            value={summary ? `${summary.hits}/${summary.misses}` : '—'}
            subtitle="Denominador excluye pendientes, void y N.E."
          />
          <MetricCard
            title="Pendientes / Void / N.E."
            value={summary ? `${summary.pending}/${summary.voidCount}/${summary.noEvaluable}` : '—'}
            subtitle="Filas no usadas en el hit rate"
          />
          <MetricCard
            title="Días con datos"
            value={metricCopy(summary?.generatedDays)}
            subtitle="Días con al menos un pick emitido por el replay"
          />
        </section>

        <section className="mt-6 grid gap-4 xl:grid-cols-2">
          <ChartCard title="Hit rate por día" subtitle="Tendencia diaria del desempeño scored.">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartDaily} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fill: '#52616a', fontSize: 12 }} />
                <YAxis tick={{ fill: '#52616a', fontSize: 12 }} width={42} />
                <Tooltip />
                <Line type="monotone" dataKey="hitRate" stroke="#8B5CF6" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Aciertos vs fallos por día" subtitle="Volumen diario scored.">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartDaily} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fill: '#52616a', fontSize: 12 }} />
                <YAxis tick={{ fill: '#52616a', fontSize: 12 }} width={42} />
                <Tooltip />
                <Legend />
                <Bar dataKey="aciertos" stackId="a" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="fallos" stackId="a" fill="#F97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </section>
        <section className="mt-4 grid gap-4 xl:grid-cols-1">
          <ChartCard
            title="Cobertura del input por día"
            subtitle="Candidatos → elegibles → input útil → picks → scored (hit+miss)."
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartDaily} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fill: '#52616a', fontSize: 12 }} />
                <YAxis tick={{ fill: '#52616a', fontSize: 12 }} width={42} />
                <Tooltip />
                <Legend />
                <Bar dataKey="candidatos" fill="#CBD5E1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="elegibles" fill="#94A3B8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="utilesInput" fill="#64748B" radius={[4, 4, 0, 0]} />
                <Bar dataKey="picks" fill="#60A5FA" radius={[4, 4, 0, 0]} />
                <Bar dataKey="scored" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-2">

          <ChartCard title="Distribución por mercado" subtitle="Qué mercados explican el volumen y el resultado.">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartMarket} layout="vertical" margin={{ top: 8, right: 8, left: 24, bottom: 0 }}>
                <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: '#52616a', fontSize: 12 }} />
                <YAxis dataKey="label" type="category" tick={{ fill: '#52616a', fontSize: 11 }} width={96} />
                <Tooltip />
                <Legend />
                <Bar dataKey="aciertos" stackId="a" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="fallos" stackId="a" fill="#F97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Distribución por acceso" subtitle="Comparación entre picks libres y premium.">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartTier} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fill: '#52616a', fontSize: 12 }} />
                <YAxis tick={{ fill: '#52616a', fontSize: 12 }} width={42} />
                <Tooltip />
                <Legend />
                <Bar dataKey="aciertos" stackId="a" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="fallos" stackId="a" fill="#F97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </section>

        <section className="mt-6 rounded-2xl border border-[#E2E8F0] bg-white px-4 py-4 md:px-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-[#26343d]">Detalle del replay</h2>
              <p className="mt-1 text-sm text-[#52616a]">
                Tabla paginada con filtros: cada fila es un pick emitido por el replay (DSR + post‑proceso)
                frente al mismo CDM histórico usado para liquidar.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <label className="flex flex-col gap-1 text-xs text-[#52616a]">
                <span>Mercado</span>
                <select
                  value={marketFilter}
                  onChange={(e) => setMarketFilter(e.target.value)}
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#26343d]"
                >
                  {markets.map((m) => (
                    <option key={m} value={m}>
                      {m === 'all' ? 'Todos' : m}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1 text-xs text-[#52616a]">
                <span>Acceso</span>
                <select
                  value={tierFilter}
                  onChange={(e) => setTierFilter(e.target.value as TierFilter)}
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#26343d]"
                >
                  <option value="all">Todos</option>
                  <option value="free">Libre</option>
                  <option value="premium">Premium</option>
                  <option value="blocked">Bloqueado</option>
                </select>
              </label>

              <label className="flex flex-col gap-1 text-xs text-[#52616a]">
                <span>Resultado</span>
                <select
                  value={outcomeFilter}
                  onChange={(e) => setOutcomeFilter(e.target.value as OutcomeFilter)}
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#26343d]"
                >
                  <option value="all">Todos</option>
                  <option value="si">Acierto</option>
                  <option value="no">Fallo</option>
                  <option value="pendiente">Pendiente</option>
                  <option value="void">Void</option>
                  <option value="ne">N.E.</option>
                </select>
              </label>

              <label className="flex flex-col gap-1 text-xs text-[#52616a]">
                <span>Liga</span>
                <select
                  value={leagueFilter}
                  onChange={(e) => setLeagueFilter(e.target.value)}
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#26343d]"
                >
                  {leagues.map((league) => (
                    <option key={league} value={league}>
                      {league === 'all' ? 'Todas' : league}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1 text-xs text-[#52616a]">
                <span>Buscar</span>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Evento o selección"
                  className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#26343d]"
                />
              </label>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0">
              <thead>
                <tr className="text-left text-[11px] font-bold uppercase tracking-[0.18em] text-[#52616a]">
                  <th className="border-b border-[#E2E8F0] px-3 py-3">Fecha real</th>
                  <th className="border-b border-[#E2E8F0] px-3 py-3">Evento</th>
                  <th className="border-b border-[#E2E8F0] px-3 py-3">Mercado</th>
                  <th className="border-b border-[#E2E8F0] px-3 py-3">Pronóstico</th>
                  <th className="border-b border-[#E2E8F0] px-3 py-3">Acceso</th>
                  <th className="border-b border-[#E2E8F0] px-3 py-3">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {isFetching ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-10 text-center text-sm text-[#52616a]">
                      Cargando replay…
                    </td>
                  </tr>
                ) : pagedRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-10 text-center text-sm text-[#52616a]">
                      No hay filas con los filtros actuales.
                    </td>
                  </tr>
                ) : (
                  pagedRows.map((row) => (
                    <tr key={`${row.operatingDayKey}-${row.eventId}`} className="text-sm text-[#26343d]">
                      <td className="border-b border-[#E2E8F0] px-3 py-3 font-['Geist_Mono',monospace] text-xs">
                        <div>{row.realKickoffDayKey}</div>
                        {row.operatingDayKey !== row.realKickoffDayKey ? (
                          <div className="mt-0.5 text-[10px] text-[#94a3b8]">
                            Bucket {row.operatingDayKey}
                          </div>
                        ) : null}
                      </td>
                      <td className="border-b border-[#E2E8F0] px-3 py-3">
                        <div className="font-medium text-[#26343d]">{row.eventLabel}</div>
                        <div className="mt-0.5 text-xs text-[#52616a]">{row.leagueLabel ?? '—'}</div>
                      </td>
                      <td className="border-b border-[#E2E8F0] px-3 py-3">{row.marketLabelEs}</td>
                      <td className="border-b border-[#E2E8F0] px-3 py-3">{row.selectionSummaryEs}</td>
                      <td className="border-b border-[#E2E8F0] px-3 py-3">
                        <span className={[
                          'inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold',
                          actionTierClass(row.actionTier),
                        ].join(' ')}>
                          {actionTierLabel(row.actionTier)}
                        </span>
                      </td>
                      <td className="border-b border-[#E2E8F0] px-3 py-3">
                        <div className="flex flex-col gap-1">
                          <span className={[
                            'inline-flex w-fit rounded-full border px-2.5 py-1 text-[11px] font-semibold',
                            outcomeClass(row.outcome as ReplayOutcome),
                          ].join(' ')}>
                            {outcomeLabel(row.outcome as ReplayOutcome)}
                          </span>
                          {row.scoreText ? <span className="text-xs text-[#52616a]">{row.scoreText}</span> : null}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-col gap-3 border-t border-[#E2E8F0] pt-4 text-sm text-[#52616a] md:flex-row md:items-center md:justify-between">
            <p>
              Mostrando <span className="font-['Geist_Mono',monospace] text-[#26343d]">{pagedRows.length}</span> de{' '}
              <span className="font-['Geist_Mono',monospace] text-[#26343d]">{filteredRows.length}</span> filas filtradas.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#26343d] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Anterior
              </button>
              <span className="font-['Geist_Mono',monospace] text-xs text-[#26343d]">
                {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#26343d] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Siguiente
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
