import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'

export type VaultUnlockResult =
  | { ok: true }
  | {
      ok: false
      reason:
        | 'insufficient_dp'
        | 'already_unlocked'
        | 'station_locked'
    }

export type VaultStoreState = {
  unlockedPickIds: string[]
}

export type VaultStoreActions = {
  isUnlocked: (pickId: string) => boolean
  tryUnlockPick: (pickId: string) => VaultUnlockResult
  /** Solo tests / reset global */
  reset: () => void
}

export type VaultStore = VaultStoreState & VaultStoreActions

const initial: VaultStoreState = {
  unlockedPickIds: [],
}

export const useVaultStore = create<VaultStore>()(
  persist(
    (set, get) => ({
      ...initial,
      isUnlocked: (pickId) => get().unlockedPickIds.includes(pickId),
      tryUnlockPick: (pickId) => {
        if (useSessionStore.getState().isStationLocked()) {
          console.warn(
            `[BT2] Bóveda bloqueada: estación cerrada hasta fin de ciclo.`,
          )
          return { ok: false, reason: 'station_locked' }
        }
        if (get().unlockedPickIds.includes(pickId)) {
          return { ok: false, reason: 'already_unlocked' }
        }
        const dp = useUserStore.getState().disciplinePoints
        if (dp < VAULT_UNLOCK_COST_DP) {
          return { ok: false, reason: 'insufficient_dp' }
        }
        useUserStore.getState().incrementDisciplinePoints(-VAULT_UNLOCK_COST_DP)
        set((s) => ({
          unlockedPickIds: s.unlockedPickIds.includes(pickId)
            ? s.unlockedPickIds
            : [...s.unlockedPickIds, pickId],
        }))
        console.info(`[BT2] Pick desbloqueado: ${pickId}`)
        return { ok: true }
      },
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_vault',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
