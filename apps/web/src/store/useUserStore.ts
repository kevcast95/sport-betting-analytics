import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

type UserStoreState = {
  isAuthenticated: boolean
  hasAcceptedContract: boolean
  operatorName: string | null
  disciplinePoints: number
  equityCop: number | null
}

type UserStoreActions = {
  setAuthenticated: (next: boolean) => void
  setHasAcceptedContract: (next: boolean) => void
  setOperatorName: (next: string | null) => void
  setDisciplinePoints: (next: number) => void
  setEquityCop: (next: number | null) => void
  incrementDisciplinePoints: (delta: number) => void
  /**
   * Útil para POC: simula login/signup y deja el contrato como pendiente.
   */
  initSession: () => void
  reset: () => void
}

export const useUserStore = create<UserStoreState & UserStoreActions>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      hasAcceptedContract: false,
      operatorName: null,
      disciplinePoints: 1250,
      equityCop: null,
      setAuthenticated: (next) => set({ isAuthenticated: next }),
      setHasAcceptedContract: (next) => set({ hasAcceptedContract: next }),
      setOperatorName: (next) => set({ operatorName: next }),
      setDisciplinePoints: (next) => set({ disciplinePoints: next }),
      setEquityCop: (next) => set({ equityCop: next }),
      incrementDisciplinePoints: (delta) =>
        set((s) => ({ disciplinePoints: s.disciplinePoints + delta })),
      initSession: () =>
        set({
          isAuthenticated: true,
          hasAcceptedContract: false,
        }),
      reset: () =>
        set({
          isAuthenticated: false,
          hasAcceptedContract: false,
          operatorName: null,
          disciplinePoints: 1250,
          equityCop: null,
        }),
    }),
    {
      name: 'bt2_v2_user_state',
      storage: createJSONStorage(() => localStorage),
    },
  ),
)

