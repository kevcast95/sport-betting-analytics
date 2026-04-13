import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

/** Claves `name` de los `persist` de Zustand (BT2 v2). */
export const BT2_PERSIST_STORAGE_KEYS = [
  'bt2_v2_user_state',
  'bt2_v2_trades',
  'bt2_v2_session',
  'bt2_v2_vault', // legado (persistía apiPicks; puede quedar basura)
  'bt2_v2_vault_v2',
  'bt2_v2_bankroll',
] as const

/**
 * Vuelve al flujo inicial: sin sesión, sin contrato, sin diagnóstico, ledger/vault/tesorería vacíos.
 * Útil para demos y pruebas manuales.
 */
export function resetAllBt2PersistedState(): void {
  useUserStore.getState().reset()
  useTradeStore.getState().reset()
  useSessionStore.getState().reset()
  useVaultStore.getState().reset()
  useBankrollStore.getState().reset()

  const storage = createBt2EncryptedLocalStorage()
  for (const key of BT2_PERSIST_STORAGE_KEYS) {
    storage.removeItem(key)
  }
}
