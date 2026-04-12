/**
 * Unifica narrativa DSR, texto CDM y origen (`dsrSource`) en un solo bloque de UI
 * (US-FE-052 / T-165; S6.1 US-FE-055 — no mezclar razonador, reglas y placeholders).
 */

export const RULES_FALLBACK_MODEL_COPY_ES =
  'No hubo señal suficiente del análisis estadístico del día; esta opción se armó con reglas del protocolo sobre cuotas reales del CDM, priorizando coherencia con los datos disponibles — no maximizar ganancia por cuota alta como único eje (D-06-027). Si el día tuvo pocos eventos, el criterio puede estar sesgado por datos limitados (D-06-025).'

/** Texto servidor/CDM que no debe mostrarse como “lectura analítica”. */
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

export type UnifiedApiModelReading = { title: string; body: string }

function isDsrApiSource(source: string): boolean {
  return source.trim().toLowerCase() === 'dsr_api'
}

/**
 * Prioridad: narrativa DSR (si origen y texto lo permiten) → CDM no placeholder → copy de reglas / vacío DSR explícito.
 * `dsrSource` gobierna si el título puede implicar “razonador en vivo” (US-FE-055).
 */
export function unifiedApiModelReading(d: {
  dsrNarrativeEs: string
  traduccionHumana: string | null | undefined
  /** p. ej. `dsr_api` | `rules_fallback` — vacío se trata como no-DSR-api para no afirmar razonador. */
  dsrSource?: string | null
}): UnifiedApiModelReading {
  const src = (d.dsrSource ?? '').trim()
  const dsrApi = isDsrApiSource(src)
  const dsr = (d.dsrNarrativeEs ?? '').trim()
  const trRaw = d.traduccionHumana?.trim() ?? ''
  const trPlaceholder = isGenericCdmTraduccionEs(trRaw)

  if (dsrApi) {
    if (dsr) {
      return { title: 'Vektor — por qué', body: dsr }
    }
    if (trRaw && !trPlaceholder) {
      return {
        title: 'Vektor — contexto',
        body: trRaw,
      }
    }
    return {
      title: 'Vektor — por qué',
      body:
        'No hay texto Vektor publicado para este ítem. Si aparece una línea de confianza, describe la postura del modelo respecto al insumo del día; no indica por sí sola un fallo operativo ni la probabilidad de acierto.',
    }
  }

  if (dsr) {
    return {
      title: 'Vektor — contexto',
      body: dsr,
    }
  }
  if (trRaw && !trPlaceholder) {
    return {
      title: 'Vektor — contexto',
      body: trRaw,
    }
  }
  return {
    title: 'Vektor — por qué',
    body: RULES_FALLBACK_MODEL_COPY_ES,
  }
}
