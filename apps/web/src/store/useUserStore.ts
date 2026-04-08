import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import type { OperatorProfileId } from '@/lib/diagnosticScoring'
import {
  fetchJson,
  bt2FetchJson,
  setStoredJwt,
  clearStoredJwt,
} from '@/lib/api'
import type {
  Bt2AuthTokenResponse,
  Bt2MeResponse,
  Bt2DpBalanceOut,
  Bt2OnboardingPhaseACompleteOut,
} from '@/lib/bt2Types'

/**
 * DP del bono de fase A (copy UI). Debe coincidir con `ONBOARDING_PHASE_A_DP_GRANT`
 * en `apps/api/bt2_router.py`; la acreditación real es vía ledger en el servidor.
 */
export const ONBOARDING_DP_GRANT = 250

export type UserStoreState = {
  isAuthenticated: boolean
  hasAcceptedContract: boolean
  operatorName: string | null
  /** ID del usuario autenticado en BD (US-FE-026). */
  userId: string | null
  /** Email del usuario autenticado (US-FE-026). */
  email: string | null
  disciplinePoints: number
  equityCop: number | null
  hasCompletedDiagnostic: boolean
  operatorProfile: OperatorProfileId | null
  /** Integridad del sistema (0–1) tras diagnóstico; null si aún no completado. */
  systemIntegrity: number | null
  /**
   * US-FE-011: true si se mostró y cerró la pantalla de cierre de fase A
   * (resumen + abono único de DP). Persistido para no repetir el grant.
   */
  onboardingPhaseAComplete: boolean
  /**
   * US-FE-011: true si el operador completó (o saltó) el tour de economía DP
   * (fase B). Persistido para no mostrar de nuevo en cada sesión.
   */
  hasSeenEconomyTour: boolean
  /** Estado de la última operación auth (para feedback en UI). */
  authError: string | null
  authLoading: boolean
}

export type UserStoreActions = {
  setAuthenticated: (next: boolean) => void
  setHasAcceptedContract: (next: boolean) => void
  setOperatorName: (next: string | null) => void
  setDisciplinePoints: (next: number) => void
  setEquityCop: (next: number | null) => void
  incrementDisciplinePoints: (delta: number) => void
  /** US-FE-026: inicia sesión con credenciales reales contra el backend. */
  loginWithCredentials: (email: string, password: string) => Promise<void>
  /** US-FE-026: registra un usuario nuevo contra el backend. */
  registerWithCredentials: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>
  /** US-FE-026: refresca perfil desde GET /bt2/auth/me. */
  refreshMe: () => Promise<void>
  /** US-FE-026: sincroniza saldo DP desde GET /bt2/user/dp-balance. */
  syncDpBalance: () => Promise<boolean>
  /** US-FE-026: cierra sesión y limpia JWT + estado. */
  logoutAndClear: () => void
  /** POC (compatibilidad Sprint 01): marca sesión autenticada sin API. */
  initSession: () => void
  /** Solo cierra la sesión; no borra DP, contrato, nombre ni equity persistidos. */
  endSession: () => void
  completeDiagnostic: (payload: {
    profile: OperatorProfileId
    systemIntegrity: number
  }) => void
  /**
   * US-FE-011: cierra fase A; el bono +250 vive en `bt2_dp_ledger` (POST idempotente).
   */
  completeOnboardingPhaseA: () => Promise<{ ok: boolean }>
  /** US-FE-011: marca el tour de economía DP como visto/completado. */
  completeEconomyTour: () => void
  reset: () => void
}

