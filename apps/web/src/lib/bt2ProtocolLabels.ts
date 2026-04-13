/** Copy operativo ES para DSR / liquidación / admin (Sprint 06). */

export function dsrConfidenceLabelEs(label: string): string {
  const l = label.trim().toLowerCase()
  if (l === 'low') return 'Baja'
  if (l === 'medium') return 'Media'
  if (l === 'high') return 'Alta'
  return label.trim() || '—'
}

/** §1.11 — línea única de confianza en Bóveda / settlement (sin “simbólica”). */
export function vektorModelConfidenceLineEs(
  label: string | null | undefined,
): string {
  if (label == null || !String(label).trim()) return ''
  return `Confianza del modelo: ${dsrConfidenceLabelEs(String(label))}`
}

/** Tablas y analytics admin — puede citar API / reglas con precisión técnica. */
export function dsrSourceDescriptionAdminEs(source: string): string {
  const s = source.trim().toLowerCase()
  if (s === 'rules_fallback') {
    return 'Origen: reglas del protocolo (sin razonador en vivo).'
  }
  if (s === 'dsr_api') {
    return 'Origen: razonador del modelo (API).'
  }
  if (!s) return ''
  return `Origen: ${source}.`
}

export function modelPredictionResultEs(
  v: string | null | undefined,
): string {
  if (v == null || v === '') return '—'
  const m: Record<string, string> = {
    hit: 'Acierto',
    miss: 'Fallo',
    void: 'Void',
    n_a: 'N/D',
  }
  return m[v] ?? v
}

export function pickStatusLabelEs(status: string): string {
  const s = status.trim().toLowerCase()
  const map: Record<string, string> = {
    open: 'Abierto',
    won: 'Ganado',
    lost: 'Perdido',
    void: 'Anulado',
    cancelled: 'Cancelado',
  }
  return map[s] ?? status
}
