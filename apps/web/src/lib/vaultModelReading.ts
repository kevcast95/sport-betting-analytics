/**
 * Una sola voz en bóveda/detalle, alineada a v1 (`razon` en `jobs/render_telegram_payload.py`):
 * título Vektor + cuerpo humano, sin segunda tarjeta ni jerga CDM/DSR/protocolo.
 */
export const MODEL_WHY_TITLE_ES = 'Vektor — por qué lo sugiere el modelo'

/** Cuando no hay `razon`/narrativa del modelo pero sí señal por reglas sobre cuotas. */
export const MODEL_WHY_FALLBACK_RULES_ES =
  'Con la información disponible para este partido, la lectura se alinea con la opción que muestra mayor respaldo entre las salidas del mercado mostradas, sin tomar solo la cuota más alta como único criterio.'

/** DSR habilitado pero sin texto publicado (ingesta o corrida). */
export const MODEL_WHY_FALLBACK_DSR_MISSING_ES =
  'Todavía no hay texto de lectura publicado para este partido; podés apoyarte en el mercado y la cuota indicadas mientras se actualiza la señal.'

/** Texto interno/legacy que no debe mostrarse tal cual al usuario. */
export function isGenericCdmTraduccionEs(text: string | null | undefined): boolean {
  if (!text || !text.trim()) return true
  const t = text.trim().toLowerCase()
  if (t.includes('modelo en construcción')) return true
  if (t.includes('cdm bt2') && t.includes('basada')) return true
  if (t.includes('datos cdm') && t.includes('construcción')) return true
  if (t.includes('sin narrativa dsr extendida')) return true
  if (t.includes('señal basada en reglas cdm')) return true
  return false
}

/**
 * Texto persistido de corridas viejas o plantillas internas: no mostrarlo tal cual al usuario.
 */
export function isPipelineJargonNarrativeEs(text: string | null | undefined): boolean {
  if (!text || !text.trim()) return false
  const t = text.trim().toLowerCase()
  const markers = [
    'línea 1x2 del cdm',
    'narrativa extendida del análisis dsr',
    'narrativa extendida',
    'criterios del protocolo sobre las cuotas',
    'sin narrativa dsr extendida',
    'señal basada en reglas cdm',
    'pipeline s6-',
    'ranking dsr automático',
    'sin cuotas suficientes para ranking',
  ]
  return markers.some((m) => t.includes(m))
}

function isDsrApiSource(source: string): boolean {
  return source.trim().toLowerCase() === 'dsr_api'
}

export type ModelWhyReading = { title: string; body: string }

/**
 * Un solo bloque para UI: prioridad narrativa DSR → texto útil del API → fallback breve sin jerga.
 */
export function modelWhyReading(d: {
  dsrNarrativeEs: string | null | undefined
  traduccionHumana: string | null | undefined
  dsrSource?: string | null
}): ModelWhyReading {
  const dsr = (d.dsrNarrativeEs ?? '').trim()
  const trRaw = (d.traduccionHumana ?? '').trim()
  const trPlaceholder = isGenericCdmTraduccionEs(trRaw)
  const dsrApi = isDsrApiSource(d.dsrSource ?? '')

  const dsrOk = Boolean(dsr) && !isPipelineJargonNarrativeEs(dsr)
  const trOk =
    Boolean(trRaw) && !trPlaceholder && !isPipelineJargonNarrativeEs(trRaw)

  if (dsrOk) {
    return { title: MODEL_WHY_TITLE_ES, body: dsr }
  }
  if (trOk) {
    return { title: MODEL_WHY_TITLE_ES, body: trRaw }
  }
  if (dsrApi) {
    return { title: MODEL_WHY_TITLE_ES, body: MODEL_WHY_FALLBACK_DSR_MISSING_ES }
  }
  return { title: MODEL_WHY_TITLE_ES, body: MODEL_WHY_FALLBACK_RULES_ES }
}

/** @deprecated Usar `modelWhyReading`; se mantiene para imports legacy. */
export const RULES_FALLBACK_MODEL_COPY_ES = MODEL_WHY_FALLBACK_RULES_ES

export type UnifiedApiModelReading = { title: string; body: string }

export function unifiedApiModelReading(d: {
  dsrNarrativeEs: string | null | undefined
  traduccionHumana: string | null | undefined
  dsrSource?: string | null
}): UnifiedApiModelReading {
  return modelWhyReading(d)
}
