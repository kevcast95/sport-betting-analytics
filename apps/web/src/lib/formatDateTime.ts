/** Fechas legibles para Colombia (COP / zona horaria local del usuario de apuestas). */

const TZ_BOG = 'America/Bogota'

/** YYYY-MM-DD → texto corto (p. ej. 23 mar 2026). */
export function formatShortDateFromYMD(isoDate: string): string {
  const [y, m, d] = isoDate.split('-').map(Number)
  if (!y || !m || !d) return isoDate
  const dt = new Date(Date.UTC(y, m - 1, d, 12, 0, 0))
  return new Intl.DateTimeFormat('es-CO', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: TZ_BOG,
  }).format(dt)
}

/**
 * Convierte el formato antiguo del meta (`YYYY-MM-DD HH:MM UTC`) a hora Colombia.
 * Si ya viene como "… · hora Colombia", se devuelve tal cual.
 */
export function kickoffReadableCol(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null
  const t = raw.trim()
  if (t.includes('hora Colombia')) return t
  const m = t.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) UTC$/i)
  if (!m) return t
  const iso = `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:00Z`
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return t
  const clock = new Intl.DateTimeFormat('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: TZ_BOG,
  }).format(d)
  return `${clock} · hora Colombia`
}

export function formatPickDateTimeLines(isoUtc: string | undefined): {
  primary: string
  secondary: string
} {
  if (!isoUtc) {
    return { primary: '—', secondary: '' }
  }
  const d = new Date(isoUtc)
  if (Number.isNaN(d.getTime())) {
    return { primary: isoUtc, secondary: '' }
  }
  const bog = new Intl.DateTimeFormat('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: TZ_BOG,
    timeZoneName: 'short',
  }).format(d)
  const utc = new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  }).format(d)
  return { primary: bog, secondary: `Misma marca en UTC: ${utc}` }
}

/** Convierte YYYY-MM-DD a texto largo en Colombia. */
export function formatCalendarDateEs(isoDate: string): string {
  const [y, m, d] = isoDate.split('-').map(Number)
  if (!y || !m || !d) return isoDate
  const dt = new Date(Date.UTC(y, m - 1, d, 12, 0, 0))
  return new Intl.DateTimeFormat('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'America/Bogota',
  }).format(dt)
}

export function formatCOP(n: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(Math.round(n))
}
