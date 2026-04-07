/**
 * US-FE-003: rejilla de picks V2 (bóveda) con desbloqueo por DP.
 * US-FE-016 (T-048): tour contextual de primera visita + botón de ayuda.
 * US-FE-023 (T-058): feed demo ~7 picks con tier open/premium.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { PickCard } from '@/components/vault/PickCard'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { vaultMockPicks } from '@/data/vaultMockPicks'
import { useTourStore } from '@/store/useTourStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

const VAULT_TOUR = getTourScript('vault')!

export default function VaultPage() {
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const onboardingPhaseAComplete = useUserStore((s) => s.onboardingPhaseAComplete)
  const unlockedPickIds = useVaultStore((s) => s.unlockedPickIds)
  const tryUnlockPick = useVaultStore((s) => s.tryUnlockPick)

  // US-FE-016: tour de primera visita — solo tras onboarding completo
  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('vault'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

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

  // Derivar isUnlocked localmente — leer estado crudo, no llamar get() en selector
  const isPickUnlocked = useCallback(
    (id: string) => {
      const p = vaultMockPicks.find((x) => x.id === id)
      if (p?.accessTier === 'open') return true
      return unlockedPickIds.includes(id)
    },
    [unlockedPickIds],
  )

  // US-FE-023: conteo open / premium para cabecera
  const openCount = useMemo(
    () => vaultMockPicks.filter((p) => p.accessTier === 'open').length,
    [],
  )
  const premiumCount = useMemo(
    () => vaultMockPicks.filter((p) => p.accessTier === 'premium').length,
    [],
  )

  return (
    <section aria-label="Bóveda de picks" className="space-y-6">
      {/* Cabecera con conteo open/premium (US-FE-023) y botón de ayuda */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
            {vaultMockPicks.length} señales disponibles
          </p>
          <span className="rounded-full bg-[#d1fae5] px-2.5 py-0.5 text-[10px] font-bold text-[#065f46]">
            {openCount} abiertas
          </span>
          <span className="rounded-full bg-[#e9ddff] px-2.5 py-0.5 text-[10px] font-bold text-[#6d3bd7]">
            {premiumCount} premium
          </span>
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
        {vaultMockPicks.map((pick) => (
          <PickCard
            key={pick.id}
            pick={pick}
            isUnlocked={isPickUnlocked(pick.id)}
            disciplinePoints={disciplinePoints}
            onRequestUnlock={(id) => {
              tryUnlockPick(id)
            }}
          />
        ))}
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
