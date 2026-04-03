import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import {
  Bt2ChartBarsIcon,
  Bt2HistoryIcon,
  Bt2PlusIcon,
  Bt2ShieldCheckIcon,
  Bt2UserIcon,
  Bt2VaultIcon,
} from '@/components/icons/bt2Icons'
import { useUserStore } from '@/store/useUserStore'

export default function BunkerLayout() {
  const {
    operatorName,
    disciplinePoints,
    equityCop,
    incrementDisciplinePoints,
  } = useUserStore()

  const [dpPulseKey, setDpPulseKey] = useState(0)

  const equityLabel = useMemo(() => {
    if (equityCop == null) return '—'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(equityCop)
  }, [equityCop])

  const incPositiveAction = () => {
    incrementDisciplinePoints(25)
    setDpPulseKey((k) => k + 1)
  }

  return (
    <div className="flex h-full w-[100vw] flex-col overflow-hidden bg-[#f6fafe] text-[#26343d]">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between gap-4 border-b border-[#26343d]/15 bg-[#f6fafe]/90 px-6 py-3 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <span className="text-xl font-bold tracking-tighter text-[#26343d]">
            BetTracker 2.0
          </span>
          <span className="hidden h-6 w-[1px] bg-[#6e7d86]/30 sm:inline-block" />
          <div className="flex items-center gap-3 rounded-xl border border-[#a4b4be]/30 bg-[#eef4fa] px-4 py-2">
            <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-[#8B5CF6]">
              <Bt2ShieldCheckIcon className="h-5 w-5" />
            </span>
            <motion.span
              key={dpPulseKey}
              initial={{ scale: 0.98 }}
              animate={{ scale: 1.02 }}
              transition={{ duration: 0.15 }}
              className="font-mono text-sm font-bold tabular-nums text-[#26343d]"
            >
              {disciplinePoints.toLocaleString('es-CO')} DP
            </motion.span>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-widest text-[#6e7d86] font-bold">
              Equity
            </span>
            <span className="font-mono text-sm tabular-nums text-[#26343d]">
              {equityLabel}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs font-bold tracking-wider text-[#26343d]">
              {operatorName ?? 'Operador'}
            </p>
            <p className="text-[10px] uppercase tracking-widest font-bold text-[#8B5CF6]">
              Nivel: Elite
            </p>
          </div>
          <div className="h-9 w-9 rounded-full border border-[#8B5CF6]/20 bg-[#eef4fa]" />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <aside className="hidden w-64 flex-col border-r border-[#26343d]/15 bg-[#eef4fa] py-8 px-4 md:flex">
          <nav className="flex-1 space-y-1">
            <button
              type="button"
              className="flex w-full items-center gap-3 rounded-none border-r-2 border-[#8B5CF6] bg-[#eef4fa]/60 px-4 py-3 text-left font-bold text-[#8B5CF6]"
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2VaultIcon className="h-5 w-5" />
              </span>
              El Búnker
            </button>
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
          </nav>

          <div className="mt-auto">
            <button
              type="button"
              onClick={incPositiveAction}
              className="w-full rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-3 text-white font-bold tracking-tight text-xs uppercase flex items-center justify-center gap-2 shadow-lg shadow-[#8B5CF6]/20"
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
                <span className="inline-flex rounded-full border border-[#a4b4be]/30 bg-white px-3 py-1 text-[10px] uppercase tracking-widest font-bold text-[#6e7d86]">
                  Actualizado ahora
                </span>
              </div>
            </header>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6 min-h-[180px]" />
              <div className="rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6 min-h-[180px]" />
              <div className="rounded-xl border border-[#a4b4be]/30 bg-white/80 p-6 min-h-[180px]" />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
