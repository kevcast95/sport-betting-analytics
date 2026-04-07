import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'
import {
  IconArrowForward,
  IconCheckCircle,
  IconFactCheck,
  IconTrendingUp,
  IconWallet,
} from '@/components/bt2StitchIcons'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { todayRoiPercent, todaySessionPnlAndStake } from '@/lib/dayLedgerMetrics'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { parseCopIntegerInput } from '@/lib/treasuryMath'
import { useBankrollStore } from '@/store/useBankrollStore'
import {
  selectStationLocked,
  useSessionStore,
} from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'

const DAILY_REVIEW_TOUR = getTourScript('daily-review')!

function discrepancyPercent(exchangeCop: number, projectedCop: number): number {
  const base = Math.max(projectedCop, 1)
  return (Math.abs(exchangeCop - projectedCop) / base) * 100
}

function formatCop(n: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(n)
}

export default function DailyReviewPage() {
  const ledger = useTradeStore((s) => s.ledger)
  const projectedCop = useBankrollStore((s) => s.confirmedBankrollCop)
  const closeStation = useSessionStore((s) => s.closeStationAndFinalizeDay)
  const stationLocked = useSessionStore(selectStationLocked)
  const lastSummary = useSessionStore((s) => s.lastCloseSummary)
  const lockedUntil = useSessionStore((s) => s.stationLockedUntilIso)
  // US-FE-012 / US-FE-014: día operativo y gracia
  const operatingDayKey = useSessionStore((s) => s.operatingDayKey)
  const graceActiveUntilIso = useSessionStore((s) => s.graceActiveUntilIso)
  const pendingItems = useSessionStore((s) => s.previousDayPendingItems)

  // Tiempo restante calculado localmente — NO usar Date.now() en selectores Zustand
  const [nowMs, setNowMs] = useState(Date.now)
  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const graceRemainingMs = useMemo(
    () => graceActiveUntilIso
      ? Math.max(0, new Date(graceActiveUntilIso).getTime() - nowMs)
      : 0,
    [graceActiveUntilIso, nowMs],
  )
  const hasPendingWithGrace = useMemo(
    () => pendingItems.length > 0 && graceActiveUntilIso !== null && graceRemainingMs > 0,
    [pendingItems.length, graceActiveUntilIso, graceRemainingMs],
  )

  const graceHoursLeft = Math.ceil(graceRemainingMs / (60 * 60 * 1000))

  const [exchangeRaw, setExchangeRaw] = useState('')
  const [reflection, setReflection] = useState('')
  const [discrepancyNote, setDiscrepancyNote] = useState('')
  const [error, setError] = useState<string | null>(null)

  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('daily-review'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    if (!hasSeenTour) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour])

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const { netPnlCop, totalStakeCop, count } = useMemo(
    () => todaySessionPnlAndStake(ledger),
    [ledger],
  )
  const roiToday = useMemo(() => todayRoiPercent(ledger), [ledger])

  const recentEntries = useMemo(() => {
    return [...ledger]
      .sort(
        (a, b) =>
          new Date(b.settledAt).getTime() - new Date(a.settledAt).getTime(),
      )
      .slice(0, 3)
  }, [ledger])

  const exchangeParsed = parseCopIntegerInput(exchangeRaw)
  const exchangeCop = Number.isFinite(exchangeParsed) ? exchangeParsed : Number.NaN
  const diffPct =
    Number.isFinite(exchangeCop) && projectedCop >= 0
      ? discrepancyPercent(exchangeCop, projectedCop)
      : Number.NaN
  const needsNote = Number.isFinite(diffPct) && diffPct > 1

  const previewDisciplineScore = Math.min(
    100,
    Math.round(52 + Math.min(38, count * 9) + (reflection.trim().length >= 24 ? 4 : 0)),
  )

  const roiBarPct = Math.min(
    100,
    Math.max(12, 45 + roiToday * 1.8),
  )

  const sessionLabel = useMemo(() => {
    if (operatingDayKey) return operatingDayKey
    const d = new Date()
    return d.toLocaleDateString('es-CO', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }, [operatingDayKey])

  const onClose = () => {
    setError(null)
    if (!Number.isFinite(exchangeCop) || exchangeCop < 0) {
      setError('Indica un saldo real válido en la casa.')
      return
    }
    if (reflection.trim().length < 8) {
      setError('La reflexión profesional es obligatoria (mín. 8 caracteres).')
      return
    }
    const res = closeStation({
      exchangeCop,
      projectedCop,
      dailyReflection: reflection,
      discrepancyNote: needsNote ? discrepancyNote : undefined,
      settlementsTodayCount: count,
    })
    if (!res.ok) {
      if (res.reason === 'note_required_for_discrepancy') {
        setError(
          'Discrepancia mayor al 1 %: añade una nota (comisiones, depósitos, etc.).',
        )
      } else {
        setError('No se pudo cerrar la estación. Revisa los datos.')
      }
      return
    }
  }

  const reconStatusLabel =
    !Number.isFinite(exchangeCop)
      ? '—'
      : diffPct <= 1
        ? 'Coincidencia aceptable'
        : 'Discrepancia'

  if (stationLocked && lastSummary) {
    return (
      <section className="relative mx-auto max-w-2xl space-y-8" aria-label="Estación cerrada">
        <div className="pointer-events-none fixed inset-0 -z-10">
          <div className="absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-[#6d3bd7]/5 to-transparent blur-3xl" />
        </div>
        <div className="rounded-2xl border border-[#8B5CF6]/20 bg-white/90 p-8 shadow-sm backdrop-blur-md">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
            Revisión final
          </p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-[#26343d]">
            Estación cerrada
          </h1>
          {/* US-FE-014: día operativo legible */}
          <p className="mt-1 text-[10px] font-mono font-semibold text-[#52616a]">
            Día operativo:{' '}
            <span className="text-[#26343d]">{operatingDayKey ?? '—'}</span>
          </p>
          <p className="mt-1 text-sm text-[#52616a]" style={monoStyle}>
            Hasta:{' '}
            {lockedUntil
              ? new Date(lockedUntil).toLocaleString('es-CO')
              : '—'}
          </p>
          <dl className="mt-6 space-y-3 text-sm" style={monoStyle}>
            <div className="flex justify-between gap-4">
              <dt className="text-[#52616a]">Reconciliación</dt>
              <dd>
                {lastSummary.status === 'PERFECT_MATCH'
                  ? 'Coincidencia aceptable'
                  : 'Discrepancia registrada'}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[#52616a]">Disciplina del día</dt>
              <dd className="tabular-nums">
                {lastSummary.disciplineScore} / 100
              </dd>
            </div>
          </dl>
        </div>
      </section>
    )
  }

  return (
    <div className="relative w-full" aria-label="Cierre del día">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-[#6d3bd7]/5 to-transparent blur-3xl" />
        <div className="absolute bottom-0 left-0 h-1/2 w-1/4 bg-gradient-to-tr from-[#ddeaf3] to-transparent blur-2xl" />
      </div>

      <div className="mx-auto flex min-h-0 max-w-7xl flex-col items-center px-6 pb-24 pt-8 md:px-12">
        {/* US-FE-012: aviso de gracia activa con ítems pendientes */}
        {hasPendingWithGrace && (
          <div
            className="mb-8 w-full rounded-xl border border-[#FACC15]/40 bg-[#FACC15]/10 px-5 py-4"
            role="alert"
          >
            <p className="text-sm font-bold text-[#92600a]">
              Día anterior con pendientes — gracia activa
            </p>
            <ul className="mt-1 text-xs text-[#92600a]/80 space-y-0.5">
              {pendingItems.includes('STATION_UNCLOSED') && (
                <li>· Estación del día anterior sin cerrar. Completa el cierre ahora.</li>
              )}
              {pendingItems.includes('UNSETTLED_PICK') && (
                <li>· Picks desbloqueados sin liquidar del día anterior.</li>
              )}
            </ul>
            <p className="mt-2 font-mono text-xs font-semibold text-[#92600a]">
              Tiempo restante de gracia: {graceHoursLeft} h
            </p>
          </div>
        )}

        <div className="mb-12 w-full text-center md:mb-16">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-[#52616a]">
            Revisión final
          </p>
          <div className="flex items-center justify-center gap-4">
            <h1 className="text-4xl font-extrabold leading-none tracking-tight text-[#26343d] md:text-5xl">
              Análisis post-sesión
            </h1>
            <button
              type="button"
              onClick={() => { resetTour('daily-review'); setTourOpen(true) }}
              className="inline-flex items-center gap-1 rounded-lg border border-[#a4b4be]/30 bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] transition-colors hover:border-[#8B5CF6]/30 hover:text-[#8B5CF6]"
              title="Ver cómo funciona esta vista"
            >
              <span aria-hidden className="text-[11px]">?</span>
              Cómo funciona
            </button>
          </div>
          <p className="mt-4 font-medium text-[#52616a]">
            {/* US-FE-014: día operativo calendario */}
            Día operativo: <span className="font-mono">{sessionLabel}</span> · Estación activa
          </p>
        </div>

        <div className="grid w-full grid-cols-1 items-start gap-8 lg:grid-cols-12">
          <div className="space-y-8 lg:col-span-7">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="flex aspect-square flex-col justify-between rounded-xl bg-[#eef4fa] p-8 md:aspect-auto">
                <div className="flex items-start justify-between">
                  <span className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                    ROI del día
                  </span>
                  <IconTrendingUp className="text-[#6d3bd7]" />
                </div>
                <div className="mt-8">
                  <div
                    className="font-mono text-4xl font-semibold tracking-tighter text-[#26343d] sm:text-5xl"
                    style={monoStyle}
                  >
                    {roiToday >= 0 ? '+' : ''}
                    {roiToday.toFixed(1)}%
                  </div>
                  <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-[#d5e5ef]">
                    <div
                      className="h-full bg-[#6d3bd7]"
                      style={{ width: `${roiBarPct}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="flex flex-col justify-between rounded-xl bg-[#eef4fa] p-8">
                <div className="flex items-start justify-between">
                  <span className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                    P/L neto
                  </span>
                  <IconWallet className="text-[#6d3bd7]" />
                </div>
                <div className="mt-8">
                  <div
                    className={`font-mono text-4xl font-semibold tracking-tighter sm:text-5xl ${netPnlCop >= 0 ? 'text-[#059669]' : 'text-[#9e3f4e]'}`}
                    style={monoStyle}
                  >
                    {netPnlCop >= 0 ? '+' : ''}
                    {formatCop(Math.round(netPnlCop))}
                  </div>
                  <p className="mt-2 text-sm text-[#52616a]">
                    {count} liquidación(es) · stake acum.{' '}
                    {Math.round(totalStakeCop)} COP
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-col items-stretch justify-between gap-6 rounded-xl border border-[#a4b4be]/15 bg-white p-8 shadow-sm sm:flex-row sm:items-center">
              <div className="flex items-center gap-6">
                <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-[#e9ddff] shadow-[inset_0px_0px_20px_rgba(109,59,215,0.05)]">
                  <Bt2ShieldCheckIcon className="h-10 w-10 text-[#6d3bd7]" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-widest text-[#52616a]">
                    Disciplina del día (vista previa)
                  </h3>
                  <div
                    className="font-mono text-4xl font-bold text-[#26343d]"
                    style={monoStyle}
                  >
                    {previewDisciplineScore} / 100
                  </div>
                </div>
              </div>
              <div className="hidden md:block">
                <span className="rounded-full bg-[#6029c9]/10 px-4 py-2 text-xs font-bold uppercase tracking-tighter text-[#6029c9]">
                  Protocolo activo
                </span>
              </div>
            </div>

            <div className="rounded-xl bg-[#eef4fa]/50 p-8">
              <h3 className="mb-6 text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                Entradas recientes en ledger
              </h3>
              <div className="space-y-4">
                {recentEntries.length === 0 ? (
                  <p className="text-sm text-[#52616a]">
                    Sin liquidaciones aún.
                  </p>
                ) : (
                  recentEntries.map((r) => (
                    <div
                      key={`${r.pickId}-${r.settledAt}`}
                      className="flex items-center justify-between border-b border-[#a4b4be]/10 py-3 last:border-0"
                    >
                      <div className="flex items-center gap-4">
                        <span className="h-2 w-2 shrink-0 rounded-full bg-[#6d3bd7]" />
                        <span className="text-sm font-medium text-[#26343d]">
                          {r.titulo ?? r.pickId}
                        </span>
                      </div>
                      <span className="font-mono text-sm" style={monoStyle}>
                        {r.pnlCop >= 0 ? '+' : ''}
                        {formatCop(Math.round(r.pnlCop))}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-col space-y-8 lg:col-span-5">
            <div className="rounded-xl bg-[#0a0f12] p-8 text-[#fcf5ff] shadow-xl">
              <div className="mb-8 flex items-center gap-3">
                <IconFactCheck className="shrink-0 text-[#e9ddff]" />
                <h2 className="text-lg font-bold tracking-tight">
                  Reconciliación
                </h2>
              </div>
              <div className="space-y-6">
                <div>
                  <label
                    htmlFor="bt2-bankroll-verify"
                    className="mb-3 block text-xs font-semibold uppercase tracking-[0.15em] text-[#d5e5ef]"
                  >
                    Verificar saldo en la casa (COP)
                  </label>
                  <div className="relative">
                    <div
                      className="absolute left-6 top-1/2 -translate-y-1/2 font-mono text-2xl text-[#6e7d86]"
                      style={monoStyle}
                    >
                      $
                    </div>
                    <input
                      id="bt2-bankroll-verify"
                      type="text"
                      inputMode="numeric"
                      value={exchangeRaw}
                      onChange={(e) => setExchangeRaw(e.target.value)}
                      className="w-full rounded-xl border-0 bg-[#26343d]/40 py-6 pl-12 pr-6 font-mono text-2xl font-semibold text-white placeholder:text-[#52616a]/60 focus:ring-2 focus:ring-[#ddcdff]"
                      style={monoStyle}
                      placeholder="0"
                    />
                  </div>
                </div>
                <div className="space-y-4 rounded-lg bg-[#26343d]/30 p-6">
                  <div className="flex justify-between text-sm">
                    <span className="text-[#d5e5ef]">Saldo proyectado</span>
                    <span className="font-medium font-mono" style={monoStyle}>
                      {formatCop(Math.round(projectedCop))}
                    </span>
                  </div>
                  <div className="flex justify-between border-t border-white/5 pt-4 text-sm">
                    <span className="text-[#d5e5ef]">Estado</span>
                    <span className="flex items-center gap-1 font-bold text-[#e9ddff]">
                      {Number.isFinite(diffPct) && diffPct <= 1 ? (
                        <>
                          <IconCheckCircle className="text-[#e9ddff]" />
                          {reconStatusLabel}
                        </>
                      ) : (
                        <span className="text-[#fe932c]">{reconStatusLabel}</span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-grow rounded-xl bg-[#eef4fa] p-8">
              <label
                htmlFor="bt2-professional-reflection"
                className="mb-3 block text-xs font-semibold uppercase tracking-[0.15em] text-[#52616a]"
              >
                Reflexión profesional
              </label>
              <textarea
                id="bt2-professional-reflection"
                rows={6}
                value={reflection}
                onChange={(e) => setReflection(e.target.value)}
                placeholder="Notas de sesión u observaciones de disciplina…"
                className="min-h-[160px] w-full resize-none rounded-xl border-0 bg-white p-6 text-sm text-[#26343d] focus:ring-1 focus:ring-[#6d3bd7]"
              />
            </div>

            {needsNote ? (
              <div className="rounded-xl border border-[#9e3f4e]/25 bg-[#fff1f2]/60 p-6">
                <label className="text-xs font-bold uppercase text-[#9e3f4e]">
                  Nota aclaratoria (obligatoria si Δ &gt; 1 %)
                </label>
                <textarea
                  rows={3}
                  value={discrepancyNote}
                  onChange={(e) => setDiscrepancyNote(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-[#a4b4be]/30 bg-white p-4 text-sm"
                  placeholder="Comisiones, depósitos externos…"
                />
              </div>
            ) : null}

            {error ? (
              <p className="text-center text-sm font-medium text-[#9e3f4e]" role="alert">
                {error}
              </p>
            ) : null}

            <button
              type="button"
              onClick={onClose}
              className="group flex w-full items-center justify-center space-x-3 rounded-xl bg-gradient-to-r from-[#6d3bd7] to-[#612aca] py-8 text-lg font-bold tracking-tight text-white transition-all hover:shadow-lg active:scale-[0.98]"
            >
              <span>Cerrar estación y finalizar día</span>
              <IconArrowForward className="transition-transform group-hover:translate-x-1" />
            </button>
            <p className="text-center text-[10px] font-medium uppercase tracking-widest text-[#52616a]/60">
              Esta acción es definitiva y bloqueará el ledger para hoy.
            </p>
          </div>
        </div>
      </div>

      {/* US-FE-021 (T-054): tour contextual */}
      <ViewTourModal
        open={tourOpen}
        title={DAILY_REVIEW_TOUR.title}
        steps={DAILY_REVIEW_TOUR.steps}
        onComplete={() => { setTourOpen(false); markTourSeen('daily-review') }}
      />
    </div>
  )
}
