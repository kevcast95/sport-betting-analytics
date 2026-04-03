import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { TreasuryModal } from '@/components/TreasuryModal'
import {
  Bt2ChartBarsIcon,
  Bt2HistoryIcon,
  Bt2PlusIcon,
  Bt2SettingsIcon,
  Bt2ShieldCheckIcon,
  Bt2UserIcon,
  Bt2VaultIcon,
} from '@/components/icons/bt2Icons'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useUserStore } from '@/store/useUserStore'

function navItemClass(isActive: boolean) {
  return [
    'flex w-full items-center gap-3 rounded-none px-4 py-3 text-left font-semibold transition-colors',
    isActive
      ? 'border-r-2 border-[#8B5CF6] bg-[#eef4fa]/60 font-bold text-[#8B5CF6]'
      : 'border-r-2 border-transparent text-[#52616a] hover:bg-white/60',
  ].join(' ')
}

export default function BunkerLayout() {
  const location = useLocation()
  const isSettings = location.pathname.startsWith('/v2/settings')

  const { operatorName, disciplinePoints, incrementDisciplinePoints } =
    useUserStore()
  const confirmedBankrollCop = useBankrollStore((s) => s.confirmedBankrollCop)

  const [dpPulseKey, setDpPulseKey] = useState(0)
  const [treasuryOpen, setTreasuryOpen] = useState(false)

  const treasuryBlocking = confirmedBankrollCop <= 0

  useEffect(() => {
    if (confirmedBankrollCop === 0) {
      setTreasuryOpen(true)
    }
  }, [confirmedBankrollCop])

  const equityLabel = useMemo(() => {
    if (confirmedBankrollCop <= 0) return 'Sin configurar'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(confirmedBankrollCop)
  }, [confirmedBankrollCop])

  const incPositiveAction = () => {
    incrementDisciplinePoints(25)
    setDpPulseKey((k) => k + 1)
  }

  const openTreasury = () => setTreasuryOpen(true)

  return (
    <div className="flex h-full w-[100vw] flex-col overflow-hidden bg-[#f6fafe] text-[#26343d]">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between gap-4 border-b border-[#26343d]/15 bg-[#f6fafe]/90 px-4 py-3 backdrop-blur-md sm:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3 sm:gap-4">
          <span className="truncate text-lg font-bold tracking-tighter text-[#26343d] sm:text-xl">
            BetTracker 2.0
          </span>
          <span className="hidden h-6 w-[1px] bg-[#6e7d86]/30 sm:inline-block" />
          <div className="flex items-center gap-2 rounded-xl border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-2 sm:gap-3 sm:px-4">
            <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-[#8B5CF6]">
              <Bt2ShieldCheckIcon className="h-5 w-5" />
            </span>
            <motion.span
              key={dpPulseKey}
              initial={{ scale: 0.98 }}
              animate={{ scale: 1.02 }}
              transition={{ duration: 0.15 }}
              className="font-mono text-xs font-bold tabular-nums text-[#26343d] sm:text-sm"
            >
              {disciplinePoints.toLocaleString('es-CO')} DP
            </motion.span>
          </div>
          <button
            type="button"
            onClick={openTreasury}
            className="hidden min-w-0 flex-col items-start rounded-xl border border-[#a4b4be]/20 bg-white/60 px-3 py-1.5 text-left transition-colors hover:bg-white sm:flex"
            title="Abrir protocolo de capital"
          >
            <span className="text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
              Total equity
            </span>
            <span
              className={[
                'max-w-[10rem] truncate font-mono text-sm font-bold tabular-nums',
                confirmedBankrollCop > 0 ? 'text-[#059669]' : 'text-[#52616a]',
              ].join(' ')}
            >
              {equityLabel}
            </span>
          </button>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-4">
          <button
            type="button"
            onClick={openTreasury}
            className="flex max-w-[9rem] flex-col rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa]/80 px-2 py-1 text-left sm:hidden"
          >
            <span className="text-[9px] font-bold uppercase tracking-wider text-[#6e7d86]">
              Equity
            </span>
            <span
              className={[
                'truncate font-mono text-[11px] font-bold',
                confirmedBankrollCop > 0 ? 'text-[#059669]' : 'text-[#52616a]',
              ].join(' ')}
            >
              {equityLabel}
            </span>
          </button>
          <div className="hidden text-right sm:block">
            <p className="text-xs font-bold tracking-wider text-[#26343d]">
              {operatorName ?? 'Operador'}
            </p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]">
              Nivel: Elite
            </p>
          </div>
          <div className="h-9 w-9 shrink-0 rounded-full border border-[#8B5CF6]/20 bg-[#eef4fa]" />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <aside className="hidden w-64 flex-col border-r border-[#26343d]/15 bg-[#eef4fa] py-8 px-4 md:flex">
          <nav className="flex-1 space-y-1">
            <NavLink
              to="/v2/dashboard"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2VaultIcon className="h-5 w-5" />
              </span>
              El Búnker
            </NavLink>
            <button
              type="button"
              className="flex w-full items-center gap-3 rounded-none px-4 py-3 text-left font-semibold text-[#52616a] hover:bg-white/60"
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2HistoryIcon className="h-5 w-5" />
              </span>
              Historial
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-3 rounded-none px-4 py-3 text-left font-semibold text-[#52616a] hover:bg-white/60"
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2ChartBarsIcon className="h-5 w-5" />
              </span>
              Estrategia
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-3 rounded-none px-4 py-3 text-left font-semibold text-[#52616a] hover:bg-white/60"
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2UserIcon className="h-5 w-5" />
              </span>
              Perfil
            </button>
            <NavLink
              to="/v2/settings"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2SettingsIcon className="h-5 w-5" />
              </span>
              Settings
            </NavLink>
          </nav>

          <div className="mt-auto">
            <button
              type="button"
              onClick={incPositiveAction}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-3 text-xs font-bold tracking-tight text-white uppercase shadow-lg shadow-[#8B5CF6]/20"
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-white">
                <Bt2PlusIcon className="h-5 w-5" />
              </span>
              Nueva Disciplina
            </button>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto p-8">
          <div className="mx-auto max-w-5xl">
            {isSettings ? (
              <header className="mb-10 space-y-4">
                <h1 className="text-3xl font-bold tracking-tighter text-[#26343d]">
                  Configuración
                </h1>
                <p className="text-sm text-[#52616a]">
                  Ajustes del entorno V2. El capital de trabajo se gestiona en el protocolo
                  institucional.
                </p>
                <button
                  type="button"
                  onClick={openTreasury}
                  className="rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] px-6 py-3 text-sm font-bold text-white shadow-lg shadow-[#8B5CF6]/20"
                >
                  Abrir Capital Management Protocol
                </button>
              </header>
            ) : (
              <header className="mb-10 flex items-end justify-between gap-4">
                <div>
                  <h1 className="text-3xl font-bold tracking-tighter text-[#26343d]">
                    El Búnker
                  </h1>
                  <p className="mt-1 text-sm text-[#52616a]">
                    Centro de control para gestión conductual y riesgo.
                  </p>
                </div>
                <div>
                  <span className="inline-flex rounded-full border border-[#a4b4be]/30 bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
                    Actualizado ahora
                  </span>
                </div>
              </header>
            )}

            {!isSettings && (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                <div className="min-h-[180px] rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6" />
                <div className="min-h-[180px] rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6" />
                <div className="min-h-[180px] rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6" />
              </div>
            )}
          </div>
        </main>
      </div>

      <TreasuryModal
        open={treasuryOpen}
        onClose={() => setTreasuryOpen(false)}
        blocking={treasuryBlocking}
      />
    </div>
  )
}
