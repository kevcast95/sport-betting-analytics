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
  const earned = Number(o.earned_dp ?? o.earnedDp ?? 0)
  const dpAfter = Number(o.dp_balance_after ?? o.dpBalanceAfter ?? 0)
  if (!Number.isFinite(pickId) || !Number.isFinite(pnl)) return null
  return {
    pick_id: pickId,
    status,
    pnl_units: pnl,
    bankroll_after_units: bankrollAfter,
    earned_dp: Number.isFinite(earned) ? earned : 0,
    dp_balance_after: Number.isFinite(dpAfter) ? dpAfter : 0,
  }
}
