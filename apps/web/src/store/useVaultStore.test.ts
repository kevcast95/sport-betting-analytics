import { describe, expect, it, vi } from 'vitest'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'

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
})
