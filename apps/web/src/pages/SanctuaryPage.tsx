import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { ledgerAggregateMetrics } from '@/lib/ledgerAnalytics'
import { useBankrollStore } from '@/store/useBankrollStore'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTourStore } from '@/store/useTourStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'

/**
 * US-FE-004: Santuario. Hero + tarjetas alineadas al mock Stitch (ref compuesta;
 * el HTML en `us_fe_004_sanctuaryt.md` no incluye este bloque; se portan tokens Zurich Calm).
 */
const SANCTUARY_TOUR = getTourScript('sanctuary')!

export default function SanctuaryPage() {
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const hasCompletedDiagnostic = useUserStore((s) => s.hasCompletedDiagnostic)
  const onboardingPhaseAComplete = useUserStore((s) => s.onboardingPhaseAComplete)
  const confirmedBankrollCop = useBankrollStore((s) => s.confirmedBankrollCop)
  const graceActiveUntilIso = useSessionStore((s) => s.graceActiveUntilIso)
  const pendingItems = useSessionStore((s) => s.previousDayPendingItems)

  // Tiempo restante calculado localmente — NO usar Date.now() dentro de selectores
  // de Zustand (useSyncExternalStore detectaría "tearing" en cada nanosegundo → loop)
  const [nowMs, setNowMs] = useState(Date.now)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  useEffect(() => {
    timerRef.current = setInterval(() => setNowMs(Date.now()), 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
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
  const operatingDayKey = useSessionStore((s) => s.operatingDayKey)
  const penaltiesApplied = useSessionStore((s) => s.penaltiesApplied)
  const stationLocked = useSessionStore(selectStationLocked)
  const sessionPendingPrev = useSessionStore(
    (s) => s.sessionPendingPrevDaySettlements,
  )
  const sessionStationClosed = useSessionStore(
    (s) => s.sessionStationClosedToday,
  )

  // US-FE-016: tour de primera visita
  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('sanctuary'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  // Mostrar tour la primera vez que se monta la vista,
  // solo DESPUÉS de que el onboarding fase A haya terminado.
  useEffect(() => {
    if (!hasSeenTour && onboardingPhaseAComplete) {
      const t = setTimeout(() => setTourOpen(true), 600)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour, onboardingPhaseAComplete])

  const handleTourComplete = () => {
    setTourOpen(false)
    markTourSeen('sanctuary')
  }

  const handleForceShowTour = () => {
    resetTour('sanctuary')
    setTourOpen(true)
  }

  const graceHoursLeft = Math.ceil(graceRemainingMs / (60 * 60 * 1000))
  const lastPenalty = penaltiesApplied[penaltiesApplied.length - 1] ?? null

  const ledger = useTradeStore((s) => s.ledger)
  const patrimonioMetrics = useMemo(() => ledgerAggregateMetrics(ledger), [ledger])
  /**
   * D-05-006: indicadores solo con al menos una liquidación en ledger (fuente local/API hidratada).
   * Sin historial → "—" y microcopy honesto; prohibido reintroducir literales decorativos.
   */
  const hasSettlementHistory = ledger.length > 0
  const growthPatrimonialDisplay = hasSettlementHistory
    ? `${patrimonioMetrics.roiPct >= 0 ? '+' : ''}${patrimonioMetrics.roiPct.toFixed(1)}%`
    : '—'
  const drawdownDisplay = hasSettlementHistory
    ? confirmedBankrollCop > 0
      ? `${((patrimonioMetrics.maxDrawdownCop / confirmedBankrollCop) * 100).toFixed(1)}%`
      : `${patrimonioMetrics.maxDrawdownCop.toLocaleString('es-CO')} COP`
    : '—'

  const equityFormatted =
    confirmedBankrollCop <= 0
      ? '—'
      : new Intl.NumberFormat('es-CO', {
          style: 'currency',
          currency: 'COP',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(confirmedBankrollCop)

  return (
    <div className="space-y-10">
      {/* US-FE-012: aviso de día anterior pendiente con gracia activa */}
      {hasPendingWithGrace && (
        <div
          className="rounded-xl border border-[#FACC15]/40 bg-[#FACC15]/10 px-5 py-4"
          role="alert"
          aria-label="Día anterior con ítems pendientes"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
            <div>
              <p className="text-sm font-bold text-[#92600a]">
                Día anterior pendiente
                {operatingDayKey ? (
                  <span className="ml-2 font-mono text-[11px] font-normal text-[#92600a]/70">
                    — hoy: {operatingDayKey}
                  </span>
                ) : null}
              </p>
              <ul className="mt-1 space-y-0.5 text-xs text-[#92600a]/80">
                {pendingItems.includes('STATION_UNCLOSED') && (
                  <li>· Estación del día anterior sin cerrar — completa el After-Action Review.</li>
                )}
                {pendingItems.includes('UNSETTLED_PICK') && (
                  <li>· Picks desbloqueados sin liquidar del día anterior.</li>
                )}
              </ul>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#92600a]/70">
                Gracia disponible
              </p>
              <p className="font-mono text-lg font-bold text-[#92600a]">
                {graceHoursLeft} h
              </p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-3">
            <NavLink
              to="/v2/daily-review"
              className="rounded-lg bg-[#FACC15]/30 px-4 py-1.5 text-xs font-bold text-[#92600a] transition-colors hover:bg-[#FACC15]/50"
            >
              Ir a cierre del día →
            </NavLink>
            {pendingItems.includes('UNSETTLED_PICK') && (
              <NavLink
                to="/v2/vault"
                className="rounded-lg border border-[#FACC15]/40 px-4 py-1.5 text-xs font-semibold text-[#92600a] transition-colors hover:bg-[#FACC15]/20"
              >
                Ir a La Bóveda →
              </NavLink>
            )}
          </div>
        </div>
      )}

      {/* US-FE-012: aviso de penalización reciente */}
      {lastPenalty && !hasPendingWithGrace && (
        <div
          className="rounded-xl border border-[#9e3f4e]/20 bg-[#fff1f2]/70 px-5 py-4"
          role="status"
        >
          <p className="text-sm font-bold text-[#9e3f4e]">
            Penalización conductual registrada
          </p>
          <p className="mt-1 text-xs text-[#9e3f4e]/80">
            {lastPenalty.description}
          </p>
        </div>
      )}

      <BunkerViewHeader
        title="Santuario"
        subtitle="Calma en el ruido del cambio."
        onHelpClick={handleForceShowTour}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#a4b4be]/20 bg-white p-6 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
            Patrimonio total
          </p>
          <p className="mt-2 font-mono text-3xl font-bold tabular-nums tracking-tight text-[#059669] sm:text-4xl">
            {equityFormatted}
          </p>
          <p className="mt-2 text-[11px] leading-relaxed text-[#6e7d86]">
            Capital de trabajo neto según el protocolo. Crece con liquidaciones positivas y disciplina constante.
          </p>
          <div className="mt-6 grid grid-cols-2 gap-6 border-t border-[#a4b4be]/15 pt-6">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                ROI sobre stake liquidado
              </p>
              <p
                className={`mt-1 font-mono text-lg font-bold tabular-nums ${
                  !hasSettlementHistory
                    ? 'text-[#6e7d86]'
                    : patrimonioMetrics.roiPct >= 0
                      ? 'text-[#8B5CF6]'
                      : 'text-[#914d00]'
                }`}
              >
                {growthPatrimonialDisplay}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                Drawdown máx. (serie PnL)
              </p>
              <p
                className={`mt-1 font-mono text-lg font-bold tabular-nums ${
                  !hasSettlementHistory ? 'text-[#6e7d86]' : 'text-[#914d00]'
                }`}
              >
                {drawdownDisplay}
              </p>
            </div>
          </div>
          {!hasSettlementHistory ? (
            <p className="mt-4 text-[11px] leading-relaxed text-[#6e7d86]">
              Sin historial aún. Se calculará con tus liquidaciones registradas en el protocolo.
            </p>
          ) : null}
        </div>

        <div className="rounded-xl border border-[#a4b4be]/20 bg-white p-6 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
            Día operativo (protocolo)
          </p>
          <p className="mt-2 font-mono text-lg font-bold tabular-nums text-[#26343d]">
            {operatingDayKey ?? '—'}
          </p>
          <p className="mt-3 text-sm text-[#52616a]">
            Estación:{' '}
            <span className="font-semibold text-[#26343d]">
              {stationLocked
                ? 'Cerrada para nuevas señales (ciclo actual)'
                : 'Abierta'}
            </span>
          </p>
          {sessionStationClosed === true ? (
            <p className="mt-2 text-xs text-[#52616a]">
              Cierre del día registrado en servidor para este día operativo.
            </p>
          ) : null}
          {sessionPendingPrev != null && sessionPendingPrev > 0 ? (
            <p className="mt-2 text-xs font-medium text-[#914d00]">
              Pendientes reportados (día anterior):{' '}
              <span className="font-mono tabular-nums">{sessionPendingPrev}</span>
            </p>
          ) : null}
          <NavLink
            to="/v2/daily-review"
            className="mt-5 inline-flex rounded-xl border border-[#8B5CF6]/35 bg-[#e9ddff]/25 px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-[#6d3bd7] transition-colors hover:bg-[#e9ddff]/45"
          >
            Ir a cierre del día →
          </NavLink>
          {!hasCompletedDiagnostic ? (
            <p className="mt-4 text-xs text-[#6e7d86]">
              <Link
                to="/v2/diagnostic"
                className="font-bold text-[#6d3bd7] underline-offset-2 hover:underline"
              >
                Completar diagnóstico
              </Link>{' '}
              para calibrar el perfil de operador.
            </p>
          ) : null}
        </div>
      </div>

      <section
        aria-label="Disciplina y misiones diarias"
        className="rounded-xl border border-[#a4b4be]/25 bg-[#ddeaf3]/40 p-6 shadow-sm"
      >
        <div className="flex flex-col gap-8 lg:flex-row lg:items-stretch lg:gap-10">
          <div className="flex shrink-0 items-center gap-4 rounded-xl border border-[#a4b4be]/20 bg-white px-5 py-4 shadow-sm">
            <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center text-[#8B5CF6]">
              <Bt2ShieldCheckIcon className="h-8 w-8" />
            </span>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#26343d]">
                Riqueza de carácter
              </p>
              <p className="mt-1 font-mono text-xl font-bold tabular-nums tracking-tight text-[#8B5CF6]">
                {(disciplinePoints ?? 0).toLocaleString('es-CO')}{' '}
                <span className="text-base font-bold">DP</span>
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-[#6e7d86]">
                Cada punto refleja decisiones alineadas al protocolo: liquidar, cerrar y reflexionar.
              </p>
            </div>
          </div>

          <div className="min-w-0 flex-1">
            {/* D-05-007: sin % inventado ni checklist simulado hasta contrato BE de misiones */}
            <div className="flex flex-wrap items-end justify-between gap-2">
              <h2 className="text-[10px] font-bold uppercase tracking-wider text-[#26343d]">
                Misiones diarias
              </h2>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                0% · en definición
              </p>
            </div>
            <div
              className="mt-3 h-3 overflow-hidden rounded-full bg-[#e5eff7]"
              role="progressbar"
              aria-valuenow={0}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Progreso de misiones diarias"
            >
              <div
                className="h-full w-0 rounded-full bg-[#8B5CF6] transition-[width] duration-500"
              />
            </div>
            <p className="mt-4 text-xs leading-relaxed text-[#52616a]">
              El módulo de misiones está en definición de producto. Mientras tanto, prioriza
              liquidar picks y cerrar la estación según el protocolo.
            </p>
          </div>
        </div>
      </section>

      <div className="rounded-xl border border-[#a4b4be]/30 bg-[#eef4fa]/40 p-6">
        <h2 className="text-sm font-bold tracking-tight text-[#26343d]">
          Próximo paso
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[#52616a]">
          Revisa oportunidades con valor esperado positivo en la bóveda. Cada
          desbloqueo consume DP de tu saldo de disciplina.
        </p>
        <NavLink
          to="/v2/vault"
          className="mt-4 inline-flex rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] px-5 py-2.5 text-xs font-bold uppercase tracking-wide text-white shadow-md shadow-[#8B5CF6]/20"
        >
          Ir a La Bóveda
        </NavLink>
      </div>

      {/* US-FE-016: tour contextual del Santuario */}
      <ViewTourModal
        open={tourOpen}
        title={SANCTUARY_TOUR.title}
        steps={SANCTUARY_TOUR.steps}
        onComplete={handleTourComplete}
      />
    </div>
  )
}
