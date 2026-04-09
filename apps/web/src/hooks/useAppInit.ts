/**
 * US-FE-027: hook de inicialización de app post-login.
 * Al detectar usuario autenticado con JWT, sincroniza stores desde API:
 * 1. GET /bt2/auth/me → userId, email, displayName
 * 2. GET /bt2/user/profile + /bt2/user/settings → bankroll, stakePct
 * 3. GET /bt2/user/dp-balance → disciplinePoints
 * 4. GET /bt2/session/day → operatingDayKey, graceActiveUntilIso
 */
import { useEffect, useRef } from 'react'
import { getStoredJwt } from '@/lib/api'
import { useUserStore } from '@/store/useUserStore'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'

export function useAppInit() {
  const isAuthenticated = useUserStore((s) => s.isAuthenticated)
  const userId = useUserStore((s) => s.userId)
  const refreshMe = useUserStore((s) => s.refreshMe)
  const syncDpBalance = useUserStore((s) => s.syncDpBalance)
  const syncFromApi = useBankrollStore((s) => s.syncFromApi)
  const hydrateFromApi = useSessionStore((s) => s.hydrateFromApi)
  const hydrateLedgerFromApi = useTradeStore((s) => s.hydrateLedgerFromApi)

  const syncedRef = useRef(false)

  useEffect(() => {
    const jwt = getStoredJwt()

    // Si hay JWT pero no isAuthenticated → intentar restaurar sesión
    if (jwt && !isAuthenticated) {
      void refreshMe()
      return
    }

    // Si autenticado y aún no sincronizado → sincronizar stores
    if (isAuthenticated && !syncedRef.current) {
      syncedRef.current = true
      void Promise.all([
        userId ? Promise.resolve() : refreshMe(),
        syncFromApi(),
        syncDpBalance(),
        hydrateFromApi(),
        hydrateLedgerFromApi(),
      ]).catch((e) => {
        console.warn('[BT2] useAppInit sync error:', e)
      })
    }

    // Reset sync flag al cerrar sesión
    if (!isAuthenticated) {
      syncedRef.current = false
    }
  }, [
    isAuthenticated,
    userId,
    refreshMe,
    syncDpBalance,
    syncFromApi,
    hydrateFromApi,
    hydrateLedgerFromApi,
  ])
}
