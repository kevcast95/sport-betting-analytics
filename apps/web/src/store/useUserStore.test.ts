/**
 * US-FE-011: tests del flujo de onboarding en useUserStore.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { bt2FetchJson } from '@/lib/api'
import { ONBOARDING_DP_GRANT, useUserStore } from '@/store/useUserStore'

beforeEach(async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  vi.mocked(bt2FetchJson).mockReset()
  vi.mocked(bt2FetchJson).mockImplementation(actual.bt2FetchJson)
  useUserStore.getState().reset()
})

describe('useUserStore (US-FE-011): onboarding fase A', () => {
  it('completeOnboardingPhaseA sincroniza DP desde API y marca la fase como completa', async () => {
    vi.mocked(bt2FetchJson).mockResolvedValueOnce({
      dp_balance: ONBOARDING_DP_GRANT,
      granted_dp: ONBOARDING_DP_GRANT,
    })

    const r = await useUserStore.getState().completeOnboardingPhaseA()

    expect(r.ok).toBe(true)
    expect(useUserStore.getState().onboardingPhaseAComplete).toBe(true)
    expect(useUserStore.getState().disciplinePoints).toBe(ONBOARDING_DP_GRANT)
    expect(bt2FetchJson).toHaveBeenCalledWith(
      '/bt2/user/onboarding-phase-a-complete',
      { method: 'POST' },
    )
  })

  it('completeOnboardingPhaseA NO llama API si ya fue completado', async () => {
    vi.mocked(bt2FetchJson).mockResolvedValueOnce({
      dp_balance: ONBOARDING_DP_GRANT,
      granted_dp: ONBOARDING_DP_GRANT,
    })
    await useUserStore.getState().completeOnboardingPhaseA()
    const dpAfterFirst = useUserStore.getState().disciplinePoints

    const r = await useUserStore.getState().completeOnboardingPhaseA()
    expect(r.ok).toBe(true)
    expect(useUserStore.getState().disciplinePoints).toBe(dpAfterFirst)
    expect(bt2FetchJson).toHaveBeenCalledTimes(1)
  })

  it('completeEconomyTour marca el tour como visto', () => {
    expect(useUserStore.getState().hasSeenEconomyTour).toBe(false)
    useUserStore.getState().completeEconomyTour()
    expect(useUserStore.getState().hasSeenEconomyTour).toBe(true)
  })

  it('reset vuelve onboarding a estado inicial', async () => {
    vi.mocked(bt2FetchJson).mockResolvedValueOnce({
      dp_balance: ONBOARDING_DP_GRANT,
      granted_dp: ONBOARDING_DP_GRANT,
    })
    await useUserStore.getState().completeOnboardingPhaseA()
    useUserStore.getState().completeEconomyTour()
    useUserStore.getState().reset()

    expect(useUserStore.getState().onboardingPhaseAComplete).toBe(false)
    expect(useUserStore.getState().hasSeenEconomyTour).toBe(false)
  })
})
