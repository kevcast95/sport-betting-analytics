/**
 * US-FE-012 — Día operativo (día calendario en TZ del usuario).
 *
 * MVP: TZ del dispositivo via Intl.DateTimeFormat().resolvedOptions().timeZone.
 * vNext: TZ explícita del perfil de usuario (campo `userTimeZone`).
 *
 * Limitación de seguridad (documentada): en MVP el cliente confía en el reloj
 * local; en producción, validar en servidor (US-BE backlog anti-manipulación).
 */

/** Formato YYYY-MM-DD estándar del día operativo. */
export type DayKey = string

/**
 * Devuelve el día operativo en formato YYYY-MM-DD usando la TZ indicada
 * (o TZ del dispositivo si no se provee).
 *
 * @param nowIso  ISO8601 del momento actual (inyectable para tests).
 * @param timeZone  IANA timezone string, p.ej. "America/Bogota".
 */
export function getOperatingDayKey(nowIso?: string, timeZone?: string): DayKey {
  const tz = timeZone ?? Intl.DateTimeFormat().resolvedOptions().timeZone
  const d = nowIso ? new Date(nowIso) : new Date()
  // 'en-CA' produce YYYY-MM-DD de forma nativa y estable.
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(d)
}

/**
 * ISO8601 de medianoche (00:00:00.000 local) del día SIGUIENTE a `dayKey`.
 * Representa el fin exacto del día operativo.
 *
 * Ejemplo: dayKey="2026-04-05" → "2026-04-06T05:00:00.000Z" (si TZ = UTC-5).
 *
 * Nota: usa aritmética local de Date (new Date(y,m,d)) que respeta la TZ
 * del proceso/dispositivo en MVP; coherente con `getOperatingDayKey`.
 */
export function endOfDayLocalIso(dayKey: DayKey): string {
  const [y, m, d] = dayKey.split('-').map(Number)
  // new Date(year, monthIndex, day) → midnight LOCAL del día d
  // +1 día → midnight del día d+1 = fin del día d
  return new Date(y, m - 1, d + 1, 0, 0, 0, 0).toISOString()
}

/**
 * ISO8601 en que expira la ventana de gracia 24 h (US-FE-012).
 * Gracia = fin del día `dayKey` + 24 h = medianoche local del día +2.
 *
 * Ejemplo: dayKey="2026-04-05" → grace expiry = 2026-04-07T00:00:00 local.
 */
export function graceExpiresIso(dayKey: DayKey): string {
  const [y, m, d] = dayKey.split('-').map(Number)
  // Medianoche local del día d+2
  return new Date(y, m - 1, d + 2, 0, 0, 0, 0).toISOString()
}

/**
 * true si el momento `nowIso` está DENTRO de la ventana de gracia del `dayKey`.
 *
 * Es decir: el día ya terminó (nowIso >= fin de día) pero la gracia no ha
 * expirado (nowIso < graceExpiry).
 */
export function isWithinGrace(dayKey: DayKey, nowIso: string): boolean {
  const now = new Date(nowIso).getTime()
  const endOfDay = new Date(endOfDayLocalIso(dayKey)).getTime()
  const graceEnd = new Date(graceExpiresIso(dayKey)).getTime()
  return now >= endOfDay && now < graceEnd
}

/**
 * true si la gracia del `dayKey` ya expiró respecto a `nowIso`.
 */
export function isGraceExpired(dayKey: DayKey, nowIso: string): boolean {
  const now = new Date(nowIso).getTime()
  const graceEnd = new Date(graceExpiresIso(dayKey)).getTime()
  return now >= graceEnd
}
