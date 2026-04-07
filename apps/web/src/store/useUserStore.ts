import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import type { OperatorProfileId } from '@/lib/diagnosticScoring'

/** DP que se acreditan UNA sola vez al completar el onboarding (US-FE-011). */
export const ONBOARDING_DP_GRANT = 250

export type UserStoreState = {
  isAuthenticated: boolean
  hasAcceptedContract: boolean
  operatorName: string | null
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
}

export type UserStoreActions = {
  setAuthenticated: (next: boolean) => void
  setHasAcceptedContract: (next: boolean) => void
  setOperatorName: (next: string | null) => void
  setDisciplinePoints: (next: number) => void
  setEquityCop: (next: number | null) => void
  incrementDisciplinePoints: (delta: number) => void
  /** POC: marca sesión autenticada; no resetea el contrato (sigue persistido tras logout). */
  initSession: () => void
  /** Solo cierra la sesión de autenticación; no borra DP, contrato, nombre ni equity persistidos. */
  endSession: () => void
  completeDiagnostic: (payload: {
    profile: OperatorProfileId
    systemIntegrity: number
  }) => void
  /**
   * US-FE-011: cierra fase A del onboarding y acredita los DP de bienvenida
   * UNA sola vez (guard interno: no repite el abono si `onboardingPhaseAComplete` es true).
   */
  completeOnboardingPhaseA: () => void
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
      disciplinePoints: 1250,
      equityCop: null,
      hasCompletedDiagnostic: false,
      operatorProfile: null,
      systemIntegrity: null,
      onboardingPhaseAComplete: false,
      hasSeenEconomyTour: false,
      setAuthenticated: (next) => set({ isAuthenticated: next }),
      setHasAcceptedContract: (next) => set({ hasAcceptedContract: next }),
      setOperatorName: (next) => set({ operatorName: next }),
      setDisciplinePoints: (next) => set({ disciplinePoints: next }),
      setEquityCop: (next) => set({ equityCop: next }),
      incrementDisciplinePoints: (delta) =>
        set((s) => ({ disciplinePoints: s.disciplinePoints + delta })),
      initSession: () => set({ isAuthenticated: true }),
      endSession: () => set({ isAuthenticated: false }),
      completeDiagnostic: (payload) =>
        set({
          hasCompletedDiagnostic: true,
          operatorProfile: payload.profile,
          systemIntegrity: payload.systemIntegrity,
        }),
      completeOnboardingPhaseA: () => {
        if (get().onboardingPhaseAComplete) return
        set((s) => ({
          onboardingPhaseAComplete: true,
          disciplinePoints: s.disciplinePoints + ONBOARDING_DP_GRANT,
        }))
        console.info(
          `[BT2] Onboarding fase A completado — abono único +${ONBOARDING_DP_GRANT} DP`,
        )
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
          disciplinePoints: 1250,
          equityCop: null,
          hasCompletedDiagnostic: false,
          operatorProfile: null,
          systemIntegrity: null,
          onboardingPhaseAComplete: false,
          hasSeenEconomyTour: false,
        }),
    }),
    {
      name: 'bt2_v2_user_state',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)

