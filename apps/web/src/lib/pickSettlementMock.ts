import type { VaultPickCdm } from '@/data/vaultMockPicks'

/** Cuota decimal estable (mock CDM) derivada del id — sin tocar los 20 objetos del dataset. */
export function mockDecimalCuotaForPick(pick: VaultPickCdm): number {
  let h = 0
  for (let i = 0; i < pick.id.length; i += 1) {
    h = (h * 31 + pick.id.charCodeAt(i)) % 10007
  }
  const spread = (h % 45) / 100
  return Number((1.72 + spread).toFixed(2))
}
