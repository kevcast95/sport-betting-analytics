import type { Bt2SettleOut } from '@/lib/bt2Types'

/**
 * Normaliza POST /bt2/picks/{id}/settle: FastAPI puede serializar snake_case;
 * proxies o versiones futuras podrían usar camelCase.
 */
export function parseBt2SettleOut(raw: unknown): Bt2SettleOut | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  const pickId = Number(o.pick_id ?? o.pickId)
  const status = String(o.status ?? '')
  const pnl = Number(o.pnl_units ?? o.pnlUnits)
  const bankrollRaw = o.bankroll_after_units ?? o.bankrollAfterUnits
  let bankrollAfter: number | null = null
  if (bankrollRaw != null && bankrollRaw !== '') {
    const n = Number(bankrollRaw)
    if (Number.isFinite(n)) bankrollAfter = n
  }
  const earnedRaw = o.earned_dp ?? o.earnedDp
  let earnedDp = 0
  if (earnedRaw != null && earnedRaw !== '') {
    const n = Number(earnedRaw)
    if (Number.isFinite(n)) earnedDp = n
  }

  let dpBalanceAfter: number | null = null
  const dpRaw = o.dp_balance_after ?? o.dpBalanceAfter
  if (dpRaw != null && dpRaw !== '') {
    const n = Number(dpRaw)
    if (Number.isFinite(n)) dpBalanceAfter = n
  }

  const settlementRaw = o.settlement_source ?? o.settlementSource
  const settlementSource =
    settlementRaw != null && settlementRaw !== ''
      ? String(settlementRaw)
      : undefined

  if (!Number.isFinite(pickId) || !Number.isFinite(pnl)) return null
  return {
    pick_id: pickId,
    status,
    pnl_units: pnl,
    bankroll_after_units: bankrollAfter,
    earned_dp: earnedDp,
    dp_balance_after: dpBalanceAfter,
    settlement_source: settlementSource,
  }
}
