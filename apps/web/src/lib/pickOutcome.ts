/** Mínimo para resultado efectivo en UI (prioriza cierre manual del usuario). */
export type EffectiveOutcomePickLike = {
  user_outcome?: 'win' | 'loss' | 'pending' | null
  system_outcome?: 'win' | 'loss' | 'pending' | null
  result?: { outcome: string } | null | undefined
}

export function effectivePickOutcome(
  p: EffectiveOutcomePickLike,
): 'win' | 'loss' | 'pending' | null {
  const u = p.user_outcome
  if (u === 'win' || u === 'loss' || u === 'pending') return u
  const s = p.system_outcome ?? p.result?.outcome
  if (s === 'win' || s === 'loss' || s === 'pending') return s
  return null
}
