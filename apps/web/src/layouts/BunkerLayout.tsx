import { motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { EconomyTourModal } from '@/components/EconomyTourModal'
import { GlossaryModal } from '@/components/GlossaryModal'
import { OnboardingCompleteModal } from '@/components/OnboardingCompleteModal'
import { TreasuryModal } from '@/components/TreasuryModal'
import { IconRestart } from '@/components/bt2StitchIcons'
import {
  Bt2ChartBarsIcon,
  Bt2HistoryIcon,
  Bt2HomeIcon,
  Bt2SettingsIcon,
  Bt2ShieldCheckIcon,
  Bt2UserIcon,
  Bt2VaultIcon,
} from '@/components/icons/bt2Icons'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

function navItemClass(isActive: boolean) {
  return [
    'flex w-full items-center gap-3 rounded-none border-r-2 px-4 py-3 text-left text-sm font-semibold uppercase tracking-wide transition-colors',
    isActive
      ? 'border-[#8B5CF6] bg-[#eef4fa]/60 font-bold text-[#8B5CF6]'
      : 'border-transparent text-[#52616a] hover:bg-white/60',
  ].join(' ')
}

function mainModuleLabel(pathname: string): string | null {
  if (pathname === '/v2' || pathname.startsWith('/v2/sanctuary')) {
    return 'Santuario'
  }
  if (pathname.startsWith('/v2/vault')) return 'La Bóveda'
  if (pathname.startsWith('/v2/settlement')) return 'Liquidación'
  if (pathname.startsWith('/v2/daily-review')) return 'Cierre del día'
  if (pathname.startsWith('/v2/ledger')) return 'Libro mayor'
  if (pathname.startsWith('/v2/performance')) return 'Estrategia'
  if (pathname.startsWith('/v2/profile')) return 'Perfil'
  if (pathname.startsWith('/v2/settings')) return 'Ajustes'
  if (pathname.startsWith('/v2/dashboard')) return 'Santuario'
  return null
}

function bunkerRankLabel(dp: number): string {
  if (dp >= 5000) return 'Master'
  if (dp >= 3000) return 'Elite'
  if (dp >= 1500) return 'Sentinel'
  return 'Novice'
}

export default function BunkerLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const isSettings = location.pathname.startsWith('/v2/settings')
  const navLogPath = useRef('')

  const operatorName = useUserStore((s) => s.operatorName)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const syncDpBalance = useUserStore((s) => s.syncDpBalance)
  const endSession = useUserStore((s) => s.endSession)
  const onboardingPhaseAComplete = useUserStore((s) => s.onboardingPhaseAComplete)
  const hasSeenEconomyTour = useUserStore((s) => s.hasSeenEconomyTour)
  const completeOnboardingPhaseA = useUserStore((s) => s.completeOnboardingPhaseA)
  const completeEconomyTour = useUserStore((s) => s.completeEconomyTour)
  const confirmedBankrollCop = useBankrollStore((s) => s.confirmedBankrollCop)
  const checkDayBoundary = useSessionStore((s) => s.checkDayBoundary)

  const [dpPulseKey, setDpPulseKey] = useState(0)
  const [dpSyncing, setDpSyncing] = useState(false)
  const [dpSyncError, setDpSyncError] = useState<string | null>(null)
  const [treasuryOpen, setTreasuryOpen] = useState(false)
  const [onboardingPhaseAOpen, setOnboardingPhaseAOpen] = useState(false)
  const [economyTourOpen, setEconomyTourOpen] = useState(false)
  const [glossaryOpen, setGlossaryOpen] = useState(false)

  const treasuryBlocking = confirmedBankrollCop <= 0

  // US-FE-012: heartbeat de día operativo cada 60 segundos
  useEffect(() => {
    const runCheck = () => {
      const unlockedPickIds = useVaultStore.getState().unlockedPickIds
      const settledPickIds = useTradeStore.getState().settledPickIds
      const hasUnsettledPicks = unlockedPickIds.some(
        (id) => !settledPickIds.includes(id),
      )
      checkDayBoundary(new Date().toISOString(), hasUnsettledPicks)
    }
    runCheck()
    const timer = window.setInterval(runCheck, 60_000)
    return () => window.clearInterval(timer)
  }, [checkDayBoundary])

  useEffect(() => {
    if (confirmedBankrollCop === 0) {
      setTreasuryOpen(true)
    }
  }, [confirmedBankrollCop])

  useEffect(() => {
    const p = location.pathname
    if (p === navLogPath.current) return
    const label = mainModuleLabel(p)
    if (label) {
      console.info(`[BT2] Navegación: ${label} → ${p}`)
    }
    navLogPath.current = p
  }, [location.pathname])

  const equityLabel = useMemo(() => {
    if (confirmedBankrollCop <= 0) return 'Sin configurar'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(confirmedBankrollCop)
  }, [confirmedBankrollCop])

  // US-FE-011: callback tras confirmar treasury
  const handleTreasuryConfirm = () => {
    if (!onboardingPhaseAComplete) {
      setOnboardingPhaseAOpen(true)
    }
  }

  const handleOnboardingPhaseAComplete = async () => {
    const { ok } = await completeOnboardingPhaseA()
    if (!ok) {
      window.alert(
        'No se pudo acreditar el bono en el servidor. Revisa la conexión e inténtalo de nuevo.',
      )
      return
    }
    setOnboardingPhaseAOpen(false)
    if (!hasSeenEconomyTour) {
      setEconomyTourOpen(true)
    }
  }

  const handleEconomyTourComplete = () => {
    completeEconomyTour()
    setEconomyTourOpen(false)
  }

  const rankLabel = useMemo(
    () => bunkerRankLabel(disciplinePoints ?? 0),
    [disciplinePoints],
  )

  const refreshDpFromServer = () => {
    setDpSyncError(null)
    setDpSyncing(true)
    void syncDpBalance().then((ok) => {
      setDpSyncing(false)
      if (ok) setDpPulseKey((k) => k + 1)
      else setDpSyncError('No se pudo sincronizar el saldo DP. Reintenta.')
    })
  }

  const openTreasury = () => setTreasuryOpen(true)

  const handleLogout = () => {
    endSession()
    navigate('/v2/session', { replace: true })
  }

  const pageTitle = isSettings
    ? 'Configuración'
    : location.pathname.startsWith('/v2/vault')
      ? 'La Bóveda'
      : location.pathname.startsWith('/v2/settlement')
        ? 'Liquidación'
        : location.pathname.startsWith('/v2/daily-review')
          ? 'Cierre del día'
          : location.pathname.startsWith('/v2/ledger')
            ? 'Libro mayor'
            : location.pathname.startsWith('/v2/performance')
              ? 'Estrategia y rendimiento'
              : location.pathname.startsWith('/v2/profile')
                ? 'Perfil operador'
                : 'Santuario'

  const pageSubtitle = isSettings
    ? 'Preferencias del entorno V2. El capital de trabajo se define en el protocolo de gestión de capital.'
    : location.pathname.startsWith('/v2/vault')
      ? 'Oportunidades con valor esperado positivo (modelo canónico CDM); desbloqueo con DP.'
      : location.pathname.startsWith('/v2/settlement')
        ? 'Auditoría de resultado y reflexión obligatoria antes de archivar en ledger.'
        : location.pathname.startsWith('/v2/daily-review')
          ? 'Reconciliación del saldo real y sellado de la estación operativa.'
          : location.pathname.startsWith('/v2/ledger')
            ? 'Auditoría histórica de liquidaciones y disciplina.'
            : location.pathname.startsWith('/v2/performance')
              ? 'Métricas macro y curva de equity desde el ledger.'
              : location.pathname.startsWith('/v2/profile')
                ? 'Progresión, medallas y recalibración de identidad.'
                : 'Panel de inicio del entorno de control conductual.'

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
              {(disciplinePoints ?? 0).toLocaleString('es-CO')} DP
            </motion.span>
          </div>
          <button
            type="button"
            onClick={openTreasury}
            className="hidden min-w-0 flex-col items-start rounded-xl border border-[#a4b4be]/20 bg-white/60 px-3 py-1.5 text-left transition-colors hover:bg-white sm:flex"
            title="Abrir protocolo de capital"
          >
            <span className="text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
              Patrimonio total
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
              Capital
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
              Rango: {rankLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="shrink-0 rounded-lg border border-[#a4b4be]/35 bg-white/70 px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-[#52616a] transition-colors hover:border-[#9e3f4e]/40 hover:text-[#9e3f4e]"
          >
            Cerrar sesión
          </button>
          <div className="h-9 w-9 shrink-0 rounded-full border border-[#8B5CF6]/20 bg-[#eef4fa]" />
        </div>
      </header>

      <nav
        aria-label="Navegación principal V2"
        className="flex shrink-0 gap-1 overflow-x-auto border-b border-[#26343d]/15 bg-[#eef4fa] px-2 py-2 lg:hidden"
      >
        <NavLink
          to="/v2/sanctuary"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Santuario
        </NavLink>
        <NavLink
          to="/v2/vault"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          La Bóveda
        </NavLink>
        <NavLink
          to="/v2/daily-review"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Cierre
        </NavLink>
        <NavLink
          to="/v2/ledger"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Ledger
        </NavLink>
        <NavLink
          to="/v2/performance"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Métricas
        </NavLink>
        <NavLink
          to="/v2/admin/dsr-accuracy"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Precisión DSR
        </NavLink>
        <NavLink
          to="/v2/profile"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Perfil
        </NavLink>
        <NavLink
          to="/v2/settings"
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-bold uppercase tracking-wide',
              isActive
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a]',
            ].join(' ')
          }
        >
          Ajustes
        </NavLink>
      </nav>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <aside
          className="hidden w-64 shrink-0 flex-col border-r border-[#26343d]/15 bg-[#eef4fa] py-8 px-4 font-sans lg:flex"
          role="navigation"
          aria-label="Navegación lateral V2"
        >
          <nav className="flex-1 space-y-1">
            <NavLink
              to="/v2/sanctuary"
              end
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2HomeIcon className="h-5 w-5" />
              </span>
              Santuario
            </NavLink>
            <NavLink
              to="/v2/vault"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2VaultIcon className="h-5 w-5" />
              </span>
              La Bóveda
            </NavLink>
            <NavLink
              to="/v2/daily-review"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2HistoryIcon className="h-5 w-5" />
              </span>
              Cierre del día
            </NavLink>
            <NavLink
              to="/v2/ledger"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2HistoryIcon className="h-5 w-5" />
              </span>
              Libro mayor
            </NavLink>
            <NavLink
              to="/v2/performance"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2ChartBarsIcon className="h-5 w-5" />
              </span>
              Estrategia
            </NavLink>
            <NavLink
              to="/v2/admin/dsr-accuracy"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2ShieldCheckIcon className="h-5 w-5" />
              </span>
              Precisión DSR
            </NavLink>
            <NavLink
              to="/v2/profile"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2UserIcon className="h-5 w-5" />
              </span>
              Perfil
            </NavLink>
            <NavLink
              to="/v2/settings"
              className={({ isActive }) => navItemClass(isActive)}
            >
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center">
                <Bt2SettingsIcon className="h-5 w-5" />
              </span>
              Ajustes
            </NavLink>
          </nav>

          <div className="mt-auto space-y-2">
            <button
              type="button"
              onClick={() => setGlossaryOpen(true)}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#a4b4be]/30 bg-white/70 py-2.5 text-xs font-bold tracking-tight text-[#52616a] uppercase hover:bg-white transition-colors"
            >
              Glosario
            </button>
            <div className="space-y-1">
              <button
                type="button"
                onClick={refreshDpFromServer}
                disabled={dpSyncing}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-3 text-xs font-bold tracking-tight text-white uppercase shadow-lg shadow-[#8B5CF6]/20 disabled:cursor-wait disabled:opacity-70"
              >
                <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-white">
                  <IconRestart
                    className={`h-5 w-5 ${dpSyncing ? 'animate-spin' : ''}`}
                  />
                </span>
                {dpSyncing ? 'Sincronizando…' : 'Sincronizar DP'}
              </button>
              {dpSyncError ? (
                <p className="text-center text-[10px] font-semibold text-[#9b1c1c]">
                  {dpSyncError}
                </p>
              ) : null}
            </div>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto p-8">
          <div className="mx-auto max-w-7xl">
            {isSettings ? (
              <header className="mb-10 space-y-4">
                <h1 className="text-3xl font-bold tracking-tighter text-[#26343d]">
                  {pageTitle}
                </h1>
                <p className="text-sm text-[#52616a]">{pageSubtitle}</p>
                <button
                  type="button"
                  onClick={openTreasury}
                  className="rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] px-6 py-3 text-sm font-bold text-white shadow-lg shadow-[#8B5CF6]/20"
                >
                  Abrir protocolo de capital
                </button>
              </header>
            ) : null}

            <Outlet />
          </div>
        </main>
      </div>

      <TreasuryModal
        open={treasuryOpen}
        onClose={() => setTreasuryOpen(false)}
        blocking={treasuryBlocking}
        onConfirm={handleTreasuryConfirm}
      />

      {/* US-FE-011: cierre de onboarding fase A (solo primera vez) */}
      <OnboardingCompleteModal
        open={onboardingPhaseAOpen}
        operatorName={operatorName}
        bankrollFormatted={equityLabel}
        onContinueToTour={handleOnboardingPhaseAComplete}
      />

      {/* US-FE-011: tour de economía DP fase B (solo primera vez) */}
      <EconomyTourModal
        open={economyTourOpen}
        onComplete={handleEconomyTourComplete}
      />

      {/* US-FE-029: glosario de términos del protocolo */}
      <GlossaryModal
        open={glossaryOpen}
        onClose={() => setGlossaryOpen(false)}
      />
    </div>
  )
}
