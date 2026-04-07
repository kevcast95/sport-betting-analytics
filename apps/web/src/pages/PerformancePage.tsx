import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'
import {
  IconPsychology,
  IconSmallCheck,
  IconTrendingUp,
  IconVerified,
  IconWarning,
} from '@/components/bt2StitchIcons'
import { EquityChart } from '@/components/analytics/EquityChart'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import {
  equitySeriesFromLedger,
  ledgerAggregateMetrics,
} from '@/lib/ledgerAnalytics'
import { useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'

function fmtAxis(iso: string): string {
  return new Date(iso).toLocaleDateString('es-CO', {
    month: 'short',
    year: '2-digit',
  })
}

const STRATEGIC_FALLBACK =
  'El ciclo actual se define por la liquidez disponible y la varianza observada en el ledger. Mantén tamaños de unidad consistentes y endurece criterios de salida en eventos atípicos. La preparación psicológica tras el cierre reciente condiciona la siguiente sesión: evita sobreapalancamiento en rachas prolongadas.'

const PERFORMANCE_TOUR = getTourScript('performance')!

export default function PerformancePage() {
  const ledger = useTradeStore((s) => s.ledger)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const equityCop = useUserStore((s) => s.equityCop)
  const lastClose = useSessionStore((s) => s.lastCloseSummary)
  const [logScale, setLogScale] = useState(false)

  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('performance'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  useEffect(() => {
    if (!hasSeenTour) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const metrics = useMemo(() => ledgerAggregateMetrics(ledger), [ledger])
  const series = useMemo(() => equitySeriesFromLedger(ledger), [ledger])

  const psychReady = useMemo(() => {
    if (!lastClose?.at) return false
    const t = new Date(lastClose.at).getTime()
    return Date.now() - t < 24 * 60 * 60 * 1000
  }, [lastClose])

  const dp = disciplinePoints ?? 0
  const protection =
    dp >= 2000
      ? 'MÁXIMO'
      : dp >= 1200
        ? 'ALTO'
        : 'ESTÁNDAR'

  const liquidityOk = equityCop != null && equityCop > 0
  const varianceOk = ledger.length > 0

  const ddPct =
    metrics.totalStakeCop > 0
      ? (metrics.maxDrawdownCop / metrics.totalStakeCop) * 100
      : 0

  const strategicNote =
    lastClose?.dailyReflection && lastClose.dailyReflection.trim().length >= 24
      ? lastClose.dailyReflection.trim()
      : STRATEGIC_FALLBACK

  const axisLeft = series.length > 0 ? fmtAxis(series[0].t) : ''
  const axisMid =
    series.length > 2
      ? fmtAxis(series[Math.floor(series.length / 2)].t)
      : axisLeft
  const axisRight =
    series.length > 1 ? fmtAxis(series[series.length - 1].t) : axisLeft

  const roiStr =
    metrics.roiPct >= 0
      ? `+${metrics.roiPct.toFixed(1)}%`
      : `${metrics.roiPct.toFixed(1)}%`

  return (
    <div
      className="mx-auto w-full max-w-7xl space-y-12"
      aria-label="Rendimiento y estrategia"
    >
      <header className="mb-2">
        <div className="flex items-center gap-3">
          <h1 className="mb-2 text-4xl font-extrabold tracking-tight text-[#26343d]">
            Estrategia y rendimiento
          </h1>
          <button
            type="button"
            onClick={() => { resetTour('performance'); setTourOpen(true) }}
            className="mb-2 inline-flex items-center gap-1 rounded-lg border border-[#a4b4be]/30 bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] transition-colors hover:border-[#8B5CF6]/30 hover:text-[#8B5CF6]"
            title="Ver cómo funciona esta vista"
          >
            <span aria-hidden className="text-[11px]">?</span>
            Cómo funciona
          </button>
        </div>
        <p className="text-sm font-medium uppercase tracking-wide text-[#52616a] opacity-70">
          Resumen ejecutivo del protocolo Alpha
        </p>
      </header>

      <div className="mb-12 grid grid-cols-1 gap-6 md:grid-cols-4">
        <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-6 transition-shadow hover:shadow-md">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
            ROI global
          </p>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold text-[#059669]"
              style={monoStyle}
            >
              {roiStr}
            </span>
            <IconTrendingUp className="h-4 w-4 shrink-0 text-[#059669]" />
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-[#6e7d86]">
            Retorno sobre el capital total en riesgo. Refleja eficiencia del protocolo, no suerte aislada.
          </p>
        </div>
        <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-6 transition-shadow hover:shadow-md">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
            Tasa de éxito
          </p>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold text-[#26343d]"
              style={monoStyle}
            >
              {metrics.winRatePct.toFixed(1)}%
            </span>
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-[#6e7d86]">
            Porcentaje de liquidaciones positivas. En protocolos sanos tiende a superar el 50 %.
          </p>
        </div>
        <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-6 transition-shadow hover:shadow-md">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
            Caída máxima
          </p>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold text-[#914d00]"
              style={monoStyle}
            >
              {ddPct.toFixed(1)}%
            </span>
            <IconWarning className="h-4 w-4 shrink-0 text-[#914d00]" />
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-[#6e7d86]">
            Mayor retroceso acumulado respecto al stake total. Mide resistencia en rachas adversas.
          </p>
        </div>
        <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-6 transition-shadow hover:shadow-md">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
            Disciplina ganada
          </p>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold text-[#6d3bd7]"
              style={monoStyle}
            >
              +{metrics.disciplineDpFromSettlements}
            </span>
            <span className="text-sm font-bold text-[#6d3bd7]">DP</span>
            <IconVerified className="h-4 w-4 shrink-0 text-[#6d3bd7]" />
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-[#6e7d86]">
            DP acumulados en liquidaciones. Independiente del resultado: mide consistencia de proceso.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="space-y-8 lg:col-span-2">
          <section className="rounded-xl border border-[#a4b4be]/15 bg-white p-8">
            <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
              <h2 className="text-lg font-bold tracking-tight text-[#26343d]">
                Curva de equity
              </h2>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-[#eef4fa] px-3 py-1 text-[10px] font-bold uppercase text-[#26343d]">
                  Histórico
                </span>
                <button
                  type="button"
                  onClick={() => setLogScale(false)}
                  className={[
                    'rounded-full px-3 py-1 text-[10px] font-bold uppercase transition-colors',
                    !logScale
                      ? 'bg-[#eef4fa] text-[#26343d]'
                      : 'text-[#52616a] hover:bg-[#eef4fa]/60',
                  ].join(' ')}
                >
                  Lineal
                </button>
                <button
                  type="button"
                  onClick={() => setLogScale(true)}
                  className={[
                    'rounded-full px-3 py-1 text-[10px] font-bold uppercase transition-colors',
                    logScale
                      ? 'bg-[#eef4fa] text-[#26343d]'
                      : 'text-[#52616a] hover:bg-[#eef4fa]/60',
                  ].join(' ')}
                >
                  Escala log
                </button>
              </div>
            </div>
            <div className="relative flex h-72 w-full flex-col justify-end overflow-hidden rounded-lg bg-[#eef4fa]/30">
              <div className="pointer-events-none absolute inset-0 grid grid-cols-6 grid-rows-4 opacity-20">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div
                    key={i}
                    className="border-b border-r border-[#a4b4be]"
                  />
                ))}
              </div>
              <EquityChart
                series={series}
                monoStyle={monoStyle}
                useLog={logScale}
                embed
              />
              <div
                className="pointer-events-none absolute bottom-4 left-4 z-[2] flex gap-8 text-[10px] text-[#52616a]"
                style={monoStyle}
              >
                <span className="uppercase">{axisLeft}</span>
                <span className="uppercase">{axisMid}</span>
                <span className="uppercase">{axisRight}</span>
              </div>
            </div>
          </section>

          <section className="rounded-xl bg-[#eef4fa] p-8">
            <div className="mb-4 flex items-center gap-2">
              <IconPsychology className="h-5 w-5 text-[#52616a]" />
              <h2 className="text-lg font-bold tracking-tight text-[#26343d]">
                Notas estratégicas (traducción humana)
              </h2>
            </div>
            <div className="min-h-[160px] rounded-lg border border-[#a4b4be]/10 bg-white p-6">
              <p className="text-sm leading-relaxed text-[#26343d]">
                {strategicNote}
              </p>
            </div>
          </section>
        </div>

        <div className="space-y-8">
          <section className="rounded-xl border border-[#a4b4be]/15 bg-white p-8 shadow-sm">
            <h2 className="mb-8 text-sm font-bold uppercase tracking-widest text-[#6d3bd7]">
              Protocolo Alpha
            </h2>
            <ul className="space-y-6">
              <li className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-4">
                  <div
                    className={[
                      'flex h-6 w-6 items-center justify-center rounded',
                      liquidityOk
                        ? 'bg-[#e9ddff] text-[#6d3bd7]'
                        : 'border-2 border-[#a4b4be]/30 bg-transparent',
                    ].join(' ')}
                  >
                    {liquidityOk ? (
                      <IconSmallCheck className="h-4 w-4" />
                    ) : null}
                  </div>
                  <span
                    className={[
                      'text-sm font-semibold',
                      liquidityOk ? 'text-[#26343d]' : 'italic text-[#52616a]',
                    ].join(' ')}
                  >
                    Chequeo de liquidez de mercado
                  </span>
                </div>
                {!liquidityOk ? (
                  <span className="text-[10px] font-bold uppercase text-[#914d00]">
                    Pendiente
                  </span>
                ) : null}
              </li>
              <li className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-4">
                  <div
                    className={[
                      'flex h-6 w-6 items-center justify-center rounded',
                      varianceOk
                        ? 'bg-[#e9ddff] text-[#6d3bd7]'
                        : 'border-2 border-[#a4b4be]/30 bg-transparent',
                    ].join(' ')}
                  >
                    {varianceOk ? (
                      <IconSmallCheck className="h-4 w-4" />
                    ) : null}
                  </div>
                  <span
                    className={[
                      'text-sm font-semibold',
                      varianceOk ? 'text-[#26343d]' : 'italic text-[#52616a]',
                    ].join(' ')}
                  >
                    Protocolo de aceptación de varianza
                  </span>
                </div>
                {!varianceOk ? (
                  <span className="text-[10px] font-bold uppercase text-[#914d00]">
                    Pendiente
                  </span>
                ) : null}
              </li>
              <li className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-4">
                  <div
                    className={[
                      'flex h-6 w-6 items-center justify-center rounded border-2',
                      psychReady
                        ? 'border-transparent bg-[#e9ddff] text-[#6d3bd7]'
                        : 'border-[#a4b4be]/30 bg-transparent',
                    ].join(' ')}
                  >
                    {psychReady ? (
                      <IconSmallCheck className="h-4 w-4" />
                    ) : null}
                  </div>
                  <span
                    className={[
                      'text-sm font-semibold',
                      psychReady ? 'text-[#26343d]' : 'italic text-[#52616a]',
                    ].join(' ')}
                  >
                    Auditoría de preparación psicológica
                  </span>
                </div>
                {!psychReady ? (
                  <span className="text-[10px] font-bold uppercase text-[#914d00]">
                    Pendiente
                  </span>
                ) : null}
              </li>
              <li className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-4">
                  <div className="flex h-6 w-6 items-center justify-center rounded bg-[#e9ddff] text-[#6d3bd7]">
                    <IconSmallCheck className="h-4 w-4" />
                  </div>
                  <span className="text-sm font-semibold text-[#26343d]">
                    Recalibración de tamaño de unidad
                  </span>
                </div>
              </li>
            </ul>
          </section>

          <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-[#6d3bd7] to-[#612aca] p-8 text-white shadow-xl">
            <div className="pointer-events-none absolute -bottom-8 -right-8 opacity-10">
              <Bt2ShieldCheckIcon className="h-40 w-40 text-white" />
            </div>
            <h3 className="mb-6 text-[10px] font-bold uppercase tracking-[0.2em] opacity-80">
              Nivel de protección
            </h3>
            <div className="mb-4 flex items-center gap-4">
              <IconVerified className="h-10 w-10 shrink-0" />
              <span
                className="text-4xl font-bold tracking-tighter"
                style={monoStyle}
              >
                {protection}
              </span>
            </div>
            <p className="text-xs leading-relaxed opacity-70">
              Tu puntuación actual de{' '}
              <span className="font-mono font-semibold">
                {dp.toLocaleString('es-CO')} DP
              </span>{' '}
              define el acceso a informes de precisión y módulos de entrada con
              control de liquidez.
            </p>
          </div>

          <div className="relative h-48 overflow-hidden rounded-xl border border-[#a4b4be]/15">
            <div
              className="absolute inset-0 bg-gradient-to-br from-[#0a0f12] via-[#26343d] to-[#6d3bd7]/40"
              aria-hidden
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0a0f12]/85 to-transparent" />
            <div className="absolute bottom-0 left-0 flex flex-col justify-end p-6">
              <span className="mb-1 text-[10px] font-bold uppercase tracking-widest text-[#e9ddff]">
                Sentimiento global
              </span>
              <span className="text-sm font-bold tracking-tight text-white">
                Risk-off moderado · estable
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* US-FE-021 (T-055): tour contextual */}
      <ViewTourModal
        open={tourOpen}
        title={PERFORMANCE_TOUR.title}
        steps={PERFORMANCE_TOUR.steps}
        onComplete={() => { setTourOpen(false); markTourSeen('performance') }}
      />
    </div>
  )
}
