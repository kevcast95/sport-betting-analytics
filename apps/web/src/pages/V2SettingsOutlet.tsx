import { Bt2LocalResetSection } from '@/components/Bt2LocalResetSection'

/**
 * Ruta /v2/settings: el encabezado lo pinta BunkerLayout; aquí el cuerpo de ajustes V2.
 */
export default function V2SettingsOutlet() {
  return (
    <div className="space-y-6">
      <p className="max-w-2xl text-sm leading-relaxed text-[#52616a]">
        Preferencias del entorno BetTracker 2.0. El capital de trabajo y el stake se
        configuran desde el protocolo de gestión de capital (modal de tesorería).
      </p>
      <Bt2LocalResetSection />
    </div>
  )
}
