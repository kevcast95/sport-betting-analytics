import { useEffect, useState } from 'react'
import { Bt2LocalResetSection } from '@/components/Bt2LocalResetSection'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'

const SETTINGS_TOUR = getTourScript('settings')!

/**
 * Ruta /v2/settings: el encabezado lo pinta BunkerLayout; aquí el cuerpo de ajustes V2.
 */
export default function V2SettingsOutlet() {
  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('settings'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    if (!hasSeenTour) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <p className="max-w-2xl text-sm leading-relaxed text-[#52616a]">
          Preferencias del entorno BetTracker 2.0. El capital de trabajo y el stake se
          configuran desde el protocolo de gestión de capital (modal de tesorería).
        </p>
        <button
          type="button"
          onClick={() => { resetTour('settings'); setTourOpen(true) }}
          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[#a4b4be]/30 bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] transition-colors hover:border-[#8B5CF6]/30 hover:text-[#8B5CF6]"
          title="Ver cómo funciona esta vista"
        >
          <span aria-hidden className="text-[11px]">?</span>
          Cómo funciona
        </button>
      </div>
      <Bt2LocalResetSection />

      {/* US-FE-021 (T-055): tour contextual */}
      <ViewTourModal
        open={tourOpen}
        title={SETTINGS_TOUR.title}
        steps={SETTINGS_TOUR.steps}
        onComplete={() => { setTourOpen(false); markTourSeen('settings') }}
      />
    </div>
  )
}
