/** Perfil operativo asignado al completar el diagnóstico (claves técnicas). */
export type OperatorProfileId =
  | 'THE_GUARDIAN'
  | 'THE_SNIPER'
  | 'THE_VOLATILE'

export const DIAGNOSTIC_INITIAL_INTEGRITY = 0.88

/** Opción A (índice 0): +0.04 · B (1): 0 · C (2): −0.06 */
export function integrityAfterAnswer(
  current: number,
  option: 0 | 1 | 2,
): number {
  const delta = option === 0 ? 0.04 : option === 1 ? 0 : -0.06
  return Math.min(1, Math.max(0, Number((current + delta).toFixed(4))))
}

export function computeOperatorProfile(answers: (0 | 1 | 2)[]): OperatorProfileId {
  let a = 0
  let c = 0
  for (const x of answers) {
    if (x === 0) a += 1
    else if (x === 2) c += 1
  }
  if (a > c) return 'THE_GUARDIAN'
  if (c > a) return 'THE_VOLATILE'
  return 'THE_SNIPER'
}

export function disciplinePointsPreview(
  baseDisciplinePoints: number,
  integrity: number,
): number {
  return Math.round(baseDisciplinePoints + (integrity - DIAGNOSTIC_INITIAL_INTEGRITY) * 400)
}

export const OPERATOR_PROFILE_LABEL_ES: Record<OperatorProfileId, string> = {
  THE_GUARDIAN: 'Guardián',
  THE_SNIPER: 'Francotirador',
  THE_VOLATILE: 'Volátil',
}
