import { vaultMockPicks } from '@/data/vaultMockPicks'
import { PickCard } from '@/components/vault/PickCard'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

/**
 * US-FE-003: rejilla de picks V2 (bóveda) con desbloqueo por DP.
 */
export default function VaultPage() {
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const unlockedPickIds = useVaultStore((s) => s.unlockedPickIds)
  const tryUnlockPick = useVaultStore((s) => s.tryUnlockPick)

  const unlockedSet = new Set(unlockedPickIds)

  return (
    <section aria-label="Bóveda de picks" className="space-y-6">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {vaultMockPicks.map((pick) => (
          <PickCard
            key={pick.id}
            pick={pick}
            isUnlocked={unlockedSet.has(pick.id)}
            disciplinePoints={disciplinePoints}
            onRequestUnlock={(id) => {
              tryUnlockPick(id)
            }}
          />
        ))}
      </div>
    </section>
  )
}
