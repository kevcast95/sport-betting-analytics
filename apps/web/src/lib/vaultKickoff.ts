/**
 * Corte por kickoff en bóveda (D-05.2-001 / US-FE-051).
 * `kickoffUtc` es instante absoluto en UTC; la comparación con `Date.now()` coincide con el servidor estricto.
 */
export function isKickoffUtcInPast(
  isoUtc: string | undefined,
  nowMs: number = Date.now(),
): boolean {
  if (isoUtc == null || typeof isoUtc !== 'string' || isoUtc.trim() === '') {
    return false
  }
  const t = Date.parse(isoUtc)
  if (Number.isNaN(t)) return false
  return nowMs >= t
}
