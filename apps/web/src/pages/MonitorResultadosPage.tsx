import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchBt2AdminMonitorResultados } from '@/lib/api'
import type { Bt2AdminMonitorResultadosOut, Bt2MonitorOutcome } from '@/lib/bt2Types'
import { useUserStore } from '@/store/useUserStore'

/** Periodo de consulta (UI). */
type MonitorPeriodPreset = 'today' | '7d' | '30d' | 'range'

const MONITOR_PAGE_SIZE = 25

type MonitorOutcomeFilter = 'all' | 'si' | 'no' | 'pendiente' | 'void' | 'ne'

type OutcomeBadge = Bt2MonitorOutcome

type TableRow = {
  dailyPickId: number
  dayKey: string
  eventLabel: string
  marketLabel: string
  selectionLabel: string
  scoreText: string
  outcome: OutcomeBadge
  decimalOdds: number | null
  flatStakeReturnUnits: number | null
}

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
  preset: MonitorPeriodPreset,
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

function outcomeLabel(o: OutcomeBadge): string {
  switch (o) {
    case 'si':
      return 'Sí'
    case 'no':
      return 'No'
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

function outcomeClass(o: OutcomeBadge): string {
  switch (o) {
    case 'si':
      return 'border-[#8B5CF6]/35 bg-[#eef4fa] text-[#6d3bd7]'
    case 'no':
      return 'border-[#ea580c]/30 bg-[#fff7ed] text-[#c2410c]'
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

function DefinitionsPanel(props: { open: boolean; onClose: () => void }) {
  if (!props.open) return null
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-[#26343d]/40 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="monitor-def-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-[#a4b4be]/25 bg-white p-6 text-sm text-[#52616a] shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="monitor-def-title" className="font-serif text-xl font-semibold text-[#26343d]">
            Definiciones
          </h2>
          <button
            type="button"
            onClick={props.onClose}
            className="rounded-lg border border-[#a4b4be]/35 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-[#52616a] hover:bg-[#eef4fa]"
          >
            Cerrar
          </button>
        </div>
        <ul className="list-inside list-disc space-y-2">
          <li>
            <strong className="text-[#26343d]">Tasa del sistema:</strong> aciertos ÷ (aciertos +
            fallos) solo sobre picks con resultado scored; pendientes, void y no evaluable no
            entran en el porcentaje.
          </li>
          <li>
            <strong className="text-[#26343d]">Tu tasa:</strong> misma fórmula (aciertos ÷ aciertos +
            fallos), sólo entre tus picks operados con veredicto oficial ya emitido; los pendientes
            no bajan el % hasta que pasen a Sí/No.
          </li>
          <li>
            <strong className="text-[#26343d]">N.E.:</strong> no evaluable (mercado o reglas fuera
            del alcance de evaluación v1).
          </li>
          <li>
            Fuente: filas de bóveda <span className="font-mono text-[#6d3bd7]">bt2_daily_picks</span>{' '}
            + <span className="font-mono text-[#6d3bd7]">bt2_pick_official_evaluation</span>.
          </li>
          <li>
            <strong className="text-[#26343d]">No es el calendario deportivo global:</strong> solo
            aparecen picks que la bóveda ya materializó para ese{' '}
            <span className="font-mono">operating_day_key</span>. Partidos jugados “hoy” sin pick en
            bóveda no cuentan aquí.
          </li>
          <li>
            Con <strong className="text-[#26343d]">Sync SportMonks</strong> activo,{' '}
            <strong className="text-[#26343d]">Actualizar + SM</strong> refresca marcadores (SM → CDM),
            evalúa pendientes y re-intenta filas marcadas N.E. por soporte antiguo del resolver (misma
            corrida en servidor actualizado).
          </li>
          <li>
            <strong className="text-[#26343d]">ROI plano:</strong> una unidad por pick; cuota ={' '}
            <span className="font-mono">reference_decimal_odds</span> si existe, si no mediana del
            consenso CDM del evento (monitor usa umbral inclusivo para no perder piernas válidas).
            Acierto: +(O−1); fallo: −1; pendientes / void / N.E. no entran.
          </li>
        </ul>
      </div>
    </div>
  )
}

function formatAdminMonitorError(msg: string): string {
  if (msg.includes('Falta VITE_BT2_ADMIN_API_KEY')) {
    return 'Configura VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).'
  }
  if (msg.startsWith('503') || msg.includes('503')) {
    return 'Admin no disponible: define BT2_ADMIN_API_KEY en el entorno del API.'
  }
  if (msg.startsWith('401') || msg.includes('401')) {
    return 'Clave admin rechazada; revisa VITE_BT2_ADMIN_API_KEY.'
  }
  return msg.length > 260 ? `${msg.slice(0, 260)}…` : msg
}

export default function MonitorResultadosPage() {
  const userId = useUserStore((s) => s.userId)
  const [preset, setPreset] = useState<MonitorPeriodPreset>('7d')
  const t0 = todayIsoBogota()
  const [rangeFrom, setRangeFrom] = useState(() => addDaysIso(t0, -6))
  const [rangeTo, setRangeTo] = useState(t0)
  const [tableFilter, setTableFilter] = useState<'all' | 'mine'>('all')
  const [onlyScored, setOnlyScored] = useState(false)
  const [defsOpen, setDefsOpen] = useState(false)
  const [data, setData] = useState<Bt2AdminMonitorResultadosOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  /** Trae marcadores desde SportMonks, actualiza CDM y re-evalúa pendientes (más lento, cuota API). */
  const [syncFromSportmonks, setSyncFromSportmonks] = useState(false)
  const [monitorPage, setMonitorPage] = useState(1)
  const [outcomeFilter, setOutcomeFilter] = useState<MonitorOutcomeFilter>('all')
  const [marketFilter, setMarketFilter] = useState('')
  const [tableSearch, setTableSearch] = useState('')

  const rangeKeys = useMemo(
    () => operatingRangeForPreset(preset, rangeFrom, rangeTo),
    [preset, rangeFrom, rangeTo],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const offset = (monitorPage - 1) * MONITOR_PAGE_SIZE
      const out = await fetchBt2AdminMonitorResultados(rangeKeys.from, rangeKeys.to, {
        monitorUserId: userId ?? undefined,
        syncFromSportmonks,
        rowsOffset: offset,
        rowsLimit: MONITOR_PAGE_SIZE,
        outcomeFilter: outcomeFilter === 'all' ? undefined : outcomeFilter,
        marketSubstring: marketFilter.trim() || undefined,
        search: tableSearch.trim() || undefined,
      })
      setData(out)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setData(null)
      setError(formatAdminMonitorError(msg))
    } finally {
      setLoading(false)
    }
  }, [
    rangeKeys.from,
    rangeKeys.to,
    userId,
    syncFromSportmonks,
    monitorPage,
    outcomeFilter,
    marketFilter,
    tableSearch,
  ])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    setMonitorPage(1)
  }, [
    preset,
    rangeFrom,
    rangeTo,
    outcomeFilter,
    marketFilter,
    tableSearch,
    syncFromSportmonks,
  ])

  const sys = data?.system
  const sysRoi = sys?.roiFlatStake
  const yrs = data?.yours
  const yrsRoi = yrs?.roiFlatStake
  const today = data?.today
  const tasaPct = sys?.hitRatePct ?? null

  const tusShowEmpty = yrs != null && yrs.totalPicks === 0
  const yoursHasPending = yrs != null && yrs.pending > 0

  const apiRowsToTable = (rows: Bt2AdminMonitorResultadosOut['rows']): TableRow[] =>
    rows.map((r) => ({
      dailyPickId: r.dailyPickId,
      dayKey: r.operatingDayKey,
      eventLabel: r.eventLabel,
      marketLabel: r.marketLabelEs,
      selectionLabel: r.selectionSummaryEs,
      scoreText: r.scoreText,
      outcome: r.outcome,
      decimalOdds: r.decimalOdds ?? null,
      flatStakeReturnUnits: r.flatStakeReturnUnits ?? null,
    }))

  const rowsTotalFromApi = data?.rowsTotal
  const monitorTotalPages =
    rowsTotalFromApi != null && rowsTotalFromApi > 0
      ? Math.max(1, Math.ceil(rowsTotalFromApi / MONITOR_PAGE_SIZE))
      : 1

  const filteredRows = useMemo(() => {
    if (!data?.rows) return []
    let src = data.rows
    if (tableFilter === 'mine' && userId) {
      src = src.filter((r) => r.userId === userId && r.iOperated)
    }
    let rows = apiRowsToTable(src)
    if (onlyScored) {
      rows = rows.filter((r) => r.outcome === 'si' || r.outcome === 'no')
    }
    return rows
  }, [data, onlyScored, tableFilter, userId])

  const handleRefresh = useCallback(() => {
    void load()
  }, [load])

  return (
    <div className="font-sans">
      <DefinitionsPanel open={defsOpen} onClose={() => setDefsOpen(false)} />

      {error ? (
        <div
          className="mb-6 rounded-xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-900"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {!loading && !error && data?.smSync?.attempted && data.smSync.messageEs ? (
        <div
          className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
            data.smSync.ok
              ? 'border-emerald-200 bg-emerald-50/95 text-emerald-950'
              : 'border-amber-200 bg-amber-50/95 text-amber-950'
          }`}
          role="status"
        >
          <strong className="font-semibold">SportMonks / CDM:</strong> {data.smSync.messageEs}
          {data.smSync.uniqueFixturesProcessed > 0 ? (
            <span className="mt-1 block font-mono text-[11px] opacity-90">
              Fixtures SM únicos: {data.smSync.uniqueFixturesProcessed}
              {data.smSync.closedPendingToFinal != null
                ? ` · pending→final: ${data.smSync.closedPendingToFinal}`
                : ''}
            </span>
          ) : null}
        </div>
      ) : null}

      {!loading && !error && preset === 'today' && data && data.system.totalPicks === 0 ? (
        <div
          className="mb-6 rounded-xl border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          <strong className="font-semibold">Sin picks para este día operativo ({rangeKeys.from}).</strong>{' '}
          El monitor solo lista filas ya guardadas en la bóveda (
          <span className="font-mono">bt2_daily_picks</span>). Si aún no corrió la generación del
          slate para hoy o no hay eventos elegibles, verás ceros aunque existan partidos terminados en
          otras fuentes. Probá <span className="font-semibold">7d</span> para ver en qué días sí hay
          datos.
        </div>
      ) : null}

      <section className="rounded-2xl border border-[#a4b4be]/15 bg-white/95 p-6 text-[#26343d] shadow-sm md:p-8">
        <div className="flex flex-col justify-between gap-6 border-b border-[#a4b4be]/15 pb-8 md:flex-row md:items-end">
          <div>
            <h1 className="font-serif text-3xl font-bold tracking-tight text-[#26343d] md:text-4xl">
              Monitor de resultados
            </h1>
            <p className="mt-2 text-sm font-medium tracking-wide text-[#52616a]">
              Picks del sistema vs picks que operaste{' '}
              <span className="mx-2 text-[#a4b4be]">|</span>{' '}
              <span className="font-mono text-xs text-[#8B5CF6]">
                TZ: {data?.timezoneLabel ?? 'America/Bogota'}
              </span>
            </p>
          </div>
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
            <div className="flex rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] p-1">
              {(
                [
                  ['today', 'Hoy'],
                  ['7d', '7d'],
                  ['30d', '30d'],
                  ['range', 'Rango'],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setPreset(key)}
                  className={[
                    'rounded-md px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest transition-colors',
                    preset === key
                      ? 'bg-white text-[#8B5CF6] shadow-sm'
                      : 'text-[#52616a] hover:text-[#26343d]',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
            {preset === 'range' ? (
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex flex-col gap-0.5 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Desde
                  <input
                    type="date"
                    value={rangeFrom}
                    onChange={(e) => setRangeFrom(e.target.value)}
                    className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-1.5 font-mono text-xs text-[#26343d]"
                  />
                </label>
                <label className="flex flex-col gap-0.5 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Hasta
                  <input
                    type="date"
                    value={rangeTo}
                    onChange={(e) => setRangeTo(e.target.value)}
                    className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-1.5 font-mono text-xs text-[#26343d]"
                  />
                </label>
              </div>
            ) : null}
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-[#a4b4be]/30 bg-white/80 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              <input
                type="checkbox"
                checked={syncFromSportmonks}
                onChange={(e) => setSyncFromSportmonks(e.target.checked)}
                className="rounded border-[#a4b4be]/50 text-[#8B5CF6] focus:ring-[#8B5CF6]/40"
              />
              Sync SM
            </label>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-lg border border-[#8B5CF6]/35 bg-white px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-[#6d3bd7] transition-colors hover:bg-[#eef4fa] disabled:opacity-50"
            >
              <span className="font-mono text-[#8B5CF6]" aria-hidden>
                ↻
              </span>
              {loading ? 'Cargando…' : syncFromSportmonks ? 'Actualizar + SM' : 'Actualizar'}
            </button>
          </div>
        </div>

        <p className="mt-4 font-mono text-[10px] text-[#6e7d86]">
          Rango API: {rangeKeys.from} … {rangeKeys.to}
          {preset === 'range' ? ' (rango manual)' : ` · preset ${preset}`}
          {data?.summaryHumanEs ? (
            <span className="mt-1 block font-sans text-[11px] leading-relaxed text-[#52616a]">
              {data.summaryHumanEs}
            </span>
          ) : null}
        </p>

        {loading && !data ? (
          <p className="mt-8 text-sm text-[#52616a]">Cargando métricas…</p>
        ) : null}

        <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-8">
          <div className="space-y-10 lg:col-span-8">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-serif text-2xl text-[#26343d]">Sistema</h2>
                <p className="flex items-center gap-1 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">
                  <span aria-hidden>ⓘ</span>
                  Denominador excluye pend., void, N.E.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-[#a4b4be]/15 md:grid-cols-2 xl:grid-cols-4">
                <div className="flex aspect-[4/3] flex-col justify-between bg-white p-6 md:aspect-auto md:min-h-[11rem]">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]">
                    Tasa de acierto
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-5xl font-light text-[#26343d] tabular-nums">
                      {tasaPct != null ? tasaPct.toFixed(1) : '—'}
                    </span>
                    <span className="font-mono text-2xl text-[#52616a]">%</span>
                  </div>
                  <div className="h-1 w-full bg-[#e5eff7]">
                    <div
                      className="h-full bg-[#8B5CF6]"
                      style={{
                        width: `${tasaPct != null ? Math.min(100, tasaPct) : 0}%`,
                      }}
                    />
                  </div>
                </div>
                <div className="flex flex-col justify-between bg-white p-6 md:min-h-[11rem]">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                    ROI (1 u · consenso)
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-5xl font-light tabular-nums text-[#26343d]">
                      {sysRoi?.roiPct != null ? sysRoi.roiPct.toFixed(1) : '—'}
                    </span>
                    <span className="font-mono text-2xl text-[#52616a]">%</span>
                  </div>
                  <p className="mt-2 text-[10px] leading-relaxed text-[#6e7d86]">
                    Net{' '}
                    <span className="font-mono text-[#435368]">
                      {sysRoi != null ? sysRoi.netUnits.toFixed(2) : '—'}
                    </span>{' '}
                    u ·{' '}
                    <span className="font-mono">{sysRoi?.picksCounted ?? 0}</span> picks con cuota
                    {sysRoi != null && sysRoi.picksMissingOdds > 0 ? (
                      <span className="block text-amber-800">
                        ({sysRoi.picksMissingOdds} SI/NO sin cuota en consenso)
                      </span>
                    ) : null}
                  </p>
                </div>
                <div className="flex aspect-[4/3] flex-col justify-between bg-white p-6 md:aspect-auto md:min-h-[11rem]">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                    Evaluados (A / F)
                  </span>
                  <div className="space-y-2">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-[#52616a]">Aciertos</span>
                      <span className="font-mono text-3xl text-[#26343d] tabular-nums">
                        {sys?.hits ?? '—'}
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-[#52616a]">Fallos</span>
                      <span className="font-mono text-3xl text-[#ea580c] tabular-nums">
                        {sys?.misses ?? '—'}
                      </span>
                    </div>
                  </div>
                </div>
                  <div className="grid grid-cols-2 gap-4 bg-white p-6 md:min-h-[11rem]">
                  <div>
                    <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                      Pendientes
                    </span>
                    <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                      {sys?.pending ?? '—'}
                    </span>
                  </div>
                  <div>
                    <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                      Void
                    </span>
                    <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                      {sys?.voidCount ?? '—'}
                    </span>
                  </div>
                  <div className="col-span-2 border-t border-[#e5eff7] pt-3">
                    <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                      No evaluable (N.E.)
                    </span>
                    <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                      {sys?.noEvaluable ?? '—'}
                    </span>
                  </div>
                </div>
              </div>
              <p className="text-[11px] leading-relaxed text-[#52616a]">
                En el periodo hay{' '}
                <span className="font-mono text-[#435368]">{sys?.totalPicks ?? '—'}</span> filas en
                bóveda;{' '}
                <span className="font-mono text-[#435368]">{sys?.evaluatedScored ?? '—'}</span>{' '}
                scored (hit+miss). El % usa solo esos scored.
              </p>
            </div>

            <div className="space-y-4">
              <h2 className="font-serif text-2xl text-[#26343d]">Tus picks</h2>
              {!userId ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50/90 px-6 py-4 text-sm text-amber-950">
                  Inicia sesión para ver la tasa sobre picks operados.
                </div>
              ) : tusShowEmpty ? (
                <div className="rounded-xl border border-[#a4b4be]/20 bg-[#eef4fa]/80 px-6 py-8 text-center text-sm text-[#52616a]">
                  No operaste ningún pick en este periodo; aquí aparecerá tu tasa cuando registres
                  operaciones en <span className="font-mono">bt2_picks</span> el mismo día operativo.
                </div>
              ) : yrs != null ? (
                <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-[#a4b4be]/15 md:grid-cols-2">
                  <div className="flex items-center justify-between bg-white p-8">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                        Tu tasa
                      </span>
                      <p className="mt-1 text-[10px] leading-snug text-[#6e7d86]">
                        Sólo sobre picks <strong className="text-[#52616a]">ya evaluados</strong>{' '}
                        (acierto/fallo oficial). Pendientes no entran en el %.
                      </p>
                      <div className="mt-1 flex items-baseline gap-1">
                        <span className="font-mono text-5xl font-light text-[#26343d] tabular-nums">
                          {yrs.hitRatePct != null ? yrs.hitRatePct.toFixed(1) : '—'}
                        </span>
                        <span className="font-mono text-xl text-[#52616a]">%</span>
                      </div>
                      <p className="mt-2 text-[10px] text-[#6e7d86]">
                        {yrs.hits} aciertos · {yrs.misses} fallos · {yrs.pending} pendientes ·{' '}
                        <span className="font-mono text-[#435368]">{yrs.evaluatedScored}</span> /
                        <span className="font-mono text-[#435368]">{yrs.totalPicks}</span> con
                        veredicto · {yrs.totalPicks} operados
                      </p>
                      {yoursHasPending ? (
                        <p className="mt-2 rounded-lg border border-amber-200/90 bg-amber-50/90 px-2 py-2 text-[10px] leading-snug text-amber-950">
                          Tenés picks operados sin resultado oficial aún: el{' '}
                          <strong>{yrs.hitRatePct != null ? yrs.hitRatePct.toFixed(1) : '—'} %</strong>{' '}
                          es <strong>{yrs.hits}</strong> de{' '}
                          <strong>{yrs.evaluatedScored}</strong> evaluados, no de{' '}
                          <strong>{yrs.totalPicks}</strong> operados.
                        </p>
                      ) : null}
                      <p className="mt-3 border-t border-[#e5eff7] pt-3 text-[10px] leading-relaxed text-[#52616a]">
                        ROI 1 u:{' '}
                        <span className="font-mono font-semibold text-[#26343d]">
                          {yrsRoi?.roiPct != null ? `${yrsRoi.roiPct.toFixed(1)} %` : '—'}
                        </span>
                        {' · Net '}
                        <span className="font-mono">{yrsRoi != null ? yrsRoi.netUnits.toFixed(2) : '—'}</span>
                        {' u'}
                        {yrsRoi != null && yrsRoi.picksMissingOdds > 0 ? (
                          <span className="block text-amber-900/90">
                            Sin cuota: {yrsRoi.picksMissingOdds} SI/NO
                          </span>
                        ) : null}
                      </p>
                    </div>
                    <div
                      className="flex h-16 w-16 items-center justify-center rounded-full border border-[#8B5CF6]/25 bg-[#eef4fa] text-[#8B5CF6]"
                      aria-hidden
                    >
                      <svg
                        className="h-7 w-7"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex items-center justify-between bg-white p-8">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                        Operados (total)
                      </span>
                      <span className="mt-1 block font-mono text-5xl font-light text-[#26343d] tabular-nums">
                        {yrs.totalPicks}
                      </span>
                    </div>
                    <div
                      className="flex h-16 w-16 items-center justify-center rounded-full border border-[#a4b4be]/25 bg-[#f8fafc] text-[#52616a]"
                      aria-hidden
                    >
                      <svg
                        className="h-8 w-8 opacity-70"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="1.25"
                      >
                        <circle cx="12" cy="12" r="9" />
                        <circle cx="12" cy="12" r="4" />
                      </svg>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-[#a4b4be]/20 bg-[#eef4fa]/80 px-6 py-6 text-sm text-[#52616a]">
                  Sin bloque «tus picks» (reintentá con sesión iniciada).
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-4">
            <div className="lg:sticky lg:top-4">
              {today ? (
                <div className="rounded-xl border border-[#a4b4be]/15 bg-[#eef4fa]/50 p-1">
                  <div className="rounded-lg border border-[#a4b4be]/10 bg-white p-6">
                    <div className="mb-8 flex items-start justify-between">
                      <div>
                        <h3 className="font-serif text-2xl font-bold text-[#26343d]">
                          {data &&
                          'focusOperatingDayKey' in data &&
                          data.focusOperatingDayKey !== data.todayOperatingDayKey
                            ? 'Ese día'
                            : 'Hoy'}
                        </h3>
                        <p className="text-[10px] uppercase tracking-[0.2em] text-[#52616a]">
                          {today.operatingDayKey} · resumen
                        </p>
                      </div>
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#8B5CF6]/10 text-[#8B5CF6]"
                        aria-hidden
                      >
                        <svg
                          className="h-5 w-5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        >
                          <path
                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </div>
                    </div>
                    <div className="mb-8 space-y-4">
                      <div className="flex items-center justify-between border-b border-[#e5eff7] pb-4">
                        <span className="text-sm font-medium text-[#26343d]">Total picks</span>
                        <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                          {today.totalPicks}
                        </span>
                      </div>
                      <div className="flex items-center justify-between border-b border-[#e5eff7] pb-4">
                        <span className="text-sm font-medium text-[#26343d]">Cerrados</span>
                        <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                          {today.resolved}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[#8B5CF6]">Pendientes</span>
                        <span className="font-mono text-2xl text-[#8B5CF6] tabular-nums">
                          {today.pending}
                        </span>
                      </div>
                    </div>
                    <div className="border-l-2 border-[#8B5CF6] bg-[#eef4fa] p-4">
                      <p className="text-xs font-medium leading-relaxed text-[#435368]">
                        Quedan{' '}
                        <span className="font-mono font-bold text-[#26343d]">{today.pending}</span>{' '}
                        picks esperando resultado final.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-[#a4b4be]/15 bg-[#eef4fa]/60 p-6 text-sm text-[#52616a]">
                  Sin datos de «hoy».
                </div>
              )}
            </div>
          </div>
        </div>

        <section className="mt-12 space-y-4 border-t border-[#a4b4be]/15 pt-10">
          <div className="flex flex-col justify-between gap-4 border-b border-[#a4b4be]/15 pb-4 md:flex-row md:items-end">
            <div className="flex flex-wrap gap-6">
              <button
                type="button"
                onClick={() => setTableFilter('all')}
                className={[
                  'relative pb-3 text-[10px] font-bold uppercase tracking-widest transition-colors',
                  tableFilter === 'all'
                    ? 'text-[#26343d] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#8B5CF6]'
                    : 'text-[#52616a] hover:text-[#26343d]',
                ].join(' ')}
              >
                Todos los picks del sistema
              </button>
              <button
                type="button"
                onClick={() => setTableFilter('mine')}
                className={[
                  'relative pb-3 text-[10px] font-bold uppercase tracking-widest transition-colors',
                  tableFilter === 'mine'
                    ? 'text-[#26343d] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#8B5CF6]'
                    : 'text-[#52616a] hover:text-[#26343d]',
                ].join(' ')}
              >
                Solo los que tomé
              </button>
            </div>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={onlyScored}
                onChange={(e) => setOnlyScored(e.target.checked)}
                className="h-4 w-4 rounded border-[#a4b4be]/40 accent-[#8B5CF6]"
              />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                Solo con resultado
              </span>
            </label>
          </div>

          <div className="flex flex-wrap items-end gap-3 rounded-xl border border-[#a4b4be]/15 bg-[#f8fafc]/80 p-4">
            <label className="flex min-w-[140px] flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Resultado
              <select
                value={outcomeFilter}
                onChange={(e) => setOutcomeFilter(e.target.value as MonitorOutcomeFilter)}
                className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 text-sm text-[#26343d]"
              >
                <option value="all">Todos</option>
                <option value="si">Sí</option>
                <option value="no">No</option>
                <option value="pendiente">Pendiente</option>
                <option value="void">Void</option>
                <option value="ne">N.E.</option>
              </select>
            </label>
            <label className="flex min-w-[160px] flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Mercado (contiene)
              <input
                value={marketFilter}
                onChange={(e) => setMarketFilter(e.target.value)}
                placeholder="p. ej. 1X2"
                className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 font-mono text-xs text-[#26343d]"
              />
            </label>
            <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Buscar equipo
              <input
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                placeholder="Local o visitante"
                className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 text-sm text-[#26343d]"
              />
            </label>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#a4b4be]/15 bg-white">
            <table className="w-full border-separate border-spacing-0 text-left">
              <thead>
                <tr className="bg-[#eef4fa]">
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Día
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Evento
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Mercado
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Pronóstico
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Resultado
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Cuota*
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    +/-1 u
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    ¿Cumplió?
                  </th>
                </tr>
              </thead>
              <tbody className="font-mono text-sm text-[#26343d]">
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-[#52616a]">
                      {loading ? 'Cargando…' : 'No hay filas con los filtros actuales.'}
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((r) => (
                    <tr
                      key={r.dailyPickId}
                      className="hover:bg-[#f6fafe]"
                    >
                      <td className="border-b border-[#e5eff7] p-4 text-[#52616a]">{r.dayKey}</td>
                      <td className="border-b border-[#e5eff7] p-4 font-medium text-[#26343d]">
                        {r.eventLabel}
                      </td>
                      <td className="border-b border-[#e5eff7] p-4 text-[#52616a]">{r.marketLabel}</td>
                      <td className="border-b border-[#e5eff7] p-4 text-[#26343d]">
                        {r.selectionLabel}
                      </td>
                      <td className="border-b border-[#e5eff7] p-4 text-right tabular-nums text-[#26343d]">
                        {r.scoreText}
                      </td>
                      <td className="border-b border-[#e5eff7] p-4 text-right tabular-nums text-[#52616a]">
                        {r.decimalOdds != null ? r.decimalOdds.toFixed(2) : '—'}
                      </td>
                      <td
                        className={[
                          'border-b border-[#e5eff7] p-4 text-right tabular-nums',
                          r.flatStakeReturnUnits != null && r.flatStakeReturnUnits >= 0
                            ? 'text-emerald-800'
                            : r.flatStakeReturnUnits != null
                              ? 'text-orange-900'
                              : 'text-[#52616a]',
                        ].join(' ')}
                      >
                        {r.flatStakeReturnUnits != null
                          ? r.flatStakeReturnUnits >= 0
                            ? `+${r.flatStakeReturnUnits.toFixed(2)}`
                            : r.flatStakeReturnUnits.toFixed(2)
                          : '—'}
                      </td>
                      <td className="border-b border-[#e5eff7] p-4 text-right">
                        <span
                          className={[
                            'inline-block border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest',
                            outcomeClass(r.outcome),
                          ].join(' ')}
                        >
                          {outcomeLabel(r.outcome)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            <p className="mt-2 px-2 text-[10px] leading-relaxed text-[#6e7d86]">
              * Cuota: prioridad{' '}
              <span className="font-mono">reference_decimal_odds</span>; si falta, mediana CDM sobre
              filas del evento (mercado/selección canónicos). Si no hay snapshot de cuotas en BD para
              ese evento → «—».
            </p>
            <div className="flex flex-col gap-3 border-t border-[#e5eff7] px-2 py-4 text-sm text-[#52616a] md:flex-row md:items-center md:justify-between">
              <p>
                Página{' '}
                <span className="font-mono text-[#26343d]">{monitorPage}</span> /{' '}
                <span className="font-mono text-[#26343d]">{monitorTotalPages}</span>
                {rowsTotalFromApi != null ? (
                  <>
                    {' '}
                    ·{' '}
                    <span className="font-mono text-[#26343d]">{rowsTotalFromApi}</span> filas en total
                  </>
                ) : null}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={monitorPage <= 1 || loading}
                  onClick={() => setMonitorPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[#26343d] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  disabled={monitorPage >= monitorTotalPages || loading}
                  onClick={() => setMonitorPage((p) => Math.min(monitorTotalPages, p + 1))}
                  className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[#26343d] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </div>
        </section>

        <footer className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-[#a4b4be]/15 pt-10 pb-4 text-[10px] text-[#52616a] md:flex-row">
          <div className="flex items-center gap-2">
            <span className="font-black uppercase tracking-widest">BetTracker 2.0</span>
            <span className="h-1 w-1 rounded-full bg-[#8B5CF6]" aria-hidden />
            <span className="font-bold uppercase tracking-tighter">Monitor interno</span>
          </div>
          <div className="flex flex-wrap justify-center gap-6">
            <button
              type="button"
              onClick={() => setDefsOpen(true)}
              className="font-bold uppercase tracking-widest underline decoration-[#8B5CF6]/30 underline-offset-4 hover:text-[#8B5CF6]"
            >
              Definiciones
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}
