/**
 * US-FE-025 (Sprint 04): Bóveda desde API real.
 * - apiPicks: picks del día desde GET /bt2/vault/picks.
 * - takenApiPicks: registro local de picks tomados (POST /bt2/picks).
 * - El tier "standard" equivale a "open" (libre sin DP).
 * - El tier "premium" requiere saldo DP ≥ unlockCostDp.
 * Se mantiene compatibilidad con picks mock (string IDs) para dev/tests.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { bt2FetchJson } from '@/lib/api'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import type { Bt2VaultPickOut, Bt2VaultPicksPageOut, Bt2PickRegisterBody, Bt2PickOut, Bt2TakenPickRecord } from '@/lib/bt2Types'
import { computeUnitValue } from '@/lib/treasuryMath'
import { useBankrollStore } from '@/store/useBankrollStore'

export const VAULT_UNLOCK_COST_DP = 50

export type VaultUnlockResult =
  | { ok: true }
  | {
      ok: false
      reason:
        | 'insufficient_dp'
        | 'already_unlocked'
        | 'station_locked'
        | 'api_error'
        | 'no_event_id'
    }

export type VaultLoadStatus = 'idle' | 'loading' | 'loaded' | 'empty' | 'error'
export type SessionOpenStatus = 'idle' | 'opening' | 'open' | 'error'

export type VaultStoreState = {
  /** Mock unlock IDs (Sprint 01 compat — string pick IDs). */
  unlockedPickIds: string[]
  /** Picks del día desde API (US-FE-025). */
  apiPicks: Bt2VaultPickOut[]
  /** Picks tomados vía POST /bt2/picks (US-FE-025). */
  takenApiPicks: Bt2TakenPickRecord[]
  /** Estado de carga de picks. */
  picksLoadStatus: VaultLoadStatus
  /** Mensaje informativo del API (ej: "No hay eventos hoy"). */
  picksMessage: string | null
  /** Estado de apertura de sesión operativa. */
  sessionOpenStatus: SessionOpenStatus
}

export type VaultStoreActions = {
  /** Compatibilidad Sprint 01: verifica si un pick (string ID) está desbloqueado. */
  isUnlocked: (pickId: string) => boolean
  /** Compatibilidad Sprint 01: intenta desbloquear un pick mock. */
  tryUnlockPick: (pickId: string) => VaultUnlockResult
  /**
   * US-FE-025: abre sesión operativa (POST /bt2/session/open)
   * y luego carga picks del día (GET /bt2/vault/picks).
   */
  loadApiPicks: () => Promise<void>
  /**
   * US-FE-025: "tomar" un pick de la API.
   * Para tier standard: simplemente registra el pick en bt2_picks (sin coste DP).
   * Para tier premium: verifica DP y luego registra.
   */
  takeApiPick: (vaultPick: Bt2VaultPickOut) => Promise<VaultUnlockResult>
  /** Devuelve el bt2PickId tomado para un vault pick dado (o null si no existe). */
  getApiPickRecord: (vaultPickId: string) => Bt2TakenPickRecord | null
  /** Solo tests / reset global */
  reset: () => void
}

export type VaultStore = VaultStoreState & VaultStoreActions

const initial: VaultStoreState = {
  unlockedPickIds: [],
  apiPicks: [],
  takenApiPicks: [],
  picksLoadStatus: 'idle',
  picksMessage: null,
  sessionOpenStatus: 'idle',
}

