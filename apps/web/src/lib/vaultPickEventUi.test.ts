import { describe, expect, it } from 'vitest'
import { vaultPickEventPresentation } from '@/lib/vaultPickEventUi'

describe('vaultPickEventPresentation (T-169)', () => {
  it('mock / no API: sin badge ni dim', () => {
    const r = vaultPickEventPresentation('scheduled', true, false)
    expect(r.statusLabel).toBeNull()
    expect(r.dimCard).toBe(false)
  })

  it('isAvailable false → No disponible + dim', () => {
    const r = vaultPickEventPresentation('scheduled', false, true)
    expect(r.statusLabel).toBe('No disponible')
    expect(r.dimCard).toBe(true)
  })

  it('finished → Finalizado + dim', () => {
    const r = vaultPickEventPresentation('finished', true, true)
    expect(r.statusLabel).toBe('Finalizado')
    expect(r.dimCard).toBe(true)
  })

  it('inplay → En juego', () => {
    const r = vaultPickEventPresentation('inplay', true, true)
    expect(r.statusLabel).toBe('En juego')
    expect(r.dimCard).toBe(false)
  })

  it('scheduled → Programado', () => {
    const r = vaultPickEventPresentation('scheduled', true, true)
    expect(r.statusLabel).toBe('Programado')
    expect(r.dimCard).toBe(false)
  })
})
