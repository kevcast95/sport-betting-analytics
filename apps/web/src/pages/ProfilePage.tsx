import { useEffect, useMemo } from 'react'
import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import {
  IconBolt,
  IconCalendar,
  IconDiamond,
  IconLock,
  IconMenuBook,
  IconSecurity,
  IconShieldHeart,
  IconShowChart,
  IconToken,
  IconVerified,
  IconWallet,
  IconWaterDrop,
} from '@/components/bt2StitchIcons'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { OPERATOR_PROFILE_LABEL_ES } from '@/lib/diagnosticScoring'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { ledgerAggregateMetrics } from '@/lib/ledgerAnalytics'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'

function tierFromDp(dp: number): { name: string; next: number } {
  if (dp >= 5000) return { name: 'Master', next: dp }
  if (dp >= 3000) return { name: 'Elite', next: 5000 }
  if (dp >= 1500) return { name: 'Sentinel', next: 3000 }
  return { name: 'Novato', next: 1500 }
}

function seniorityDays(ledger: { settledAt: string }[]): number {
  if (ledger.length === 0) return 0
  const t = Math.min(...ledger.map((r) => new Date(r.settledAt).getTime()))
  return Math.max(0, Math.floor((Date.now() - t) / 86_400_000))
}

export default function ProfilePage() {
  const operatorName = useUserStore((s) => s.operatorName)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const profile = useUserStore((s) => s.operatorProfile)
  const integrity = useUserStore((s) => s.systemIntegrity)
  const hasDiagnostic = useUserStore((s) => s.hasCompletedDiagnostic)
  const ledger = useTradeStore((s) => s.ledger)

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const metrics = useMemo(() => ledgerAggregateMetrics(ledger), [ledger])
  const tier = tierFromDp(disciplinePoints)
  const pctToNext =
    tier.next <= disciplinePoints
      ? 100
      : Math.min(100, (disciplinePoints / tier.next) * 100)

  const rSvg = 88
  const c = 2 * Math.PI * rSvg
  const dashOffset = c * (1 - pctToNext / 100)

  const rankTopPct = Math.max(0.1, 100 - disciplinePoints / 50).toFixed(1)
  const activeStreakDays = useMemo(() => {
    if (ledger.length === 0) return 0
    const days = new Set(
      ledger.map((r) => new Date(r.settledAt).toISOString().slice(0, 10)),
    )
    return Math.min(42, days.size)
  }, [ledger])

  const seniority = seniorityDays(ledger)
  const avgDpPerCycle =
    ledger.length > 0
      ? metrics.disciplineDpFromSettlements / ledger.length
      : 0

  const lastAchievedLabel =
    ledger.length > 0
      ? new Date(
          [...ledger].sort(
            (a, b) =>
              new Date(b.settledAt).getTime() - new Date(a.settledAt).getTime(),
          )[0].settledAt,
        ).toLocaleDateString('es-CO', { month: 'short', year: 'numeric' })
      : '—'

  const medals = [
    {
      id: 'm1',
      title: 'Adherencia al protocolo (30 días)',
      unlocked: ledger.length >= 5,
      icon: IconVerified,
    },
    {
      id: 'm2',
      title: 'Drawdown máximo contenido',
      unlocked: disciplinePoints >= 2000,
      icon: IconShieldHeart,
    },
    {
      id: 'm3',
      title: 'Maestro de alta liquidez',
      unlocked: metrics.winRatePct >= 55 && ledger.length >= 8,
      icon: IconWaterDrop,
    },
    {
      id: 'm4',
      title: 'Guardián de la bóveda',
      unlocked: disciplinePoints >= 4000,
      icon: IconLock,
    },
  ]

  const operatorTitle =
    hasDiagnostic && profile != null
      ? `${OPERATOR_PROFILE_LABEL_ES[profile]} · consultor de estrategia`
      : 'Operador en calibración'

  const recalibrateAvailable = false

  return (
    <div
      className="mx-auto w-full max-w-7xl space-y-12"
      aria-label="Perfil operador"
    >
      <section className="grid grid-cols-1 items-stretch gap-8 lg:grid-cols-12">
        <div className="relative flex flex-col justify-between overflow-hidden rounded-xl bg-white p-10 lg:col-span-8">
          <div className="relative z-10">
            <h3 className="mb-2 text-xs font-medium uppercase tracking-[0.1em] text-[#52616a]">
              Usuario autenticado
            </h3>
            <h1 className="text-4xl font-extrabold tracking-tight text-[#26343d]">
              {operatorName ?? 'Operador'}
            </h1>
            <p className="mt-2 flex items-center gap-2 font-medium text-[#6d3bd7]">
              <IconVerified className="h-5 w-5 shrink-0 text-[#6d3bd7]" />
              {operatorTitle}
            </p>
          </div>
          <div className="relative z-10 mt-12 grid grid-cols-3 gap-6">
            <div>
              <p className="mb-1 text-xs uppercase tracking-wider text-[#52616a]">
                Rank
              </p>
              <p
                className="text-xl font-bold text-[#26343d]"
                style={monoStyle}
              >
                Top {rankTopPct}%
              </p>
            </div>
            <div>
              <p className="mb-1 text-xs uppercase tracking-wider text-[#52616a]">
                Racha activa
              </p>
              <p
                className="text-xl font-bold text-[#26343d]"
                style={monoStyle}
              >
                {activeStreakDays} {activeStreakDays === 1 ? 'día' : 'días'}
              </p>
            </div>
            <div>
              <p className="mb-1 text-xs uppercase tracking-wider text-[#52616a]">
                Consistencia
              </p>
              <p
                className="text-xl font-bold text-[#6d3bd7]"
                style={monoStyle}
              >
                {ledger.length > 0 ? `${metrics.winRatePct.toFixed(1)}%` : '—'}
              </p>
            </div>
          </div>
          <div
            className="pointer-events-none absolute right-[-10%] top-[-20%] h-64 w-64 rounded-full bg-[#6d3bd7]/5 blur-3xl"
            aria-hidden
          />
        </div>

        <div className="flex flex-col items-center justify-center rounded-xl border border-[#a4b4be]/10 bg-white p-10 text-center lg:col-span-4">
          <div className="relative mb-6 h-48 w-48">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 192 192">
              <circle
                cx="96"
                cy="96"
                r={rSvg}
                fill="transparent"
                stroke="#ddeaf3"
                strokeWidth={6}
              />
              <circle
                cx="96"
                cy="96"
                r={rSvg}
                fill="transparent"
                stroke="#612aca"
                strokeWidth={8}
                strokeDasharray={c}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span
                className="text-4xl font-bold text-[#26343d]"
                style={monoStyle}
              >
                {Math.round(pctToNext)}%
              </span>
              <span className="mt-1 text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                Hacia {tier.name}
              </span>
            </div>
          </div>
          <p className="text-sm font-medium text-[#52616a]">
            Próximo hito:{' '}
            <span className="text-[#26343d]">
              {tier.next > disciplinePoints
                ? `${tier.next.toLocaleString('es-CO')} DP`
                : 'Apex desbloqueado'}
            </span>
          </p>
        </div>
      </section>

      {hasDiagnostic ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-[#a4b4be]/25 p-4">
            <p className="text-[10px] font-bold uppercase text-[#52616a]">
              Perfil diagnóstico
            </p>
            <p className="mt-2 text-lg font-bold text-[#26343d]">
              {profile != null ? OPERATOR_PROFILE_LABEL_ES[profile] : '—'}
            </p>
          </div>
          <div className="rounded-xl border border-[#a4b4be]/25 p-4">
            <p className="text-[10px] font-bold uppercase text-[#52616a]">
              Integridad
            </p>
            <p
              className="mt-2 font-mono text-lg font-bold tabular-nums"
              style={monoStyle}
            >
              {integrity != null ? integrity.toFixed(3) : '—'}
            </p>
          </div>
        </div>
      ) : null}

      <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="rounded-xl border border-transparent bg-[#eef4fa] p-6 transition-all hover:border-[#6d3bd7]/20">
          <p className="mb-4 text-xs font-bold uppercase tracking-widest text-[#52616a]">
            DP total ganados
          </p>
          <div className="flex items-end justify-between">
            <span
              className="text-3xl font-bold text-[#26343d]"
              style={monoStyle}
            >
              {disciplinePoints.toLocaleString('es-CO')}
            </span>
            <IconWallet className="h-7 w-7 text-[#6d3bd7]" />
          </div>
        </div>
        <div className="rounded-xl border border-transparent bg-[#eef4fa] p-6 transition-all hover:border-[#6d3bd7]/20">
          <p className="mb-4 text-xs font-bold uppercase tracking-widest text-[#52616a]">
            Disciplina media / ciclo
          </p>
          <div className="flex items-end justify-between">
            <span
              className="text-3xl font-bold text-[#26343d]"
              style={monoStyle}
            >
              {ledger.length > 0 ? avgDpPerCycle.toFixed(1) : '—'}
            </span>
            <IconShowChart className="h-7 w-7 text-[#914d00]" />
          </div>
        </div>
        <div className="rounded-xl border border-transparent bg-[#eef4fa] p-6 transition-all hover:border-[#6d3bd7]/20">
          <p className="mb-4 text-xs font-bold uppercase tracking-widest text-[#52616a]">
            Antigüedad de cuenta
          </p>
          <div className="flex items-end justify-between">
            <span
              className="text-3xl font-bold text-[#26343d]"
              style={monoStyle}
            >
              {seniority}
              <span className="ml-1 text-sm font-normal">DÍAS</span>
            </span>
            <IconCalendar className="h-7 w-7 text-[#52616a]" />
          </div>
        </div>
      </section>

      <section>
        <div className="mb-8 flex items-baseline justify-between gap-4">
          <h3 className="text-2xl font-bold text-[#26343d]">
            Hitos de disciplina
          </h3>
          <span className="text-xs font-bold uppercase tracking-widest text-[#52616a]">
            Archivo histórico
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {medals.map((m) => {
            const Ico = m.icon
            return (
              <div
                key={m.id}
                className={[
                  'group flex flex-col items-center rounded-xl border p-6 text-center transition-all',
                  m.unlocked
                    ? 'border-[#a4b4be]/20 bg-white hover:border-[#6d3bd7]'
                    : 'border-dashed border-[#a4b4be]/30 bg-white/80',
                ].join(' ')}
              >
                <div
                  className={[
                    'mb-4 flex h-16 w-16 items-center justify-center rounded-full border transition-colors',
                    m.unlocked
                      ? 'border-[#e9ddff] text-[#6d3bd7] group-hover:bg-[#e9ddff]'
                      : 'border-[#a4b4be]/20 text-[#a4b4be]',
                  ].join(' ')}
                >
                  <Ico className="h-8 w-8" />
                </div>
                <h4
                  className={[
                    'mb-1 text-sm font-bold leading-tight',
                    m.unlocked ? 'text-[#26343d]' : 'text-[#52616a]',
                  ].join(' ')}
                >
                  {m.title}
                </h4>
                <p className="text-[10px] uppercase tracking-tighter text-[#52616a]">
                  {m.unlocked
                    ? `Logrado: ${lastAchievedLabel}`
                    : m.id === 'm4'
                      ? 'Bloqueado'
                      : 'En progreso'}
                </p>
              </div>
            )
          })}
        </div>
      </section>

      <section className="relative overflow-hidden rounded-xl border border-[#a4b4be]/10 bg-white p-10">
        <h3 className="mb-12 text-2xl font-bold text-[#26343d]">
          Hoja de ruta
        </h3>
        <div className="relative">
          <div className="absolute left-0 top-8 hidden h-[2px] w-full bg-[#ddeaf3] md:block" />
          <div className="relative z-10 grid grid-cols-1 gap-8 md:grid-cols-4">
            <div className="space-y-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#6d3bd7] text-white shadow-lg ring-8 ring-white">
                <IconToken className="h-7 w-7 text-white" />
              </div>
              <div>
                <h5 className="text-sm font-bold text-[#26343d]">
                  Acceso Alpha-9
                </h5>
                <p className="mt-1 text-xs font-medium text-[#6d3bd7]">
                  Desbloqueado
                </p>
                <p className="mt-2 text-xs text-[#52616a]">
                  Permisos de análisis algorítmico completos.
                </p>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#6d3bd7] text-white shadow-lg ring-8 ring-white">
                <IconMenuBook className="h-7 w-7 text-white" />
              </div>
              <div>
                <h5 className="text-sm font-bold text-[#26343d]">
                  Libro mayor estratégico
                </h5>
                <p className="mt-1 text-xs font-medium text-[#6d3bd7]">
                  Desbloqueado
                </p>
                <p className="mt-2 text-xs text-[#52616a]">
                  Archivo histórico de profundidad activo.
                </p>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-[#6d3bd7] bg-[#d5e5ef] text-[#6d3bd7] shadow-lg ring-8 ring-white">
                <IconBolt className="h-7 w-7" />
              </div>
              <div>
                <h5 className="text-sm font-bold text-[#26343d]">
                  Protocolo Sigma-2
                </h5>
                <p className="mt-1 text-xs font-medium text-[#914d00]">
                  {disciplinePoints >= 2000
                    ? 'Desbloqueado'
                    : 'Desbloqueo a 2.000 DP'}
                </p>
                <p className="mt-2 text-xs text-[#52616a]">
                  Motor de mitigación de riesgo en tiempo real.
                </p>
              </div>
            </div>
            <div className="space-y-4 opacity-40 grayscale">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#ddeaf3] text-[#52616a] ring-8 ring-white">
                <IconDiamond className="h-7 w-7" />
              </div>
              <div>
                <h5 className="text-sm font-bold text-[#26343d]">
                  Portal private equity
                </h5>
                <p className="mt-1 text-xs font-medium text-[#52616a]">
                  Bloqueado
                </p>
                <p className="mt-2 text-xs text-[#52616a]">
                  Integración directa con fondos y herramientas de gestión.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="flex justify-center pt-4">
        <div className="flex items-center gap-6 rounded-xl border border-[#6d3bd7]/5 bg-white p-6 shadow-[0px_20px_40px_rgba(38,52,61,0.06)]">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#6d3bd7]/10">
              <IconSecurity className="h-6 w-6 text-[#6d3bd7]" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                Estado del protocolo
              </p>
              <p
                className="text-lg font-bold text-[#6d3bd7]"
                style={monoStyle}
              >
                ACTIVO
              </p>
            </div>
          </div>
          <div className="h-10 w-px bg-[#a4b4be]/30" />
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#914d00]/10">
              <Bt2ShieldCheckIcon className="h-6 w-6 text-[#914d00]" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                Discipline Shield
              </p>
              <p className="text-lg font-bold text-[#26343d]" style={monoStyle}>
                {disciplinePoints.toLocaleString('es-CO')}{' '}
                <span className="text-xs font-normal">pts</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-[#26343d]/10 bg-[#eef4fa]/50 p-5">
        <h2 className="text-sm font-bold text-[#26343d]">
          Centro de recalibración
        </h2>
        <p className="mt-2 text-sm text-[#52616a]">
          Repetir el diagnóstico quedará habilitado tras 30 días y 50 entradas en
          ledger (US-FE-010).
        </p>
        {recalibrateAvailable ? (
          <Link
            to="/v2/diagnostic"
            className="mt-4 inline-block rounded-lg bg-[#8B5CF6] px-4 py-2 text-sm font-bold text-white"
          >
            Recalibrar identidad
          </Link>
        ) : (
          <button
            type="button"
            disabled
            className="mt-4 cursor-not-allowed rounded-lg border border-[#a4b4be]/40 bg-white/60 px-4 py-2 text-sm font-semibold text-[#a4b4be]"
          >
            Recalibración no disponible
          </button>
        )}
      </div>
    </div>
  )
}
