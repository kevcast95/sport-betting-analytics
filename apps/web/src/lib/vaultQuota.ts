/**
 * Sprint 05.2 — cupo diario 3 estándar + 2 premium (D-05.2-002 §5).
 * Solo cuenta **tomas** (POST /bt2/picks), no desbloqueos premium aislados.
 */
import type { Bt2TakenPickRecord, Bt2VaultPickOut } from '@/lib/bt2Types'

export const VAULT_DAILY_CAP_STANDARD = 3
export const VAULT_DAILY_CAP_PREMIUM = 2

export type VaultQuotaSnapshot = {
  standardTaken: number
  premiumTaken: number
  standardRemaining: number
  premiumRemaining: number
  atStandardCap: boolean
  atPremiumCap: boolean
}

function tierForRecord(
  r: Bt2TakenPickRecord,
  sessionDay: string | null,
  apiPicks: Bt2VaultPickOut[],
): 'standard' | 'premium' | null {
  if (!sessionDay) return null
  if (r.operatingDayKey != null && r.operatingDayKey !== sessionDay) return null
  if (r.accessTier === 'standard' || r.accessTier === 'premium') {
    return r.accessTier
  }
  const v = apiPicks.find((p) => p.id === r.vaultPickId)
  if (!v || v.operatingDayKey !== sessionDay) return null
  return v.accessTier
}

export function computeVaultQuota(
  taken: Bt2TakenPickRecord[],
  sessionOperatingDayKey: string | null,
  apiPicks: Bt2VaultPickOut[],
): VaultQuotaSnapshot {
  let standardTaken = 0
  let premiumTaken = 0
  for (const r of taken) {
    const t = tierForRecord(r, sessionOperatingDayKey, apiPicks)
    if (t === 'standard') standardTaken += 1
    else if (t === 'premium') premiumTaken += 1
  }
  const standardRemaining = Math.max(0, VAULT_DAILY_CAP_STANDARD - standardTaken)
  const premiumRemaining = Math.max(0, VAULT_DAILY_CAP_PREMIUM - premiumTaken)
  return {
    standardTaken,
    premiumTaken,
    standardRemaining,
    premiumRemaining,
    atStandardCap: standardTaken >= VAULT_DAILY_CAP_STANDARD,
    atPremiumCap: premiumTaken >= VAULT_DAILY_CAP_PREMIUM,
  }
}
