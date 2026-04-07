/**
 * US-FE-012: tests unitarios para utilidades de día operativo.
 * Reloj inyectable para determinismo.
 */
import { describe, expect, it } from 'vitest'
import {
  endOfDayLocalIso,
  getOperatingDayKey,
  graceExpiresIso,
  isGraceExpired,
  isWithinGrace,
} from '@/lib/operatingDay'

describe('getOperatingDayKey', () => {
  it('devuelve formato YYYY-MM-DD', () => {
    const key = getOperatingDayKey('2026-04-05T14:00:00.000Z')
    expect(key).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('usa el reloj del sistema si no se inyecta nowIso', () => {
    const key = getOperatingDayKey()
    expect(key).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

describe('endOfDayLocalIso y graceExpiresIso', () => {
  it('endOfDayLocalIso del 2026-04-05 es medianoche del 2026-04-06 (local)', () => {
    const end = endOfDayLocalIso('2026-04-05')
    const endMs = new Date(end).getTime()
    // Medianoche local del 6 debe estar estrictamente después del 5 a las 12:00 local
    const noon5Apr = new Date(2026, 3, 5, 12, 0, 0).getTime()
    expect(endMs).toBeGreaterThan(noon5Apr)
    // Y antes del mediodía del 6
    const noon6Apr = new Date(2026, 3, 6, 12, 0, 0).getTime()
    expect(endMs).toBeLessThan(noon6Apr)
  })

  it('graceExpiresIso del 2026-04-05 es medianoche del 2026-04-07 (local)', () => {
    const grace = graceExpiresIso('2026-04-05')
    const graceMs = new Date(grace).getTime()
    const endMs = new Date(endOfDayLocalIso('2026-04-05')).getTime()
    // La gracia expira exactamente 24h después del fin del día
    expect(graceMs - endMs).toBe(24 * 60 * 60 * 1000)
  })
})

describe('isWithinGrace', () => {
  it('es true durante la ventana de gracia (entre fin del día y expiry)', () => {
    // Fin del día 2026-04-05 + 1 hora = debería estar en gracia
    const endMs = new Date(endOfDayLocalIso('2026-04-05')).getTime()
    const withinMs = endMs + 60 * 60 * 1000 // +1h tras fin de día
    expect(isWithinGrace('2026-04-05', new Date(withinMs).toISOString())).toBe(true)
  })

  it('es false antes de que termine el día', () => {
    // 12:00 del mismo día → dentro del día, no en gracia
    const noon = new Date(2026, 3, 5, 12, 0, 0).toISOString()
    expect(isWithinGrace('2026-04-05', noon)).toBe(false)
  })

  it('es false después de que expira la gracia', () => {
    const graceEnd = new Date(graceExpiresIso('2026-04-05')).getTime()
    const afterGrace = new Date(graceEnd + 1000).toISOString()
    expect(isWithinGrace('2026-04-05', afterGrace)).toBe(false)
  })
})

describe('isGraceExpired', () => {
  it('es true cuando ya pasó la gracia', () => {
    const graceEnd = new Date(graceExpiresIso('2026-04-05')).getTime()
    const afterGrace = new Date(graceEnd + 5000).toISOString()
    expect(isGraceExpired('2026-04-05', afterGrace)).toBe(true)
  })

  it('es false cuando la gracia sigue activa', () => {
    const endMs = new Date(endOfDayLocalIso('2026-04-05')).getTime()
    const withinGrace = new Date(endMs + 3600_000).toISOString()
    expect(isGraceExpired('2026-04-05', withinGrace)).toBe(false)
  })
})
