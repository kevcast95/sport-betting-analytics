/**
 * Copy de producto (es-ES) para las 4 dimensiones de señal; sin tecnicismos.
 */
export function labelEvidenceQuality(
  v: string | null | undefined,
): string {
  const x = (v || '').toLowerCase()
  if (x === 'high') return 'Alto'
  if (x === 'medium') return 'Medio'
  if (x === 'low') return 'Bajo'
  return '—'
}

export function labelPredictiveTier(v: string | null | undefined): string {
  const x = (v || '').toLowerCase()
  if (x === 'high') return 'Alta'
  if (x === 'medium') return 'Media'
  if (x === 'low') return 'Baja'
  return '—'
}

export function labelActionTier(v: string | null | undefined): string {
  const x = (v || '').toLowerCase()
  if (x === 'premium') return 'Premium (DP)'
  if (x === 'free') return 'Libre'
  if (x === 'blocked') return 'Sin acceso'
  return '—'
}

export function formatEstimatedHitPct(p: number | null | undefined): string {
  if (p == null || Number.isNaN(p)) return '—'
  const clamped = Math.min(1, Math.max(0, p))
  return `${Math.round(clamped * 100)} %`
}
