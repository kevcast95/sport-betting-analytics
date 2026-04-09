/**
 * Unifica lectura CDM (`traduccionHumana`) y narrativa DSR en un solo bloque de UI
 * (US-FE-052 / T-165 — evitar “dos razonamientos” cuando el CDM es placeholder).
 */

export const RULES_FALLBACK_MODEL_COPY_ES =
  'Esta señal se priorizó con las reglas del protocolo; no hay narrativa adicional del razonador para este ítem.'

export function isGenericCdmTraduccionEs(text: string | null | undefined): boolean {
  if (!text || !text.trim()) return true
  const t = text.trim().toLowerCase()
  if (t.includes('modelo en construcción')) return true
  if (t.includes('cdm bt2') && t.includes('basada')) return true
  if (t.includes('datos cdm') && t.includes('construcción')) return true
  return false
}

export type UnifiedApiModelReading = { title: string; body: string }

/** Prioridad: narrativa DSR → lectura CDM no genérica → copy de reglas (una sola voz). */
export function unifiedApiModelReading(d: {
  dsrNarrativeEs: string
  traduccionHumana: string | null | undefined
}): UnifiedApiModelReading {
  const dsr = (d.dsrNarrativeEs ?? '').trim()
  if (dsr) {
    return { title: 'Criterio del modelo (DSR)', body: dsr }
  }
  const tr = d.traduccionHumana?.trim() ?? ''
  if (tr && !isGenericCdmTraduccionEs(tr)) {
    return { title: 'Lectura del modelo', body: tr }
  }
  return {
    title: 'Criterio del modelo (DSR)',
    body: RULES_FALLBACK_MODEL_COPY_ES,
  }
}
