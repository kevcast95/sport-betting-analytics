import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { vaultMockPicks } from '@/data/vaultMockPicks'
import type { SettlementOutcome } from '@/lib/settlementPnL'
import { computeSettlementPnlCop } from '@/lib/settlementPnL'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

const SETTLEMENT_DP_REWARD = 25

export type LedgerRow = {
  pickId: string
  /** US-FE-008: protocolo CDM (clase de mercado). */
  marketClass?: string
  titulo?: string
  outcome: SettlementOutcome
  reflection: string
  pnlCop: number
  stakeCop: number
  decimalCuota: number
  settledAt: string
  /** +25 DP por liquidación (US-FE-006). */
  earnedDp?: number
}

export type FinalizeSettlementResult =
  | { ok: true }
  | {
      ok: false
      reason:
        | 'already_settled'
        | 'pick_locked'
        | 'invalid_reflection'
        | 'invalid_amounts'
        | 'station_locked'
    }

export type TradeStoreState = {
  settledPickIds: string[]
  ledger: LedgerRow[]
}

export type TradeStoreActions = {
  isSettled: (pickId: string) => boolean
  finalizeSettlement: (input: {
    pickId: string
    outcome: SettlementOutcome
    reflection: string
    stakeCop: number
    decimalCuota: number
  }) => FinalizeSettlementResult
  reset: () => void
}

export type TradeStore = TradeStoreState & TradeStoreActions

const initial: TradeStoreState = {
  settledPickIds: [],
  ledger: [],
}

export const useTradeStore = create<TradeStore>()(
  persist(
    (set, get) => ({
      ...initial,
      isSettled: (pickId) => get().settledPickIds.includes(pickId),
      finalizeSettlement: (input) => {
        if (useSessionStore.getState().isStationLocked()) {
          return { ok: false, reason: 'station_locked' }
        }
        const reflection = input.reflection.trim()
        if (reflection.length < 10) {
          return { ok: false, reason: 'invalid_reflection' }
        }
        if (get().settledPickIds.includes(input.pickId)) {
          return { ok: false, reason: 'already_settled' }
        }
        if (!useVaultStore.getState().isUnlocked(input.pickId)) {
          return { ok: false, reason: 'pick_locked' }
        }
        const pnl = computeSettlementPnlCop(
          input.stakeCop,
          input.decimalCuota,
          input.outcome,
        )
        if (!Number.isFinite(pnl)) {
          return { ok: false, reason: 'invalid_amounts' }
        }
        const meta = vaultMockPicks.find((p) => p.id === input.pickId)
        const row: LedgerRow = {
          pickId: input.pickId,
          marketClass: meta?.marketClass ?? 'CDM',
          titulo: meta?.titulo ?? input.pickId,
          outcome: input.outcome,
          reflection,
          pnlCop: pnl,
          stakeCop: input.stakeCop,
          decimalCuota: input.decimalCuota,
          settledAt: new Date().toISOString(),
          earnedDp: SETTLEMENT_DP_REWARD,
        }
        useBankrollStore.getState().applyBankrollDelta(pnl)
        useUserStore.getState().incrementDisciplinePoints(SETTLEMENT_DP_REWARD)
        set((s) => ({
          settledPickIds: [...s.settledPickIds, input.pickId],
          ledger: [...s.ledger, row],
        }))
        console.info(
          `[BT2] Liquidación archivada en ledger: ${input.pickId} · PnL ${pnl} COP · +${SETTLEMENT_DP_REWARD} DP`,
        )
        return { ok: true }
      },
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_trades',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
