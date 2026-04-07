/**
 * US-FE-016 (T-048): Persistencia de tours contextuales por vista.
 *
 * Cada ruta V2 tiene un flag `hasSeenTour*` independiente:
 * — Se establece en true cuando el usuario completa o salta el tour.
 * — No bloquea sin "Saltar" (Regla 1 US-FE-016).
 * — No se repite automáticamente en cada sesión si ya fue visto.
 * — Se puede relanzar con `forceShow: true` desde el botón "Cómo funciona esta vista".
 *
 * Extensible: añadir nuevas claves a `TOUR_ROUTE_KEYS` cuando se creen más tours.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'

export const TOUR_ROUTE_KEYS = [
  'sanctuary',
  'vault',
  'settlement',
  'daily-review',
  'ledger',
  'performance',
  'profile',
  'settings',
] as const

export type TourRouteKey = (typeof TOUR_ROUTE_KEYS)[number]

export type TourStoreState = {
  /** Conjunto de claves de rutas cuyo tour ya fue visto/saltado. */
  seenTourKeys: string[]
}

export type TourStoreActions = {
  /** Marca el tour de la ruta como visto/completado. */
  markTourSeen: (key: TourRouteKey) => void
  /** Consulta si el tour de la ruta ya fue visto. */
  hasSeenTour: (key: TourRouteKey) => boolean
  /** Reinicia un tour específico (usado internamente por forceShow). */
  resetTour: (key: TourRouteKey) => void
  reset: () => void
}

export type TourStore = TourStoreState & TourStoreActions

const initial: TourStoreState = {
  seenTourKeys: [],
}

export const useTourStore = create<TourStore>()(
  persist(
    (set, get) => ({
      ...initial,
      markTourSeen: (key) => {
        if (get().seenTourKeys.includes(key)) return
        set((s) => ({ seenTourKeys: [...s.seenTourKeys, key] }))
        console.info(`[BT2] Tour visto: ${key}`)
      },
      hasSeenTour: (key) => get().seenTourKeys.includes(key),
      resetTour: (key) => {
        set((s) => ({ seenTourKeys: s.seenTourKeys.filter((k) => k !== key) }))
      },
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_tours',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
