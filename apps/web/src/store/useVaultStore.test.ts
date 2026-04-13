import { describe, expect, it, vi } from 'vitest'
import * as api from '@/lib/api'
import {
  BT2_ERR_INSUFFICIENT_BANKROLL_STAKE,
  BT2_ERR_PICK_EVENT_KICKOFF_ELAPSED,
} from '@/lib/bt2VaultConstants'
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    bt2PostVaultPremiumUnlock: vi.fn(),
    bt2PostPickRegister: vi.fn(),
  }
})

describe('useVaultStore', () => {
  it('desbloquea pick, descuenta DP y registra observabilidad', () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => {})
    useUserStore.setState({ disciplinePoints: 200 })
    const r = useVaultStore.getState().tryUnlockPick('v2-p-001')
    expect(r).toEqual({ ok: true })
    expect(useUserStore.getState().disciplinePoints).toBe(
      200 - VAULT_UNLOCK_COST_DP,
    )
    expect(useVaultStore.getState().unlockedPickIds).toContain('v2-p-001')
    expect(log).toHaveBeenCalledWith(expect.stringContaining('[BT2] Pick desbloqueado'))
    log.mockRestore()
  })

  it('rechaza si DP insuficiente sin mutar listas', () => {
    useUserStore.setState({ disciplinePoints: VAULT_UNLOCK_COST_DP - 1 })
    const beforeIds = [...useVaultStore.getState().unlockedPickIds]
    const r = useVaultStore.getState().tryUnlockPick('v2-p-002')
    expect(r).toEqual({ ok: false, reason: 'insufficient_dp' })
    expect(useUserStore.getState().disciplinePoints).toBe(
      VAULT_UNLOCK_COST_DP - 1,
    )
    expect(useVaultStore.getState().unlockedPickIds).toEqual(beforeIds)
  })

  it('rechaza si ya estaba desbloqueado', () => {
    useUserStore.setState({ disciplinePoints: 500 })
    expect(useVaultStore.getState().tryUnlockPick('v2-p-003')).toEqual({
      ok: true,
    })
    const dp = useUserStore.getState().disciplinePoints
    const r = useVaultStore.getState().tryUnlockPick('v2-p-003')
    expect(r).toEqual({ ok: false, reason: 'already_unlocked' })
    expect(useUserStore.getState().disciplinePoints).toBe(dp)
  })

  it('T-169: invalida fetch cuando operatingDayKey ≠ snapshot persistido', () => {
    useVaultStore.getState().reset()
    useVaultStore.setState({
      picksLoadStatus: 'loaded',
      vaultSnapshotOperatingDayKey: '2026-04-06',
      apiPicks: [],
    })
    useVaultStore.getState().invalidateVaultIfOperatingDayMismatch('2026-04-07')
    expect(useVaultStore.getState().picksLoadStatus).toBe('idle')
  })

  it('T-169: no invalida si el día coincide', () => {
    useVaultStore.getState().reset()
    useVaultStore.setState({
      picksLoadStatus: 'loaded',
      vaultSnapshotOperatingDayKey: '2026-04-06',
      apiPicks: [],
    })
    useVaultStore.getState().invalidateVaultIfOperatingDayMismatch('2026-04-06')
    expect(useVaultStore.getState().picksLoadStatus).toBe('loaded')
  })

  it('unlockPremiumVaultPick rechaza ítem no premium', async () => {
    useVaultStore.getState().reset()
    const p = {
      id: 'dp-x',
      accessTier: 'standard',
      premiumUnlocked: false,
      timeBand: 'afternoon',
    } as Bt2VaultPickOut
    useVaultStore.setState({ apiPicks: [p] })
    const r = await useVaultStore.getState().unlockPremiumVaultPick('dp-x')
    expect(r).toEqual({ ok: false, reason: 'not_premium' })
  })

  it('unlockPremiumVaultPick actualiza premiumUnlocked tras API OK', async () => {
    vi.mocked(api.bt2PostVaultPremiumUnlock).mockResolvedValue({
      ok: true,
      data: {
        vaultPickId: 'dp-99',
        premiumUnlocked: true,
        dpBalanceAfter: 200,
      },
    })
    useVaultStore.getState().reset()
    const p = {
      id: 'dp-99',
      accessTier: 'premium',
      premiumUnlocked: false,
      eventId: 1,
      marketClass: 'h2h',
      marketLabelEs: 'H2H',
      eventLabel: 'A vs B',
      titulo: 'Test',
      suggestedDecimalOdds: 2.0,
      edgeBps: 0,
      selectionSummaryEs: 'A',
      traduccionHumana: '',
      curvaEquidad: [],
      operatingDayKey: '2026-04-07',
      isAvailable: true,
      kickoffUtc: '',
      eventStatus: 'scheduled',
      externalSearchUrl: '',
      unlockCostDp: 50,
      timeBand: 'afternoon',
    } satisfies Bt2VaultPickOut
    useVaultStore.setState({ apiPicks: [p] })
    const r = await useVaultStore.getState().unlockPremiumVaultPick('dp-99')
    expect(r).toEqual({ ok: true })
    expect(
      useVaultStore.getState().apiPicks[0]?.premiumUnlocked,
    ).toBe(true)
  })

  it('takeApiPick — rechaza kickoff pasado en cliente sin POST', async () => {
    const post = vi.mocked(api.bt2PostPickRegister)
    post.mockClear()
    useVaultStore.getState().reset()
    useSessionStore.setState({ operatingDayKey: '2026-04-07' })
    useBankrollStore.setState({
      confirmedBankrollCop: 1_000_000,
      selectedStakePct: 2,
    })
    const p = {
      id: 'dp-old',
      accessTier: 'standard',
      premiumUnlocked: false,
      eventId: 1,
      marketClass: 'h2h',
      marketLabelEs: 'H2H',
      eventLabel: 'Old',
      titulo: 'T',
      suggestedDecimalOdds: 2.0,
      edgeBps: 0,
      selectionSummaryEs: 'A',
      traduccionHumana: '',
      curvaEquidad: [],
      operatingDayKey: '2026-04-07',
      isAvailable: true,
      kickoffUtc: '2020-01-01T12:00:00.000Z',
      eventStatus: 'scheduled',
      externalSearchUrl: '',
      unlockCostDp: 0,
      timeBand: 'morning',
    } satisfies Bt2VaultPickOut
    useVaultStore.setState({ apiPicks: [p], takenApiPicks: [] })
    const r = await useVaultStore.getState().takeApiPick(p)
    expect(r).toMatchObject({ ok: false, reason: 'kickoff_elapsed' })
    expect(post).not.toHaveBeenCalled()
  })

  it('takeApiPick — 422 pick_event_kickoff_elapsed → kickoff_elapsed', async () => {
    vi.mocked(api.bt2PostPickRegister).mockResolvedValue({
      ok: false,
      status: 422,
      bodyText: '',
      premiumInsufficient: null,
      message: 'El partido ya inició',
      errorCode: BT2_ERR_PICK_EVENT_KICKOFF_ELAPSED,
    })
    useVaultStore.getState().reset()
    useSessionStore.setState({ operatingDayKey: '2026-04-07' })
    useBankrollStore.setState({
      confirmedBankrollCop: 1_000_000,
      selectedStakePct: 2,
    })
    const p = {
      id: 'dp-k',
      accessTier: 'standard',
      premiumUnlocked: false,
      eventId: 99,
      marketClass: 'h2h',
      marketLabelEs: 'H2H',
      eventLabel: 'A vs B',
      titulo: 'T',
      suggestedDecimalOdds: 2.0,
      edgeBps: 0,
      selectionSummaryEs: 'A',
      traduccionHumana: '',
      curvaEquidad: [],
      operatingDayKey: '2026-04-07',
      isAvailable: true,
      kickoffUtc: '2099-01-01T00:00:00.000Z',
      eventStatus: 'scheduled',
      externalSearchUrl: '',
      unlockCostDp: 0,
      timeBand: 'evening',
    } satisfies Bt2VaultPickOut
    useVaultStore.setState({ apiPicks: [p], takenApiPicks: [] })
    const r = await useVaultStore.getState().takeApiPick(p)
    expect(r).toEqual({
      ok: false,
      reason: 'kickoff_elapsed',
      apiMessage: 'El partido ya inició',
    })
  })

  it('takeApiPick — 422 insufficient_bankroll_for_stake → insufficient_bankroll', async () => {
    const syncSpy = vi
      .spyOn(useBankrollStore.getState(), 'syncFromApi')
      .mockResolvedValue(undefined)
    vi.mocked(api.bt2PostPickRegister).mockResolvedValue({
      ok: false,
      status: 422,
      bodyText: '',
      premiumInsufficient: null,
      message: 'Saldo insuficiente para el stake',
      errorCode: BT2_ERR_INSUFFICIENT_BANKROLL_STAKE,
    })
    useVaultStore.getState().reset()
    useSessionStore.setState({ operatingDayKey: '2026-04-07' })
    useBankrollStore.setState({
      confirmedBankrollCop: 1_000_000,
      selectedStakePct: 2,
    })
    const p = {
      id: 'dp-br',
      accessTier: 'standard',
      premiumUnlocked: false,
      eventId: 101,
      marketClass: 'h2h',
      marketLabelEs: 'H2H',
      eventLabel: 'A vs B',
      titulo: 'T',
      suggestedDecimalOdds: 2.0,
      edgeBps: 0,
      selectionSummaryEs: 'A',
      traduccionHumana: '',
      curvaEquidad: [],
      operatingDayKey: '2026-04-07',
      isAvailable: true,
      kickoffUtc: '2099-01-01T00:00:00.000Z',
      eventStatus: 'scheduled',
      externalSearchUrl: '',
      unlockCostDp: 0,
      timeBand: 'evening',
    } satisfies Bt2VaultPickOut
    useVaultStore.setState({ apiPicks: [p], takenApiPicks: [] })
    const r = await useVaultStore.getState().takeApiPick(p)
    expect(r).toEqual({
      ok: false,
      reason: 'insufficient_bankroll',
      apiMessage: 'Saldo insuficiente para el stake',
    })
    expect(syncSpy).toHaveBeenCalled()
    syncSpy.mockRestore()
  })

  it('takeApiPick — OK con bankrollAfterUnits reconcilia bankroll local', async () => {
    vi.mocked(api.bt2PostPickRegister).mockResolvedValue({
      ok: true,
      data: {
        pick_id: 555,
        status: 'open',
        opened_at: '2026-04-07T12:00:00.000Z',
        stake_units: 20_000,
        odds_accepted: 2.0,
        event_label: 'A vs B',
        event_id: 102,
        market: 'h2h',
        selection: 'A',
        settled_at: null,
        pnl_units: null,
        earned_dp: null,
        bankrollAfterUnits: 980_000,
      },
    })
    useVaultStore.getState().reset()
    useSessionStore.setState({ operatingDayKey: '2026-04-07' })
    useBankrollStore.setState({
      confirmedBankrollCop: 1_000_000,
      selectedStakePct: 2,
    })
    const p = {
      id: 'dp-ok',
      accessTier: 'standard',
      premiumUnlocked: false,
      eventId: 102,
      marketClass: 'h2h',
      marketLabelEs: 'H2H',
      eventLabel: 'A vs B',
      titulo: 'T',
      suggestedDecimalOdds: 2.0,
      edgeBps: 0,
      selectionSummaryEs: 'A',
      traduccionHumana: '',
      curvaEquidad: [],
      operatingDayKey: '2026-04-07',
      isAvailable: true,
      kickoffUtc: '2099-01-01T00:00:00.000Z',
      eventStatus: 'scheduled',
      externalSearchUrl: '',
      unlockCostDp: 0,
      timeBand: 'evening',
    } satisfies Bt2VaultPickOut
    useVaultStore.setState({ apiPicks: [p], takenApiPicks: [] })
    const r = await useVaultStore.getState().takeApiPick(p)
    expect(r).toEqual({ ok: true })
    expect(useBankrollStore.getState().confirmedBankrollCop).toBe(980_000)
  })

  it('regenerateVaultSlate rota ciclo local sin llamar al API (baraja pool ya cargado)', () => {
    useVaultStore.getState().reset()
    const pick = {
      id: 'pool-1',
      accessTier: 'standard',
      premiumUnlocked: true,
      eventId: 1,
      marketClass: 'h2h',
      marketLabelEs: 'H2H',
      eventLabel: 'X vs Y',
      titulo: 'T',
      suggestedDecimalOdds: 2.0,
      edgeBps: 0,
      selectionSummaryEs: '1',
      traduccionHumana: '',
      curvaEquidad: [],
      operatingDayKey: '2026-04-09',
      isAvailable: true,
      kickoffUtc: '2099-06-01T18:00:00.000Z',
      eventStatus: 'scheduled',
      externalSearchUrl: '',
      unlockCostDp: 0,
      timeBand: 'afternoon',
    } satisfies Bt2VaultPickOut
    useVaultStore.setState({
      apiPicks: [pick],
      vaultLocalSlateCycle: 2,
      vaultPoolMeta: {
        poolTargetCount: 5,
        poolHardCap: 5,
        valuePoolUniverseMax: 20,
        poolItemCount: 1,
        vaultUniversePersistedCount: 1,
        slateBandCycle: 2,
        poolBelowTarget: false,
      },
      picksLoadStatus: 'loaded',
    })
    const r = useVaultStore.getState().regenerateVaultSlate()
    expect(r).toEqual({ ok: true, cycle: 3, poolSize: 1 })
    expect(useVaultStore.getState().vaultLocalSlateCycle).toBe(3)
    expect(useVaultStore.getState().apiPicks[0]?.id).toBe('pool-1')
  })
})
