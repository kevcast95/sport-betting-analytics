import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import type { OperatorProfileId } from '@/lib/diagnosticScoring'

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
  reset: () => void
}

export type UserStore = UserStoreState & UserStoreActions

export const useUserStore = create<UserStore>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      hasAcceptedContract: false,
      operatorName: null,
      disciplinePoints: 1250,
      equityCop: null,
      hasCompletedDiagnostic: false,
      operatorProfile: null,
      systemIntegrity: null,
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
        }),
    }),
    {
      name: 'bt2_v2_user_state',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)

