import { resetAllBt2PersistedState } from '@/lib/bt2ResetAllLocalState'

/**
 * Solo en desarrollo: bloque para borrar persistencia BT2 sin ocupar otras vistas.
 */
export function Bt2LocalResetSection() {
  if (!import.meta.env.DEV) return null
  return (
    <section
      className="mt-10 rounded-xl border border-dashed border-[#a4b4be]/50 bg-[#eef4fa]/40 p-6"
      aria-label="Herramientas de desarrollo"
    >
      <h2 className="text-xs font-bold uppercase tracking-widest text-[#6e7d86]">
        Desarrollo · datos locales
      </h2>
      <p className="mt-2 max-w-xl text-sm text-[#52616a]">
        Borra contrato, diagnóstico, ledger, bóveda, tesorería y sesión guardados en este
        navegador. Útil para repetir el flujo desde el login.
      </p>
      <button
        type="button"
        className="mt-4 rounded-lg border border-[#a4b4be]/40 bg-white px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-[#52616a] transition-colors hover:border-[#9e3f4e]/50 hover:text-[#9e3f4e]"
        onClick={() => {
          if (
            !window.confirm(
              '¿Borrar todo el estado local de BetTracker 2? Se cerrará la sesión y volverás a /v2/session.',
            )
          ) {
            return
          }
          resetAllBt2PersistedState()
          window.location.href = '/v2/session'
        }}
      >
        Prueba desde cero
      </button>
    </section>
  )
}
