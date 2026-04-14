/**
 * US-FE-003: rejilla de picks V2 (bóveda) con desbloqueo por DP.
 * US-FE-016 (T-048): tour contextual de primera visita + botón de ayuda.
 * US-FE-025 (Sprint 04): picks desde GET /bt2/vault/picks; fallback mock en dev.
 */
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useLocation } from 'react-router-dom'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import { PickCard } from '@/components/vault/PickCard'
import { VaultDevTools } from '@/components/vault/VaultDevTools'
import { VektorShortDisclaimer } from '@/components/vault/VektorShortDisclaimer'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import {
  computeVaultQuota,
  VAULT_DAILY_CAP_PREMIUM,
  VAULT_DAILY_CAP_STANDARD,
} from '@/lib/vaultQuota'
import {
  reorderVaultPicksForBandCycle,
  selectVisibleFromOrderedPool,
} from '@/lib/vaultTimeBand'
import { useTradeStore } from '@/store/useTradeStore'

const VAULT_TOUR = getTourScript('vault')!

function VaultEmptyState({
  headline,
  detail,
  technicalHint,
  onRefresh,
}: {
  headline: string
  detail: string
  /** Línea opcional con conteos operativos (sin mezclar con el mensaje principal). */
  technicalHint?: string | null
  /** Tras cerrar sesión / ingesta CDM, forzar otro `session/open` + GET vault. */
  onRefresh?: () => void
}) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-[#a4b4be]/20 bg-[#f6fafe] py-16 text-center">
      <p className="mb-2 text-lg font-bold text-[#26343d]">{headline}</p>
      <p className="max-w-sm text-sm text-[#52616a]">{detail}</p>
      {technicalHint ? (
        <p className="mt-3 max-w-md font-mono text-[10px] leading-relaxed text-[#6e7d86]">
          {technicalHint}
        </p>
      ) : null}
      {onRefresh ? (
        <button
          type="button"
          onClick={onRefresh}
          className="mt-6 rounded-lg border border-[#26343d]/25 bg-[#26343d] px-5 py-2 text-sm font-bold text-white transition hover:bg-[#1c2730]"
        >
          Obtener cartelera
        </button>
      ) : null}
    </div>
  )
}

function VaultErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-[#fee2e2] bg-[#fff1f2] py-16 text-center">
      <p className="mb-2 text-lg font-bold text-[#9b1c1c]">Error al cargar la bóveda</p>
      <p className="mb-4 max-w-sm text-sm text-[#52616a]">
        No se pudo conectar con el servidor. Verifica tu conexión o inténtalo de nuevo.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-lg bg-[#8B5CF6] px-5 py-2 text-sm font-semibold text-white"
      >
        Reintentar
      </button>
    </div>
  )
}

function VaultLoadingState() {
  return (
    <>
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="min-h-[220px] animate-pulse rounded-xl border border-[#a4b4be]/20 bg-[#eef4fa]"
        />
      ))}
    </>
  )
}

