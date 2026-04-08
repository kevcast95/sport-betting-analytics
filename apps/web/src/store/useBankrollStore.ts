import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { STAKE_PCT_DEFAULT } from '@/lib/treasuryMath'
import { bt2FetchJson } from '@/lib/api'

export type BankrollStoreState = {
  /** Capital confirmado en COP (0 = sin configurar; dispara modal automático). */
  confirmedBankrollCop: number
  /** Porcentaje de stake por unidad (0,25 – 5). */
  selectedStakePct: number
  /** ISO8601 del último commit del modal, o null. */
  lastCalculatedAt: string | null
}

export type BankrollStoreActions = {
  confirmTreasury: (bankrollCop: number, stakePct: number) => void
  /** US-FE-006: aplica PnL de liquidación al capital confirmado (mínimo 0). */
  applyBankrollDelta: (deltaCop: number) => void
  /** US-FE-007: alinea el capital confirmado al saldo real reportado en cierre. */
  reconcileToExchangeBalance: (cop: number) => void
  /**
   * US-FE-027: sincroniza bankroll desde API tras login.
   * Lee GET /bt2/user/profile y GET /bt2/user/settings.
   */
  syncFromApi: () => Promise<void>
  /**
   * US-FE-027: guarda bankroll en servidor vía POST /bt2/user/bankroll.
   */
  persistBankrollToApi: (cop: number, currency?: string) => Promise<void>
  /**
   * US-FE-027: guarda stake % en servidor vía PUT /bt2/user/settings.
   */
  persistStakePctToApi: (stakePct: number) => Promise<void>
  reset: () => void
}

export type BankrollStore = BankrollStoreState & BankrollStoreActions

const initial: BankrollStoreState = {
  confirmedBankrollCop: 0,
  selectedStakePct: STAKE_PCT_DEFAULT,
  lastCalculatedAt: null,
}

function logTreasuryConfirm(stakePct: number, bankrollCop: number) {
  const masked =
    bankrollCop <= 0
      ? '0'
      : `***${String(Math.round(bankrollCop)).slice(-3)}`
  console.info(
    `[BT2] Tesorería confirmada: unidad al ${stakePct}% del capital · monto≈${masked} COP`,
  )
}

export const useBankrollStore = create<BankrollStore>()(
  persist(
    (set) => ({
      ...initial,
      confirmTreasury: (bankrollCop, stakePct) => {
        if (!Number.isFinite(bankrollCop) || bankrollCop <= 0) return
        if (!Number.isFinite(stakePct)) return
        logTreasuryConfirm(stakePct, bankrollCop)
        set({
          confirmedBankrollCop: bankrollCop,
          selectedStakePct: stakePct,
          lastCalculatedAt: new Date().toISOString(),
        })
      },
      applyBankrollDelta: (deltaCop) => {
        if (!Number.isFinite(deltaCop)) return
        set((s) => ({
          confirmedBankrollCop: Math.max(0, s.confirmedBankrollCop + deltaCop),
        }))
      },
      reconcileToExchangeBalance: (cop) => {
        if (!Number.isFinite(cop) || cop < 0) return
        set({ confirmedBankrollCop: cop })
      },
      syncFromApi: async () => {
        try {
          const [profile, settings] = await Promise.all([
            bt2FetchJson<Record<string, unknown>>('/bt2/user/profile'),
            bt2FetchJson<Record<string, unknown>>('/bt2/user/settings'),
          ])
          // FastAPI sin response_model_by_alias devuelve snake_case.
          const bankrollRaw =
            profile.bankroll_amount ?? profile.bankrollAmount ?? 0
          const bankrollNum =
            typeof bankrollRaw === 'number' && Number.isFinite(bankrollRaw)
              ? bankrollRaw
              : Number(bankrollRaw)
          const bankrollCop = Number.isFinite(bankrollNum) ? bankrollNum : 0

          const stakeRaw =
            settings.risk_per_pick_pct ?? settings.riskPerPickPct
          const stakeNum =
            typeof stakeRaw === 'number' && Number.isFinite(stakeRaw)
              ? stakeRaw
              : Number(stakeRaw)
          const stakePct = Number.isFinite(stakeNum)
            ? stakeNum
            : STAKE_PCT_DEFAULT

          if (bankrollCop > 0 || stakePct !== STAKE_PCT_DEFAULT) {
            set({
              confirmedBankrollCop: bankrollCop,
              selectedStakePct: stakePct,
              lastCalculatedAt: new Date().toISOString(),
            })
            console.info(`[BT2] Bankroll sincronizado desde API: ${bankrollCop} COP · stake ${stakePct}%`)
          }
        } catch (e) {
          console.warn('[BT2] syncFromApi bankroll error:', e instanceof Error ? e.message : e)
        }
      },
      persistBankrollToApi: async (cop, currency = 'COP') => {
        try {
          await bt2FetchJson('/bt2/user/bankroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: cop, currency }),
          })
          console.info(`[BT2] Bankroll persistido en servidor: ${cop} ${currency}`)
        } catch (e) {
          console.warn('[BT2] persistBankrollToApi error:', e instanceof Error ? e.message : e)
        }
      },
      persistStakePctToApi: async (stakePct) => {
        try {
          await bt2FetchJson('/bt2/user/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ risk_per_pick_pct: stakePct }),
          })
          console.info(`[BT2] Stake % persistido en servidor: ${stakePct}%`)
        } catch (e) {
          console.warn('[BT2] persistStakePctToApi error:', e instanceof Error ? e.message : e)
        }
      },
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_bankroll',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
