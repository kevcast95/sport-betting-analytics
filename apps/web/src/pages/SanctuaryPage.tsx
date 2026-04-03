import { NavLink } from 'react-router-dom'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useUserStore } from '@/store/useUserStore'

const DAILY_MISSIONS_PROGRESS_PCT = 84

function HeartIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M12 20.5s-6.5-4.35-9-8.25C1.25 9.1 2.51 6 5.25 6c1.74 0 3.05 1.12 3.75 2.5C9.7 7.12 11.01 6 12.75 6 15.49 6 16.75 9.1 15 12.25 12.5 16.15 12 20.5 12 20.5Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/**
 * US-FE-004: Santuario. Hero + tarjetas alineadas al mock Stitch (ref compuesta;
 * el HTML en `us_fe_004_sanctuaryt.md` no incluye este bloque; se portan tokens Zurich Calm).
 */
export default function SanctuaryPage() {
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const confirmedBankrollCop = useBankrollStore((s) => s.confirmedBankrollCop)

  const equityFormatted =
    confirmedBankrollCop <= 0
      ? '—'
      : new Intl.NumberFormat('es-CO', {
          style: 'currency',
          currency: 'COP',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(confirmedBankrollCop)

  return (
    <div className="space-y-10">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
        <div className="min-w-0 space-y-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8B5CF6]">
            Santuario Zurich
          </p>
          <h1 className="max-w-4xl text-4xl font-bold tracking-tighter text-[#26343d] sm:text-5xl lg:text-6xl">
            Calma en el ruido del cambio.
          </h1>
        </div>
        <span className="inline-flex w-fit shrink-0 self-end rounded-full border border-[#a4b4be]/30 bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] sm:self-auto">
          Actualizado ahora
        </span>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#a4b4be]/20 bg-white p-6 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
            Patrimonio total
          </p>
          <p className="mt-2 font-mono text-3xl font-bold tabular-nums tracking-tight text-[#059669] sm:text-4xl">
            {equityFormatted}
          </p>
          <div className="mt-6 grid grid-cols-2 gap-6 border-t border-[#a4b4be]/15 pt-6">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                Crecimiento patrimonial
              </p>
              <p className="mt-1 font-mono text-lg font-bold tabular-nums text-[#8B5CF6]">
                +14.2%
              </p>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                Caída máxima
              </p>
              <p className="mt-1 font-mono text-lg font-bold tabular-nums text-[#914d00]">
                -4.2%
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[#8B5CF6]/20 bg-[#e9ddff]/35 p-6 shadow-sm backdrop-blur-sm">
          <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-[#8B5CF6]/15 text-[#8B5CF6]">
            <HeartIcon className="h-5 w-5" />
          </div>
          <h2 className="text-lg font-bold tracking-tight text-[#26343d]">
            Estado: óptimo y disciplinado
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-[#52616a]">
            Tu perfil de riesgo y tus métricas de disciplina están dentro de
            parámetros. Opera con estrategia, no con impulso.
          </p>
        </div>
      </div>

      <section
        aria-label="Disciplina y misiones diarias"
        className="rounded-xl border border-[#a4b4be]/25 bg-[#ddeaf3]/40 p-6 shadow-sm"
      >
        <div className="flex flex-col gap-8 lg:flex-row lg:items-stretch lg:gap-10">
          <div className="flex shrink-0 items-center gap-4 rounded-xl border border-[#a4b4be]/20 bg-white px-5 py-4 shadow-sm">
            <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center text-[#8B5CF6]">
              <Bt2ShieldCheckIcon className="h-8 w-8" />
            </span>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#26343d]">
                Riqueza de carácter
              </p>
              <p className="mt-1 font-mono text-xl font-bold tabular-nums tracking-tight text-[#8B5CF6]">
                {disciplinePoints.toLocaleString('es-CO')}{' '}
                <span className="text-base font-bold">DP</span>
              </p>
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <h2 className="text-[10px] font-bold uppercase tracking-wider text-[#26343d]">
                Misiones diarias
              </h2>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                {DAILY_MISSIONS_PROGRESS_PCT}% completado
              </p>
            </div>
            <div
              className="mt-3 h-3 overflow-hidden rounded-full bg-[#e5eff7]"
              role="progressbar"
              aria-valuenow={DAILY_MISSIONS_PROGRESS_PCT}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Progreso de misiones diarias"
            >
              <div
                className="h-full rounded-full bg-[#8B5CF6] transition-[width] duration-500"
                style={{ width: `${DAILY_MISSIONS_PROGRESS_PCT}%` }}
              />
            </div>
            <ul className="mt-5 flex flex-wrap gap-x-8 gap-y-3 text-xs font-semibold">
              <li className="flex items-center gap-2 text-[#26343d]">
                <span className="h-2 w-2 shrink-0 rounded-full bg-[#8B5CF6]" />
                Mantener el stake
              </li>
              <li className="flex items-center gap-2 text-[#26343d]">
                <span className="h-2 w-2 shrink-0 rounded-full bg-[#8B5CF6]" />
                Consistencia de sesión
              </li>
              <li className="flex items-center gap-2 text-[#52616a]">
                <span className="h-2 w-2 shrink-0 rounded-full bg-[#a4b4be]" />
                Paciencia de mercado
              </li>
            </ul>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#a4b4be]/30 bg-[#eef4fa]/40 p-6">
          <h2 className="text-sm font-bold tracking-tight text-[#26343d]">
            Próximo paso
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#52616a]">
            Revisa oportunidades con valor esperado positivo en la bóveda. Cada
            desbloqueo consume DP de tu saldo de disciplina.
          </p>
          <NavLink
            to="/v2/vault"
            className="mt-4 inline-flex rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] px-5 py-2.5 text-xs font-bold uppercase tracking-wide text-white shadow-md shadow-[#8B5CF6]/20"
          >
            Ir a La Bóveda
          </NavLink>
        </div>
        <div className="rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6">
          <h2 className="text-sm font-bold tracking-tight text-[#26343d]">
            Estado del entorno
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#52616a]">
            Panel de control conductual V2. Sin datos de proveedor en esta
            vista: métricas locales del dispositivo.
          </p>
        </div>
      </div>
    </div>
  )
}