export default function VaultPage() {
  const location = useLocation()
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const onboardingPhaseAComplete = useUserStore((s) => s.onboardingPhaseAComplete)

  const apiPicks = useVaultStore((s) => s.apiPicks)
  const picksLoadStatus = useVaultStore((s) => s.picksLoadStatus)
  const picksMessage = useVaultStore((s) => s.picksMessage)
  const takenApiPicks = useVaultStore((s) => s.takenApiPicks)
  const unlockedPickIds = useVaultStore((s) => s.unlockedPickIds)
  const loadApiPicks = useVaultStore((s) => s.loadApiPicks)
  const regenerateVaultSlate = useVaultStore((s) => s.regenerateVaultSlate)
  const invalidateVaultIfOperatingDayMismatch = useVaultStore(
    (s) => s.invalidateVaultIfOperatingDayMismatch,
  )
  const operatingDayKey = useSessionStore((s) => s.operatingDayKey)
  const takeApiPick = useVaultStore((s) => s.takeApiPick)
  const unlockPremiumVaultPick = useVaultStore((s) => s.unlockPremiumVaultPick)
  const tryUnlockPick = useVaultStore((s) => s.tryUnlockPick)
  const hydrateLedgerFromApi = useTradeStore((s) => s.hydrateLedgerFromApi)
  const vaultPoolMeta = useVaultStore((s) => s.vaultPoolMeta)
  const vaultDaySnapshotMeta = useVaultStore((s) => s.vaultDaySnapshotMeta)
  const vaultLocalSlateCycle = useVaultStore((s) => s.vaultLocalSlateCycle)

  const [vaultToast, setVaultToast] = useState<string | null>(null)

  const userTimeZone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Bogota',
    [],
  )
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // US-FE-016: tour de primera visita — solo tras onboarding completo
  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('vault'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  // T-169: al cambiar día operativo vs último snapshot persistido, forzar nuevo GET.
  useEffect(() => {
    invalidateVaultIfOperatingDayMismatch(operatingDayKey)
  }, [operatingDayKey, invalidateVaultIfOperatingDayMismatch])

  /**
   * Si la última carga dejó `empty` en persistencia, el efecto siguiente solo corre con `idle`
   * y nunca se vuelve a pedir la API (p. ej. tras `session/close` + CDM nuevo sin cambiar de ruta).
   * Al montar la bóveda, normalizar a `idle` para disparar un GET fresco.
   */
  useLayoutEffect(() => {
    const s = useVaultStore.getState().picksLoadStatus
    if (s === 'empty') {
      useVaultStore.setState({ picksLoadStatus: 'idle' })
    }
  }, [])

  // Cargar picks de API al montar o tras invalidación (picksLoadStatus → idle).
  useEffect(() => {
    if (picksLoadStatus === 'idle') {
      void loadApiPicks()
    }
  }, [picksLoadStatus, loadApiPicks])

  useEffect(() => {
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current)
    }
  }, [])

  useEffect(() => {
    if (!hasSeenTour && onboardingPhaseAComplete) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour, onboardingPhaseAComplete])

  const handleTourComplete = () => {
    setTourOpen(false)
    markTourSeen('vault')
  }

  const handleForceShowTour = () => {
    resetTour('vault')
    setTourOpen(true)
  }

  /**
   * US-FE-033: estándar y premium requieren POST /bt2/picks (compromiso / desbloqueo)
   * antes de ver contenido y liquidar.
   */
  const isApiPickCommitted = useCallback(
    (pick: Bt2VaultPickOut) =>
      takenApiPicks.some((r) => r.vaultPickId === pick.id),
    [takenApiPicks],
  )

  // Para compatibilidad con picks mock (string IDs)
  const isMockPickUnlocked = useCallback(
    (id: string) => unlockedPickIds.includes(id),
    [unlockedPickIds],
  )
  void isMockPickUnlocked // evitar lint unused

  const visibleHardCap = vaultPoolMeta?.poolHardCap ?? 5

  /** Orden según ciclo local (regenerar); sin esto la grilla ignora el barajado. */
  const orderedPoolPicks = useMemo(
    () => reorderVaultPicksForBandCycle(apiPicks, userTimeZone, vaultLocalSlateCycle),
    [apiPicks, userTimeZone, vaultLocalSlateCycle],
  )

  /** Ventana de 5 sobre el pool ordenado; `vaultLocalSlateCycle` rota el inicio (circular). */
  const displayedPicks = useMemo(
    () =>
      selectVisibleFromOrderedPool(
        orderedPoolPicks,
        userTimeZone,
        visibleHardCap,
        undefined,
        vaultLocalSlateCycle,
      ),
    [orderedPoolPicks, userTimeZone, visibleHardCap, vaultLocalSlateCycle],
  )

  // Conteo por tier (solo cartelera visible)
  const standardCount = useMemo(
    () => displayedPicks.filter((p) => p.accessTier === 'standard').length,
    [displayedPicks],
  )
  const premiumCount = useMemo(
    () => displayedPicks.filter((p) => p.accessTier === 'premium').length,
    [displayedPicks],
  )

  const quota = useMemo(
    () => computeVaultQuota(takenApiPicks, operatingDayKey, apiPicks),
    [takenApiPicks, operatingDayKey, apiPicks],
  )

  const emptyVaultCopy = useMemo(() => {
    const m = vaultDaySnapshotMeta
    const serverMsg = picksMessage
    const countsHint = m
      ? `Pool elegible (fallback): ${m.fallbackEligiblePoolCount} filas · eventos futuros en ventana: ${m.futureEventsInWindowCount}`
      : null
    if (m?.operationalEmptyHard) {
      return {
        headline: 'Sin cartelera elegible (vacío operativo)',
        detail:
          m.vaultOperationalMessageEs?.trim() ||
          serverMsg ||
          'No hay eventos o cuotas utilizables en el universo del día; no se publicó señal de respaldo. Revisa ingesta CDM u operación.',
        technicalHint: countsHint,
      }
    }
    return {
      headline: 'Sin señales publicadas hoy',
      detail:
        m?.vaultOperationalMessageEs?.trim() ||
        serverMsg ||
        'El sistema actualiza la cartelera en el ciclo operativo. Si hay datos pero el razonador no aportó salida, el servidor puede dejar la bóveda vacía según reglas.',
      technicalHint: countsHint,
    }
  }, [picksMessage, vaultDaySnapshotMeta])

  const takeBlockedByQuota = useCallback(
    (pick: Bt2VaultPickOut, taken: boolean) => {
      if (taken) return false
      if (pick.accessTier === 'standard') return quota.atStandardCap
      return quota.atPremiumCap
    },
    [quota.atPremiumCap, quota.atStandardCap],
  )

  const showVaultToast = useCallback((msg: string) => {
    setVaultToast(msg)
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => {
      setVaultToast(null)
      toastTimer.current = null
    }, 6000)
  }, [])

  useEffect(() => {
    const st = location.state as { settlementBlocked?: string } | null | undefined
    const msg = st?.settlementBlocked
    if (!msg) return
    showVaultToast(msg)
    window.history.replaceState({}, document.title)
  }, [location.state, showVaultToast])

  const handlePremiumUnlock = useCallback(
    async (pickId: string) => {
      const res = await unlockPremiumVaultPick(pickId)
      if (res.ok) {
        showVaultToast('Señal premium desbloqueada. Ya puedes registrar la posición.')
        void hydrateLedgerFromApi()
        return
      }
      if (res.reason === 'insufficient_dp_premium' && res.premiumDetail) {
        showVaultToast(res.premiumDetail.message)
        return
      }
      if (res.reason === 'station_locked') {
        showVaultToast('Estación cerrada: no puedes desbloquear señales en este ciclo.')
        return
      }
      if (res.reason === 'already_unlocked') return
      if (res.reason === 'not_premium' || res.reason === 'pick_not_found') return
      if (res.reason === 'kickoff_elapsed') {
        showVaultToast(
          res.apiMessage ??
            'El partido ya inició; no puedes desbloquear esta señal.',
        )
        return
      }
      showVaultToast('No se pudo desbloquear la señal premium. Reintenta o revisa tu conexión.')
    },
    [unlockPremiumVaultPick, showVaultToast, hydrateLedgerFromApi],
  )

  const handleTakePick = useCallback(
    async (pickId: string) => {
      const apiPick = apiPicks.find((p) => p.id === pickId)
      if (apiPick) {
        const res = await takeApiPick(apiPick)
        if (res.ok) {
          showVaultToast('Señal registrada en el protocolo.')
          void hydrateLedgerFromApi()
          return
        }
        if (res.reason === 'insufficient_dp_premium' && res.premiumDetail) {
          showVaultToast(res.premiumDetail.message)
          return
        }
        if (res.reason === 'premium_not_unlocked') {
          showVaultToast('Desbloquea primero la señal premium (deslizar en la tarjeta).')
          return
        }
        if (res.reason === 'station_locked') {
          showVaultToast('Estación cerrada: no puedes registrar señales en este ciclo.')
          return
        }
        if (res.reason === 'already_unlocked') return
        if (res.reason === 'pick_unavailable') {
          showVaultToast('Este pick no está disponible para registro.')
          return
        }
        if (res.reason === 'kickoff_elapsed') {
          showVaultToast(
            res.apiMessage ??
              'El partido ya inició; el servidor no permite registrar el pick.',
          )
          return
        }
        if (res.reason === 'quota_standard_exhausted') {
          showVaultToast(
            'Cupo diario de señales estándar agotado (3 por día operativo).',
          )
          return
        }
        if (res.reason === 'quota_premium_exhausted') {
          showVaultToast(
            'Cupo diario de señales premium agotado (2 por día operativo).',
          )
          return
        }
        if (res.reason === 'insufficient_bankroll') {
          showVaultToast(
            res.apiMessage ??
              'Bankroll insuficiente para el stake de esta señal.',
          )
          return
        }
        showVaultToast(
          res.apiMessage ??
            'No se pudo registrar la señal. Reintenta o revisa tu conexión.',
        )
      } else {
        tryUnlockPick(pickId)
      }
    },
    [apiPicks, takeApiPick, tryUnlockPick, showVaultToast, hydrateLedgerFromApi],
  )

  return (
    <section aria-label="Bóveda de picks" className="space-y-6">
      {vaultToast ? (
        <div
          role="status"
          className="rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] px-4 py-3 text-sm text-[#26343d]"
        >
          {vaultToast}
        </div>
      ) : null}
      <BunkerViewHeader
        title="La Bóveda"
        subtitle="Señales del día con criterio DSR: lectura prioritaria apoyada en datos e histórico del input y coherencia cuota–narrativa — no maximizar ganancia como eje único (D-06-027). Estándar sin DP; premium con desbloqueo en DP y registro aparte."
        onHelpClick={handleForceShowTour}
        rightActions={
          <div className="flex flex-wrap items-center gap-2">
            {picksLoadStatus === 'loaded' ? (
              <>
                <p className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                  {displayedPicks.length}/{visibleHardCap} visibles · {apiPicks.length} en pool
                </p>
                <span className="rounded-full bg-[#d1fae5] px-2.5 py-0.5 text-[10px] font-bold text-[#065f46]">
                  {standardCount} estándar
                </span>
                <span className="rounded-full bg-[#e9ddff] px-2.5 py-0.5 text-[10px] font-bold text-[#6d3bd7]">
                  {premiumCount} premium
                </span>
              </>
            ) : null}
          </div>
        }
      />

      <div className="rounded-xl border border-[#a4b4be]/20 bg-white/80 px-4 py-3">
        <VektorShortDisclaimer />
      </div>

      {import.meta.env.DEV ? (
        <div className="rounded-xl border border-amber-300/40 px-1 py-1">
          <VaultDevTools />
        </div>
      ) : null}

      {picksLoadStatus === 'loaded' && apiPicks.length > 0 && picksMessage ? (
        <div
          role="status"
          className="rounded-xl border border-[#b45309]/25 bg-[#fffbeb] px-4 py-3 text-sm text-[#78350f]"
        >
          <p className="font-semibold text-[#92400e]">Aviso del snapshot</p>
          <p className="mt-1 leading-relaxed">{picksMessage}</p>
        </div>
      ) : null}

      {picksLoadStatus === 'loaded' && apiPicks.length > 0 ? (
        <div className="space-y-4 rounded-xl border border-[#a4b4be]/20 bg-white/70 p-4 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between lg:gap-6">
            <div className="flex min-w-0 flex-col gap-2">
              <button
                type="button"
                disabled={apiPicks.length === 0}
                onClick={() => {
                  const r = regenerateVaultSlate()
                  if (!r.ok) {
                    showVaultToast(r.message.slice(0, 220))
                    return
                  }
                  showVaultToast(
                    `Ciclo ${r.cycle}/4 · ${r.poolSize} picks en pool · orden de cartelera actualizado (solo cliente, sin otro request).`,
                  )
                }}
                className="w-full max-w-xs rounded-lg border border-[#26343d]/20 bg-[#26343d] px-4 py-2.5 text-center text-sm font-bold text-white transition-colors hover:bg-[#1c2730] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                title="Rota el ciclo de franjas horarias sobre el pool ya traído en el GET (hasta 20); no vuelve a llamar al servidor."
              >
                Regenerar cartelera
              </button>
              <p className="text-[10px] leading-snug text-[#6e7d86]">
                <span className="font-semibold text-[#26343d]">
                  Total en pool (API):{' '}
                  <span className="font-mono tabular-nums">{apiPicks.length}</span>
                </span>
                . Un solo GET al abrir la estación trae el pool del día; «Regenerar» solo baraja
                el orden visible (ciclo 0–3 y franja local), hasta{' '}
                <span className="font-mono">{visibleHardCap}</span> tarjetas.
              </p>
            </div>
            <div
              className="min-w-0 font-mono text-[11px] leading-relaxed text-[#52616a]"
              role="status"
            >
              <span className="font-sans font-semibold text-[#26343d]">
                Cupo de tomas hoy:{' '}
              </span>
              estándar{' '}
              <span className="tabular-nums text-[#065f46]">
                {quota.standardRemaining}/{VAULT_DAILY_CAP_STANDARD}
              </span>{' '}
              restantes · premium{' '}
              <span className="tabular-nums text-[#6d3bd7]">
                {quota.premiumRemaining}/{VAULT_DAILY_CAP_PREMIUM}
              </span>{' '}
              restantes.
              <span className="mt-1 block text-[10px] text-[#6e7d86]">
                El desbloqueo premium (DP) no cuenta como toma hasta que pulses
                «Tomar pick». Límite alineado a reglas del protocolo (3+2 por día
                operativo).
              </span>
            </div>
          </div>
          {vaultPoolMeta ? (
            <p className="text-[10px] leading-snug text-[#6e7d86]">
              Pool en cliente:{' '}
              <span className="font-mono tabular-nums">{vaultPoolMeta.poolItemCount}</span> ítems
              (tope valor ≤{' '}
              {vaultPoolMeta.valuePoolUniverseMax != null ? (
                <span className="font-mono">{vaultPoolMeta.valuePoolUniverseMax}</span>
              ) : (
                '20'
              )}
              ). Grilla: hasta{' '}
              <span className="font-mono">{vaultPoolMeta.poolHardCap}</span> visibles · ciclo
              local{' '}
              <span className="font-mono">{vaultLocalSlateCycle}</span>/4.
              {vaultPoolMeta.poolBelowTarget
                ? ' Por debajo del objetivo: el CDM aportó menos eventos válidos.'
                : null}
            </p>
          ) : null}
          {vaultDaySnapshotMeta?.limitedCoverage ? (
            <p className="text-[10px] leading-snug text-[#92400e]">
              Cobertura baja en la ventana del día (&lt; 5 eventos futuros): el criterio puede
              depender de pocos partidos; no implica fallo de ingesta por sí sola (D-06-026 §4).
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {picksLoadStatus === 'loading' ? (
          <VaultLoadingState />
        ) : picksLoadStatus === 'error' ? (
          <VaultErrorState onRetry={() => void loadApiPicks()} />
        ) : (picksLoadStatus === 'empty' || (picksLoadStatus === 'loaded' && apiPicks.length === 0)) ? (
          <VaultEmptyState
            headline={emptyVaultCopy.headline}
            detail={emptyVaultCopy.detail}
            technicalHint={emptyVaultCopy.technicalHint}
            onRefresh={() => void loadApiPicks()}
          />
        ) : (
          displayedPicks.map((pick) => (
            <PickCard
              key={pick.id}
              pick={pick}
              pickTaken={isApiPickCommitted(pick)}
              premiumUnlocked={
                pick.accessTier === 'standard' ? true : pick.premiumUnlocked
              }
              disciplinePoints={disciplinePoints}
              onPremiumUnlock={(id) => void handlePremiumUnlock(id)}
              onTakePick={(id) => void handleTakePick(id)}
              takeBlockedByDailyQuota={takeBlockedByQuota(
                pick,
                isApiPickCommitted(pick),
              )}
            />
          ))
        )}
      </div>

      {/* US-FE-016: tour contextual de La Bóveda */}
      <ViewTourModal
        open={tourOpen}
        title={VAULT_TOUR.title}
        steps={VAULT_TOUR.steps}
        onComplete={handleTourComplete}
      />
    </section>
  )
}
