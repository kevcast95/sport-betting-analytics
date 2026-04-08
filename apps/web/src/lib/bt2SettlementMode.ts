/**
 * US-FE-013 / US-DX-001 — Modo de verificación de liquidaciones.
 *
 * 'trust'    → MVP autodeclarado: el operador declara el resultado final.
 *              Sin cruce contra resultado canónico externo. Control vía
 *              topes diarios, fricción (reflexión, cierre) y reglas de sesión.
 *
 * 'verified' → vNext: cruce de resultado declarado vs resultado canónico del
 *              evento en CDM (requiere US-BE + fuente de resultado por eventId).
 *              No implementar hasta que US-BE esté acordada.
 *              Ver: DECISIONES.md "Liquidación y DP: modo confianza (MVP) vs verificado (vNext)"
 *
 * Para cambiar a 'verified': coordinar con US-DX-001 y US-BE, no modificar
 * solo este archivo.
 */
export type SettlementVerificationMode = 'trust' | 'verified'

/** Valor actual del modo; el tipo amplio permite ramas UI para `verified` sin errores TS. */
export const SETTLEMENT_VERIFICATION_MODE: SettlementVerificationMode = 'trust'

/** Etiqueta legible en español para el modo actual (US-FE-013 §6, criterio 1). */
export const SETTLEMENT_MODE_LABEL_ES: Record<SettlementVerificationMode, string> = {
  trust:
    'Liquidación autodeclarada. En esta fase el operador declara el resultado; en futuras versiones podrá validarse contra el resultado canónico del evento.',
  verified:
    'Liquidación verificada contra resultado canónico del evento (vNext).',
}
