import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as api from '@/lib/api'
import { useTradeStore } from '@/store/useTradeStore'
import { useVaultStore } from '@/store/useVaultStore'

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return { ...actual, bt2FetchJson: vi.fn() }
})

beforeEach(() => {
  useTradeStore.getState().reset()
  useVaultStore.getState().reset()
  vi.mocked(api.bt2FetchJson).mockReset()
})

describe('useTradeStore.hydrateLedgerFromApi (US-FE-032)', () => {
  it('hidrata pick liquidado y enlaza vaultPickId', async () => {
    vi.mocked(api.bt2FetchJson).mockResolvedValueOnce({
      picks: [
        {
          pick_id: 42,
          status: 'won',
          opened_at: '2026-04-07T10:00:00Z',
          settled_at: '2026-04-07T12:00:00Z',
          stake_units: 100,
          odds_accepted: 2,
          pnl_units: 100,
          earned_dp: 10,
          event_id: 9,
          market: 'ML_HOME',
          selection: 'Local',
          event_label: 'A vs B',
        },
      ],
    })
    useVaultStore.setState({
      takenApiPicks: [
        {
          vaultPickId: 'dp-7',
          bt2PickId: 42,
          eventId: 9,
          market: 'ML_HOME',
          selection: 'Local',
          oddsAccepted: 2,
          stakeUnits: 100,
          openedAt: '2026-04-07T10:00:00Z',
          eventLabel: 'A vs B',
        },
      ],
    })

    await useTradeStore.getState().hydrateLedgerFromApi()

    const { ledger, settledPickIds } = useTradeStore.getState()
    expect(ledger).toHaveLength(1)
    expect(ledger[0].pickId).toBe('dp-7')
    expect(ledger[0].earnedDp).toBe(10)
    expect(ledger[0].outcome).toBe('PROFIT')
    expect(settledPickIds).toContain('dp-7')
  })

  it('pick abierto no entra al ledger', async () => {
    vi.mocked(api.bt2FetchJson).mockResolvedValueOnce({
      picks: [
        {
          pick_id: 1,
          status: 'open',
          opened_at: '2026-04-07T10:00:00Z',
          settled_at: null,
          stake_units: 50,
          odds_accepted: 1.9,
          pnl_units: null,
          earned_dp: null,
          event_id: 2,
          market: 'T',
          selection: 'x',
          event_label: 'C vs D',
        },
      ],
    })
    await useTradeStore.getState().hydrateLedgerFromApi()
    expect(useTradeStore.getState().ledger).toHaveLength(0)
  })

  it('lista vacía deja ledger vacío', async () => {
    vi.mocked(api.bt2FetchJson).mockResolvedValueOnce({ picks: [] })
    await useTradeStore.getState().hydrateLedgerFromApi()
    expect(useTradeStore.getState().ledger).toHaveLength(0)
  })

  it('pick reabierto en servidor (status open) elimina fila ledger persistida y settledPickIds', async () => {
    useTradeStore.setState({
      ledger: [
        {
          pickId: 'dp-7',
          outcome: 'PROFIT',
          reflection: 'Sincronizado desde el servidor',
          pnlCop: 100,
          stakeCop: 100,
          decimalCuota: 2,
          settledAt: '2026-04-07T12:00:00Z',
          earnedDp: 10,
          bt2PickId: 42,
        },
      ],
      settledPickIds: ['dp-7'],
    })
    vi.mocked(api.bt2FetchJson).mockResolvedValueOnce({
      picks: [
        {
          pick_id: 42,
          status: 'open',
          opened_at: '2026-04-07T10:00:00Z',
          settled_at: null,
          stake_units: 100,
          odds_accepted: 2,
          pnl_units: null,
          earned_dp: null,
          event_id: 9,
          market: 'ML_HOME',
          selection: 'Local',
          event_label: 'A vs B',
        },
      ],
    })
    useVaultStore.setState({
      takenApiPicks: [
        {
          vaultPickId: 'dp-7',
          bt2PickId: 42,
          eventId: 9,
          market: 'ML_HOME',
          selection: 'Local',
          oddsAccepted: 2,
          stakeUnits: 100,
          openedAt: '2026-04-07T10:00:00Z',
          eventLabel: 'A vs B',
        },
      ],
    })

    await useTradeStore.getState().hydrateLedgerFromApi()

    const { ledger, settledPickIds, openPickSelfRows } = useTradeStore.getState()
    expect(ledger).toHaveLength(0)
    expect(settledPickIds).not.toContain('dp-7')
    expect(openPickSelfRows.some((r) => r.bt2PickId === 42)).toBe(true)
  })
})
