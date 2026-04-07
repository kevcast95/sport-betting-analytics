/**
 * US-FE-011: tests del flujo de onboarding en useUserStore.
 */
import { describe, expect, it, beforeEach } from 'vitest'
import { ONBOARDING_DP_GRANT, useUserStore } from '@/store/useUserStore'

beforeEach(() => {
  useUserStore.getState().reset()
})

describe('useUserStore (US-FE-011): onboarding fase A', () => {
  it('completeOnboardingPhaseA abona DP y marca la fase como completa', () => {
    const dpBefore = useUserStore.getState().disciplinePoints
    useUserStore.getState().completeOnboardingPhaseA()

    expect(useUserStore.getState().onboardingPhaseAComplete).toBe(true)
    expect(useUserStore.getState().disciplinePoints).toBe(dpBefore + ONBOARDING_DP_GRANT)
  })

  it('completeOnboardingPhaseA NO duplica el grant si ya fue completado', () => {
    useUserStore.getState().completeOnboardingPhaseA()
    const dpAfterFirst = useUserStore.getState().disciplinePoints

    useUserStore.getState().completeOnboardingPhaseA()
    expect(useUserStore.getState().disciplinePoints).toBe(dpAfterFirst)
  })

  it('completeEconomyTour marca el tour como visto', () => {
    expect(useUserStore.getState().hasSeenEconomyTour).toBe(false)
    useUserStore.getState().completeEconomyTour()
    expect(useUserStore.getState().hasSeenEconomyTour).toBe(true)
  })

  it('reset vuelve onboarding a estado inicial', () => {
    useUserStore.getState().completeOnboardingPhaseA()
    useUserStore.getState().completeEconomyTour()
    useUserStore.getState().reset()

    expect(useUserStore.getState().onboardingPhaseAComplete).toBe(false)
    expect(useUserStore.getState().hasSeenEconomyTour).toBe(false)
  })
})
