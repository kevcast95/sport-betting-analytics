/**
 * US-FE-002: valor de una unidad de apuesta según bankroll y % de stake.
 * stakePct en puntos porcentuales (p. ej. 2 → 2%).
 */
export function computeUnitValue(bankroll: number, stakePct: number): number {
  if (!Number.isFinite(bankroll) || !Number.isFinite(stakePct)) return Number.NaN
  return bankroll * (stakePct / 100)
}

export const STAKE_PCT_MIN = 0.25
export const STAKE_PCT_MAX = 5
export const STAKE_PCT_DEFAULT = 2
export const STAKE_PCT_STEP = 0.05

/** Entero COP: solo dígitos (permite pegar con separadores). */
export function parseCopIntegerInput(raw: string): number {
  const digits = raw.replace(/\D/g, '')
  if (digits === '') return Number.NaN
  const n = Number(digits)
  return Number.isFinite(n) ? n : Number.NaN
}
