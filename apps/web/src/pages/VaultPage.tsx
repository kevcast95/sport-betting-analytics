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
import {
  type Bt2VaultPickOut,
  bt2VaultPickUnlockEligible,
} from '@/lib/bt2Types'
import { isKickoffUtcInPast } from '@/lib/vaultKickoff'
import { reorderVaultPicksForBandCycle } from '@/lib/vaultTimeBand'
import { useTradeStore } from '@/store/useTradeStore'

const VAULT_TOUR = getTourScript('vault')!

/** Vista lista: 5 tarjetas por página para evitar scroll largo. */
const VAULT_PAGE_SIZE = 5

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
  const invalidateVaultIfOperatingDayMismatch = useVaultStore(
    (s) => s.invalidateVaultIfOperatingDayMismatch,
  )
  const operatingDayKey = useSessionStore((s) => s.operatingDayKey)
  const takeApiPick = useVaultStore((s) => s.takeApiPick)
  const unlockPremiumVaultPick = useVaultStore((s) => s.unlockPremiumVaultPick)
  const unlockStandardVaultPick = useVaultStore((s) => s.unlockStandardVaultPick)
  const setVaultPickCommitment = useVaultStore((s) => s.setVaultPickCommitment)
  const tryUnlockPick = useVaultStore((s) => s.tryUnlockPick)
  const hydrateLedgerFromApi = useTradeStore((s) => s.hydrateLedgerFromApi)
  const vaultDaySnapshotMeta = useVaultStore((s) => s.vaultDaySnapshotMeta)
  const vaultLocalSlateCycle = useVaultStore((s) => s.vaultLocalSlateCycle)

  const [vaultToast, setVaultToast] = useState<string | null>(null)
  const [vaultTab, setVaultTab] = useState<
    'disponibles' | 'liberados' | 'cerrados'
  >('disponibles')
  const [vaultListPage, setVaultListPage] = useState(1)

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

  /** Al entrar en bóveda: alinear ledger/settledPickIds con GET /bt2/picks (p. ej. tras reopen en servidor). */
  useEffect(() => {
    void hydrateLedgerFromApi()
  }, [hydrateLedgerFromApi])

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

  /** Pool interno (hasta 20) ordenado por franja; liberación limitada por topes en servidor. */
  const orderedPoolPicks = useMemo(
    () => reorderVaultPicksForBandCycle(apiPicks, userTimeZone, vaultLocalSlateCycle),
    [apiPicks, userTimeZone, vaultLocalSlateCycle],
  )

  const disponiblesPicks = useMemo(
    () =>
      orderedPoolPicks.filter((p) => {
        const past = isKickoffUtcInPast(p.kickoffUtc)
        return (
          p.contentUnlocked !== true && bt2VaultPickUnlockEligible(p) && !past
        )
      }),
    [orderedPoolPicks],
  )

  const liberadosPicks = useMemo(
    () => orderedPoolPicks.filter((p) => p.contentUnlocked === true),
    [orderedPoolPicks],
  )

  const cerradosPicks = useMemo(
    () =>
      orderedPoolPicks.filter((p) => {
        const past = isKickoffUtcInPast(p.kickoffUtc)
        return (
          p.contentUnlocked !== true &&
          (!bt2VaultPickUnlockEligible(p) || past)
        )
      }),
    [orderedPoolPicks],
  )

  const tabPicks =
    vaultTab === 'disponibles'
      ? disponiblesPicks
      : vaultTab === 'liberados'
        ? liberadosPicks
        : cerradosPicks

  useEffect(() => {
    setVaultListPage(1)
  }, [vaultTab])

  const vaultTotalPages = Math.max(1, Math.ceil(tabPicks.length / VAULT_PAGE_SIZE))
  const vaultSafePage = Math.min(vaultListPage, vaultTotalPages)

  useEffect(() => {
    setVaultListPage((p) => Math.min(p, vaultTotalPages))
  }, [vaultTotalPages])

  const pagedVaultPicks = useMemo(() => {
    const start = (vaultSafePage - 1) * VAULT_PAGE_SIZE
    return tabPicks.slice(start, start + VAULT_PAGE_SIZE)
  }, [tabPicks, vaultSafePage])

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

  const handleStandardUnlock = useCallback(
    async (pickId: string) => {
      const res = await unlockStandardVaultPick(pickId)
      if (res.ok) {
        showVaultToast('Contenido liberado. Podés marcar más tarde si apostaste.')
        return
      }
      if (res.reason === 'station_locked') {
        showVaultToast('Estación cerrada: no puedes liberar señales en este ciclo.')
        return
      }
      if (res.reason === 'already_unlocked') return
      if (res.reason === 'kickoff_elapsed') {
        showVaultToast(
          res.apiMessage ?? 'El partido ya inició; no puedes liberar esta señal.',
        )
        return
      }
      if (res.reason === 'pick_unavailable') {
        showVaultToast(
          res.apiMessage ??
            'Este ítem no está disponible para liberación. Actualizá la bóveda o revisá la pestaña Cerrados.',
        )
        return
      }
      showVaultToast(
        res.apiMessage?.slice(0, 220) ??
          'No se pudo liberar la señal. Revisá cupos del día o conexión.',
      )
    },
    [unlockStandardVaultPick, showVaultToast],
  )

  const handleCommitment = useCallback(
    async (pickId: string, c: 'taken' | 'not_taken') => {
      const r = await setVaultPickCommitment(pickId, c)
      if (r.ok) {
        showVaultToast(c === 'taken' ? 'Marcado como tomado.' : 'Marcado como no tomado.')
        return
      }
      showVaultToast(r.message.slice(0, 220))
    },
    [setVaultPickCommitment, showVaultToast],
  )

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
      if (res.reason === 'pick_unavailable') {
        showVaultToast(
          res.apiMessage ??
            'Este evento no admite desbloqueo en este momento. Revisá la pestaña Cerrados.',
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
        subtitle="Picks del día seleccionados con criterio, contexto y disciplina."
        onHelpClick={handleForceShowTour}
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
        <div
          role="tablist"
          aria-label="Secciones de la bóveda"
          className="flex flex-wrap gap-2 rounded-xl border border-[#a4b4be]/25 bg-[#f6fafe]/80 p-2"
        >
          {(
            [
              ['disponibles', 'Disponibles', disponiblesPicks.length],
              ['liberados', 'Liberados', liberadosPicks.length],
              ['cerrados', 'Cerrados', cerradosPicks.length],
            ] as const
          ).map(([key, label, count]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={vaultTab === key}
              onClick={() => setVaultTab(key)}
              className={`rounded-lg px-4 py-2 text-sm font-bold transition-colors ${
                vaultTab === key
                  ? 'bg-[#26343d] text-white'
                  : 'bg-white/90 text-[#52616a] hover:bg-[#eef4fa]'
              }`}
            >
              {label}{' '}
              <span className="font-mono text-xs tabular-nums opacity-90">({count})</span>
            </button>
          ))}
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
        ) : tabPicks.length === 0 ? (
          <div className="col-span-full rounded-xl border border-[#a4b4be]/20 bg-[#f6fafe] px-6 py-12 text-center text-sm text-[#52616a]">
            {vaultTab === 'disponibles'
              ? 'No hay picks disponibles para liberar en este momento.'
              : vaultTab === 'liberados'
                ? 'Todavía no liberaste ningún pick hoy.'
                : 'No hay picks cerrados por tiempo en esta vista.'}
          </div>
        ) : (
          <>
            {pagedVaultPicks.map((pick) => (
              <PickCard
                key={pick.id}
                pick={pick}
                vaultCardVariant={
                  vaultTab === 'disponibles'
                    ? 'disponible'
                    : vaultTab === 'liberados'
                      ? 'liberado'
                      : 'cerrado'
                }
                pickTaken={isApiPickCommitted(pick)}
                disciplinePoints={disciplinePoints}
                onPremiumUnlock={(id) => void handlePremiumUnlock(id)}
                onStandardUnlock={(id) => void handleStandardUnlock(id)}
                onCommitment={(id, c) => void handleCommitment(id, c)}
                onTakePick={(id) => void handleTakePick(id)}
              />
            ))}
            <nav
              className="col-span-full flex flex-col items-center gap-3 border-t border-[#a4b4be]/20 pt-6"
              aria-label="Paginación de la lista de picks"
            >
              <div className="flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  disabled={vaultSafePage <= 1}
                  onClick={() => setVaultListPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-[#26343d]/25 bg-white px-4 py-2 text-sm font-semibold text-[#26343d] transition-colors hover:bg-[#eef4fa] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ← Anterior
                </button>
                <p className="text-sm text-[#52616a]">
                  Página{' '}
                  <span className="font-mono tabular-nums font-bold text-[#26343d]">
                    {vaultSafePage}
                  </span>{' '}
                  de{' '}
                  <span className="font-mono tabular-nums">{vaultTotalPages}</span>
                  <span className="mx-2 text-[#a4b4be]">·</span>
                  <span className="font-mono text-xs tabular-nums text-[#6e7d86]">
                    {(vaultSafePage - 1) * VAULT_PAGE_SIZE + 1}–
                    {Math.min(vaultSafePage * VAULT_PAGE_SIZE, tabPicks.length)} de{' '}
                    {tabPicks.length}
                  </span>
                </p>
                <button
                  type="button"
                  disabled={vaultSafePage >= vaultTotalPages}
                  onClick={() =>
                    setVaultListPage((p) => Math.min(vaultTotalPages, p + 1))
                  }
                  className="rounded-lg border border-[#26343d]/25 bg-white px-4 py-2 text-sm font-semibold text-[#26343d] transition-colors hover:bg-[#eef4fa] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Siguiente →
                </button>
              </div>
            </nav>
          </>
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
