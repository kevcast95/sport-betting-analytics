import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { STAKE_PCT_DEFAULT } from '@/lib/treasuryMath'

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
    `[BT2] Treasury confirmado: stake=${stakePct}% · bankroll≈${masked} COP`,
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
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_bankroll',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
