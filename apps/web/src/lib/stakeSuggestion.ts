/** Heurística local: sugerir % de bankroll según confianza declarada por el modelo. */

export type ConfidenceTier = 'high' | 'medium' | 'low' | 'unknown'

function norm(s: string) {
  return s.trim().toLowerCase()
}

export function confidenceTierFromLabel(conf?: string | null): ConfidenceTier {
  if (!conf) return 'unknown'
  const c = norm(conf)
  if (
    c.includes('muy') &&
    (c.includes('alt') || c.includes('high') || c.includes('fuerte'))
  )
    return 'high'
  if (
    c.includes('alt') ||
    c.includes('high') ||
    c.includes('fuerte') ||
    c.includes('★★★') ||
    c === 'a'
  )
    return 'high'
  if (
    c.includes('med') ||
    c.includes('mid') ||
    c.includes('media') ||
    c.includes('★★') ||
    c === 'm'
  )
    return 'medium'
  if (
    c.includes('baj') ||
    c.includes('low') ||
    c.includes('débil') ||
    c.includes('debil') ||
    c.includes('★') ||
    c === 'b'
  )
    return 'low'
  const n = Number.parseFloat(c.replace(',', '.'))
  if (!Number.isNaN(n)) {
    if (n >= 0.75) return 'high'
    if (n >= 0.45) return 'medium'
    if (n > 0) return 'low'
  }
  return 'unknown'
}

const PCT: Record<ConfidenceTier, { min: number; max: number }> = {
  high: { min: 0.01, max: 0.025 },
  medium: { min: 0.005, max: 0.015 },
  low: { min: 0.0025, max: 0.0075 },
  unknown: { min: 0.005, max: 0.012 },
}

/** Punto medio del rango sugerido (útil para botón «aplicar sugerencia»). */
export function suggestedStakeMidCOP(
  bankroll: number,
  tier: ConfidenceTier,
): number {
  const { min, max } = suggestedStakeRangeCOP(bankroll, tier)
  return Math.round((min + max) / 2)
}

export function suggestedStakeRangeCOP(
  bankroll: number,
  tier: ConfidenceTier,
): { min: number; max: number } {
  const b = Math.max(0, bankroll)
  const { min, max } = PCT[tier]
  return {
    min: Math.round(b * min),
    max: Math.round(b * max),
  }
}

export function stakeAssessmentCOP(
  amount: number,
  bankroll: number,
  tier: ConfidenceTier,
): { tone: 'ok' | 'warn' | 'risk'; message: string } {
  if (!Number.isFinite(amount) || amount <= 0) {
    return { tone: 'ok', message: '' }
  }
  if (!Number.isFinite(bankroll) || bankroll <= 0) {
    return {
      tone: 'warn',
      message:
        'Indica tu bankroll en la barra lateral para recibir sugerencias de monto.',
    }
  }
  const { min, max } = suggestedStakeRangeCOP(bankroll, tier)
  const pct = amount / bankroll
  if (pct > 0.05) {
    return {
      tone: 'risk',
      message: `Supera el 5 % del bankroll (${(pct * 100).toFixed(1)} %). Solo si tu plan lo permite.`,
    }
  }
  if (amount > max * 1.35) {
    return {
      tone: 'warn',
      message: `Por encima del rango sugerido para esta confianza (${min.toLocaleString('es-CO')} – ${max.toLocaleString('es-CO')} COP aprox.).`,
    }
  }
  if (amount < min * 0.5 && min > 0) {
    return {
      tone: 'ok',
      message: 'Monto conservador respecto al rango sugerido.',
    }
  }
  return {
    tone: 'ok',
    message: 'Dentro de un rango razonable para tu bankroll y la confianza del modelo.',
  }
}

export function tierLabelEs(tier: ConfidenceTier): string {
  switch (tier) {
    case 'high':
      return 'Confianza alta (modelo)'
    case 'medium':
      return 'Confianza media'
    case 'low':
      return 'Confianza baja'
    default:
      return 'Confianza no tipificada'
  }
}
