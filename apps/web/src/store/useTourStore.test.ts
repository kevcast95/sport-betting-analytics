/**
 * US-FE-016: tests unitarios del store de tours contextuales.
 */
import { describe, expect, it, beforeEach } from 'vitest'
import { useTourStore } from '@/store/useTourStore'

beforeEach(() => {
  useTourStore.getState().reset()
})

describe('useTourStore (US-FE-016)', () => {
  it('hasSeenTour es false por defecto', () => {
    expect(useTourStore.getState().hasSeenTour('sanctuary')).toBe(false)
    expect(useTourStore.getState().hasSeenTour('vault')).toBe(false)
  })

  it('markTourSeen marca el tour como visto', () => {
    useTourStore.getState().markTourSeen('sanctuary')
    expect(useTourStore.getState().hasSeenTour('sanctuary')).toBe(true)
    // Otras rutas no afectadas
    expect(useTourStore.getState().hasSeenTour('vault')).toBe(false)
  })

  it('markTourSeen es idempotente (no duplica en seenTourKeys)', () => {
    useTourStore.getState().markTourSeen('vault')
    useTourStore.getState().markTourSeen('vault')
    const { seenTourKeys } = useTourStore.getState()
    expect(seenTourKeys.filter((k) => k === 'vault')).toHaveLength(1)
  })

  it('resetTour permite relanzar el tour (forceShow)', () => {
    useTourStore.getState().markTourSeen('sanctuary')
    useTourStore.getState().resetTour('sanctuary')
    expect(useTourStore.getState().hasSeenTour('sanctuary')).toBe(false)
  })

  it('resetTour solo afecta la ruta indicada', () => {
    useTourStore.getState().markTourSeen('sanctuary')
    useTourStore.getState().markTourSeen('vault')
    useTourStore.getState().resetTour('sanctuary')
    expect(useTourStore.getState().hasSeenTour('sanctuary')).toBe(false)
    expect(useTourStore.getState().hasSeenTour('vault')).toBe(true)
  })

  it('reset devuelve el store a estado inicial', () => {
    useTourStore.getState().markTourSeen('sanctuary')
    useTourStore.getState().markTourSeen('vault')
    useTourStore.getState().reset()
    expect(useTourStore.getState().seenTourKeys).toHaveLength(0)
  })
})
