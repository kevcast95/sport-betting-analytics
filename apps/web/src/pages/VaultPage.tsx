/**
 * US-FE-003: rejilla de picks V2 (bóveda) con desbloqueo por DP.
 * US-FE-016 (T-048): tour contextual de primera visita + botón de ayuda.
 * US-FE-025 (Sprint 04): picks desde GET /bt2/vault/picks; fallback mock en dev.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { PickCard } from '@/components/vault/PickCard'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import type { Bt2VaultPickOut } from '@/lib/bt2Types'

const VAULT_TOUR = getTourScript('vault')!

function VaultEmptyState({ message }: { message: string | null }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-[#a4b4be]/20 bg-[#f6fafe] py-16 text-center">
      <p className="mb-2 text-lg font-bold text-[#26343d]">Sin señales disponibles</p>
      <p className="max-w-sm text-sm text-[#52616a]">
        {message ?? 'El sistema actualiza la cartelera cada mañana. Vuelve pronto.'}
      </p>
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
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const onboardingPhaseAComplete = useUserStore((s) => s.onboardingPhaseAComplete)

  const apiPicks = useVaultStore((s) => s.apiPicks)
  const picksLoadStatus = useVaultStore((s) => s.picksLoadStatus)
  const picksMessage = useVaultStore((s) => s.picksMessage)
  const takenApiPicks = useVaultStore((s) => s.takenApiPicks)
  const unlockedPickIds = useVaultStore((s) => s.unlockedPickIds)
  const loadApiPicks = useVaultStore((s) => s.loadApiPicks)
  const takeApiPick = useVaultStore((s) => s.takeApiPick)
  const tryUnlockPick = useVaultStore((s) => s.tryUnlockPick)

  // US-FE-016: tour de primera visita — solo tras onboarding completo
  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('vault'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  // Cargar picks de API al montar
  useEffect(() => {
    if (picksLoadStatus === 'idle') {
      void loadApiPicks()
    }
  }, [picksLoadStatus, loadApiPicks])

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

  // Determina si un pick API está desbloqueado (standard = siempre, premium = si tomado)
  const isApiPickUnlocked = useCallback(
    (pick: Bt2VaultPickOut) => {
      if (pick.accessTier === 'standard') return true
      return takenApiPicks.some((r) => r.vaultPickId === pick.id)
    },
    [takenApiPicks],
  )

  // Para compatibilidad con picks mock (string IDs)
  const isMockPickUnlocked = useCallback(
    (id: string) => unlockedPickIds.includes(id),
    [unlockedPickIds],
  )
  void isMockPickUnlocked // evitar lint unused

  // Conteo por tier
  const standardCount = useMemo(
    () => apiPicks.filter((p) => p.accessTier === 'standard').length,
    [apiPicks],
  )
  const premiumCount = useMemo(
    () => apiPicks.filter((p) => p.accessTier === 'premium').length,
    [apiPicks],
  )

  const handleRequestUnlock = useCallback(
    async (pickId: string) => {
      const apiPick = apiPicks.find((p) => p.id === pickId)
      if (apiPick) {
        await takeApiPick(apiPick)
      } else {
        tryUnlockPick(pickId)
      }
    },
    [apiPicks, takeApiPick, tryUnlockPick],
  )

  return (
    <section aria-label="Bóveda de picks" className="space-y-6">
      {/* Cabecera con conteo standard/premium y botón de ayuda */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {picksLoadStatus === 'loaded' ? (
            <>
              <p className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                {apiPicks.length} señales disponibles
              </p>
              <span className="rounded-full bg-[#d1fae5] px-2.5 py-0.5 text-[10px] font-bold text-[#065f46]">
                {standardCount} estándar
              </span>
              <span className="rounded-full bg-[#e9ddff] px-2.5 py-0.5 text-[10px] font-bold text-[#6d3bd7]">
                {premiumCount} premium
              </span>
            </>
          ) : (
            <p className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
              La Bóveda
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleForceShowTour}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#a4b4be]/30 bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] transition-colors hover:border-[#8B5CF6]/30 hover:text-[#8B5CF6]"
          title="Ver cómo funciona La Bóveda"
        >
          <span aria-hidden="true" className="text-[11px]">?</span>
          Cómo funciona
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {picksLoadStatus === 'loading' ? (
          <VaultLoadingState />
        ) : picksLoadStatus === 'error' ? (
          <VaultErrorState onRetry={() => void loadApiPicks()} />
        ) : (picksLoadStatus === 'empty' || (picksLoadStatus === 'loaded' && apiPicks.length === 0)) ? (
          <VaultEmptyState message={picksMessage} />
        ) : (
          apiPicks.map((pick) => (
            <PickCard
              key={pick.id}
              pick={pick}
              isUnlocked={isApiPickUnlocked(pick)}
              disciplinePoints={disciplinePoints}
              onRequestUnlock={(id) => void handleRequestUnlock(id)}
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