export const useVaultStore = create<VaultStore>()(
  persist(
    (set, get) => ({
      ...initial,

      // ── Sprint 01 compat ──────────────────────────────────────────────────
      isUnlocked: (pickId) => {
        // API picks (string like "dp-7"): check takenApiPicks
        const takenRecord = get().takenApiPicks.find((r) => r.vaultPickId === pickId)
        if (takenRecord) return true
        // API picks with standard tier: always unlocked
        const apiPick = get().apiPicks.find((p) => p.id === pickId)
        if (apiPick?.accessTier === 'standard') return true
        // Legacy string IDs in unlockedPickIds
        return get().unlockedPickIds.includes(pickId)
      },

      tryUnlockPick: (pickId) => {
        // Check API picks first
        const apiPick = get().apiPicks.find((p) => p.id === pickId)
        if (apiPick) {
          // Delegate to async takeApiPick (not called here for backwards compat)
          return { ok: false, reason: 'api_error' }
        }
        // Legacy mock flow
        if (useSessionStore.getState().isStationLocked()) {
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
        console.info(`[BT2] Pick desbloqueado (mock): ${pickId}`)
        return { ok: true }
      },

      // ── API flow (US-FE-025) ──────────────────────────────────────────────
      loadApiPicks: async () => {
        set({ picksLoadStatus: 'loading' })
        // 1. Abrir sesión si no está abierta
        set({ sessionOpenStatus: 'opening' })
        try {
          await bt2FetchJson('/bt2/session/open', { method: 'POST' })
          set({ sessionOpenStatus: 'open' })
        } catch (e) {
          const msg = e instanceof Error ? e.message : ''
          if (msg.includes('409')) {
            // Sesión ya abierta: OK
            set({ sessionOpenStatus: 'open' })
          } else {
            console.warn('[BT2] session/open error:', msg)
            set({ sessionOpenStatus: 'error' })
          }
        }
        // 2. Cargar picks
        try {
          const data = await bt2FetchJson<Bt2VaultPicksPageOut>('/bt2/vault/picks')
          if (!data.picks.length) {
            set({
              apiPicks: [],
              picksLoadStatus: 'empty',
              picksMessage: data.message ?? 'No hay picks disponibles hoy.',
            })
          } else {
            set({
              apiPicks: data.picks,
              picksLoadStatus: 'loaded',
              picksMessage: data.message ?? null,
            })
          }
        } catch (e) {
          console.error('[BT2] vault/picks error:', e)
          set({ picksLoadStatus: 'error', picksMessage: null })
        }
      },

      takeApiPick: async (vaultPick) => {
        // Ya tomado previamente
        const existing = get().takenApiPicks.find((r) => r.vaultPickId === vaultPick.id)
        if (existing) return { ok: false, reason: 'already_unlocked' }

        // Verificar estación
        if (useSessionStore.getState().isStationLocked()) {
          return { ok: false, reason: 'station_locked' }
        }

        // Verificar DP para premium
        if (vaultPick.accessTier === 'premium') {
          const dp = useUserStore.getState().disciplinePoints
          const cost = vaultPick.unlockCostDp || VAULT_UNLOCK_COST_DP
          if (dp < cost) {
            return { ok: false, reason: 'insufficient_dp' }
          }
        }

        if (!vaultPick.eventId) {
          return { ok: false, reason: 'no_event_id' }
        }

        // Construir stake
        const bankroll = useBankrollStore.getState().confirmedBankrollCop
        const stakePct = useBankrollStore.getState().selectedStakePct
        const stakeUnits = computeUnitValue(bankroll, stakePct)

        const body: Bt2PickRegisterBody = {
          event_id: vaultPick.eventId,
          market: vaultPick.marketClass,
          selection: vaultPick.selectionSummaryEs,
          odds_accepted: vaultPick.suggestedDecimalOdds,
          stake_units: stakeUnits > 0 ? stakeUnits : 1,
        }

        try {
          const res = await bt2FetchJson<Bt2PickOut>('/bt2/picks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })

          // Deducir DP para premium (local optimista; BE no registra aún en dp_ledger).
          // T-121 (US-FE-030): reconciliar con servidor tras la deducción local para
          // mantener el chip de DP alineado con la BD.
          // DECISIONES.md D-04-FE-003: gap hasta que BE implemente pick_premium_unlock en ledger.
          if (vaultPick.accessTier === 'premium') {
            const cost = vaultPick.unlockCostDp || VAULT_UNLOCK_COST_DP
            useUserStore.getState().incrementDisciplinePoints(-cost)
            console.info(`[BT2] Pick premium desbloqueado: ${vaultPick.id} · -${cost} DP (local)`)
            void useUserStore.getState().syncDpBalance()
          }

          const record: Bt2TakenPickRecord = {
            vaultPickId: vaultPick.id,
            bt2PickId: res.pick_id,
            eventId: vaultPick.eventId,
            market: res.market,
            selection: res.selection,
            oddsAccepted: res.odds_accepted,
            stakeUnits: res.stake_units,
            openedAt: res.opened_at,
            eventLabel: vaultPick.eventLabel,
          }

          set((s) => ({ takenApiPicks: [...s.takenApiPicks, record] }))
          console.info(`[BT2] Pick API registrado: ${vaultPick.id} → bt2PickId=${res.pick_id}`)
          return { ok: true }
        } catch (e) {
          console.error('[BT2] takeApiPick error:', e)
          return { ok: false, reason: 'api_error' }
        }
      },

      getApiPickRecord: (vaultPickId) => {
        return get().takenApiPicks.find((r) => r.vaultPickId === vaultPickId) ?? null
      },

      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_vault',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