export type UserStore = UserStoreState & UserStoreActions

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      hasAcceptedContract: false,
      operatorName: null,
      userId: null,
      email: null,
      disciplinePoints: 0,
      equityCop: null,
      hasCompletedDiagnostic: false,
      operatorProfile: null,
      systemIntegrity: null,
      onboardingPhaseAComplete: false,
      hasSeenEconomyTour: false,
      authError: null,
      authLoading: false,

      setAuthenticated: (next) => set({ isAuthenticated: next }),
      setHasAcceptedContract: (next) => set({ hasAcceptedContract: next }),
      setOperatorName: (next) => set({ operatorName: next }),
      setDisciplinePoints: (next) => set({ disciplinePoints: next ?? 0 }),
      setEquityCop: (next) => set({ equityCop: next }),
      incrementDisciplinePoints: (delta) =>
        set((s) => ({ disciplinePoints: (s.disciplinePoints ?? 0) + delta })),

      loginWithCredentials: async (email, password) => {
        set({ authLoading: true, authError: null })
        try {
          const res = await fetchJson<Bt2AuthTokenResponse>(
            '/bt2/auth/login',
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email: email.toLowerCase().trim(), password }),
            },
          )
          setStoredJwt(res.access_token)
          set({ isAuthenticated: true, authLoading: false, authError: null })
          await get().refreshMe()
        } catch (e) {
          const msg = e instanceof Error ? e.message : 'Error de autenticación'
          const userMsg = msg.includes('401')
            ? 'Credenciales incorrectas. Verifica tu correo y contraseña.'
            : `Error al conectar con el servidor: ${msg}`
          set({ authLoading: false, authError: userMsg, isAuthenticated: false })
          throw new Error(userMsg)
        }
      },

      registerWithCredentials: async (email, password, displayName) => {
        set({ authLoading: true, authError: null })
        try {
          const body: Record<string, string> = {
            email: email.toLowerCase().trim(),
            password,
          }
          if (displayName?.trim()) body.display_name = displayName.trim()

          const res = await fetchJson<Bt2AuthTokenResponse>(
            '/bt2/auth/register',
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(body),
            },
          )
          setStoredJwt(res.access_token)
          if (res.display_name) set({ operatorName: res.display_name })
          set({ isAuthenticated: true, authLoading: false, authError: null })
          await get().refreshMe()
        } catch (e) {
          const msg = e instanceof Error ? e.message : 'Error de registro'
          const userMsg = msg.includes('409')
            ? 'Este correo ya está registrado. Intenta iniciar sesión.'
            : `Error al registrar: ${msg}`
          set({ authLoading: false, authError: userMsg, isAuthenticated: false })
          throw new Error(userMsg)
        }
      },

      refreshMe: async () => {
        try {
          const me = await bt2FetchJson<Bt2MeResponse>('/bt2/auth/me')
          set({
            userId: me.user_id,
            email: me.email,
            operatorName: me.display_name || get().operatorName,
            isAuthenticated: true,
          })
        } catch (e) {
          const msg = e instanceof Error ? e.message : ''
          if (msg.startsWith('401 ')) {
            set({ isAuthenticated: false, userId: null, email: null })
          }
        }
      },

      syncDpBalance: async () => {
        try {
          const data = await bt2FetchJson<Bt2DpBalanceOut>('/bt2/user/dp-balance')
          const balance =
            typeof data.dp_balance === 'number' ? data.dp_balance : 0
          set({ disciplinePoints: balance })
          return true
        } catch {
          return false
        }
      },

      logoutAndClear: () => {
        clearStoredJwt()
        set({
          isAuthenticated: false,
          userId: null,
          email: null,
          authError: null,
        })
      },

      initSession: () => set({ isAuthenticated: true }),
      endSession: () => set({ isAuthenticated: false }),

      completeDiagnostic: (payload) =>
        set({
          hasCompletedDiagnostic: true,
          operatorProfile: payload.profile,
          systemIntegrity: payload.systemIntegrity,
        }),

      completeOnboardingPhaseA: async () => {
        if (get().onboardingPhaseAComplete) return { ok: true }
        try {
          const data = await bt2FetchJson<Bt2OnboardingPhaseACompleteOut>(
            '/bt2/user/onboarding-phase-a-complete',
            { method: 'POST' },
          )
          const balance =
            typeof data.dp_balance === 'number' ? data.dp_balance : 0
          set({
            onboardingPhaseAComplete: true,
            disciplinePoints: balance,
          })
          console.info(
            `[BT2] Onboarding fase A — ledger +${data.granted_dp ?? 0} DP · saldo ${balance}`,
          )
          return { ok: true }
        } catch (e) {
          console.warn(
            '[BT2] onboarding-phase-a-complete:',
            e instanceof Error ? e.message : e,
          )
          return { ok: false }
        }
      },

      completeEconomyTour: () => {
        set({ hasSeenEconomyTour: true })
        console.info('[BT2] Tour de economía DP completado')
      },

      reset: () =>
        set({
          isAuthenticated: false,
          hasAcceptedContract: false,
          operatorName: null,
          userId: null,
          email: null,
          disciplinePoints: 0,
          equityCop: null,
          hasCompletedDiagnostic: false,
          operatorProfile: null,
          systemIntegrity: null,
          onboardingPhaseAComplete: false,
          hasSeenEconomyTour: false,
          authError: null,
          authLoading: false,
        }),
    }),
    {
      name: 'bt2_v2_user_state',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
      // No persistir authError/authLoading (estado transitorio)
      partialize: (s) => ({
        isAuthenticated: s.isAuthenticated,
        hasAcceptedContract: s.hasAcceptedContract,
        operatorName: s.operatorName,
        userId: s.userId,
        email: s.email,
        disciplinePoints: s.disciplinePoints,
        equityCop: s.equityCop,
        hasCompletedDiagnostic: s.hasCompletedDiagnostic,
        operatorProfile: s.operatorProfile,
        systemIntegrity: s.systemIntegrity,
        onboardingPhaseAComplete: s.onboardingPhaseAComplete,
        hasSeenEconomyTour: s.hasSeenEconomyTour,
      }),
    },
  ),
)
