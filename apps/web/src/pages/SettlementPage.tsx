import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import {
  IconAnalytics,
  IconPsychology,
  IconRestart,
  IconTrendingDown,
  IconTrendingUp,
  IconWallet,
} from '@/components/bt2StitchIcons'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { vaultMockPicks } from '@/data/vaultMockPicks'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { ledgerAggregateMetrics } from '@/lib/ledgerAnalytics'
import { mockDecimalCuotaForPick } from '@/lib/pickSettlementMock'
import {
  computeSettlementPnlCop,
  potentialProfitCop,
  type SettlementOutcome,
} from '@/lib/settlementPnL'
import { computeUnitValue } from '@/lib/treasuryMath'
import { useBankrollStore } from '@/store/useBankrollStore'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import { Navigate, useNavigate, useParams } from 'react-router-dom'

const OUTCOME_LABEL: Record<SettlementOutcome, string> = {
  PROFIT: 'Profit',
  LOSS: 'Loss',
  PUSH: 'Push / Void',
}

function formatCop(n: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(n)
}

function vaultLevelLabel(dp: number): string {
  if (dp >= 4000) return 'Vault Master · Nivel 5'
  if (dp >= 3000) return 'Vault Master · Nivel 4'
  if (dp >= 2000) return 'Vault Sentinel · Nivel 3'
  if (dp >= 1500) return 'Vault Sentinel · Nivel 2'
  return 'Vault Operativo · Nivel 1'
}

export default function SettlementPage() {
  const { pickId = '' } = useParams<{ pickId: string }>()
  const navigate = useNavigate()
  const pick = useMemo(
    () => vaultMockPicks.find((p) => p.id === pickId) ?? null,
    [pickId],
  )
  const stationLocked = useSessionStore(selectStationLocked)
  const unlocked = useVaultStore((s) => s.unlockedPickIds.includes(pickId))
  const settled = useTradeStore((s) => s.settledPickIds.includes(pickId))
  const ledger = useTradeStore((s) => s.ledger)
  const finalizeSettlement = useTradeStore((s) => s.finalizeSettlement)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)

  const bankroll = useBankrollStore((s) => s.confirmedBankrollCop)
  const stakePct = useBankrollStore((s) => s.selectedStakePct)

  const [outcome, setOutcome] = useState<SettlementOutcome | null>(null)
  const [reflection, setReflection] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

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

  const decimalCuota = pick ? mockDecimalCuotaForPick(pick) : Number.NaN
  const stakeCop = computeUnitValue(bankroll, stakePct)
  const pnlPreview =
    outcome != null && Number.isFinite(stakeCop)
      ? computeSettlementPnlCop(stakeCop, decimalCuota, outcome)
      : Number.NaN
  const pnlPotential = Number.isFinite(stakeCop)
    ? potentialProfitCop(stakeCop, decimalCuota)
    : Number.NaN

  const canSubmit =
    outcome != null &&
    reflection.trim().length >= 10 &&
    Number.isFinite(stakeCop) &&
    stakeCop > 0

  const newBankrollPreview =
    Number.isFinite(pnlPreview) && Number.isFinite(bankroll)
      ? Math.max(0, bankroll + pnlPreview)
      : Number.NaN

  if (!pick) return <Navigate to="/v2/vault" replace />
  if (stationLocked) return <Navigate to="/v2/vault" replace />
  if (!unlocked) return <Navigate to="/v2/vault" replace />
  if (settled) return <Navigate to="/v2/vault" replace />

  const onRequestConfirm = () => {
    if (!canSubmit || outcome == null) return
    setConfirmOpen(true)
  }

  const onConfirmAudit = () => {
    if (!canSubmit || outcome == null) return
    const res = finalizeSettlement({
      pickId,
      outcome,
      reflection,
      stakeCop,
      decimalCuota,
    })
    setConfirmOpen(false)
    if (!res.ok) return
    setToast('Protocolo cumplido. La disciplina es el verdadero profit.')
    window.setTimeout(() => navigate('/v2/vault', { replace: true }), 2200)
  }

  return (
    <div className="w-full" aria-label="Terminal de liquidación">
      {toast ? (
        <div
          className="fixed bottom-24 left-1/2 z-[80] max-w-md -translate-x-1/2 rounded-lg border border-[#8B5CF6]/25 bg-[#f6fafe] px-5 py-3 text-center text-sm font-medium text-[#26343d] shadow-lg lg:bottom-8"
          role="status"
        >
          {toast}
        </div>
      ) : null}

      <div className="mb-10 lg:mb-12">
        <div className="mb-2 flex items-center text-xs font-semibold uppercase tracking-widest text-[#52616a]">
          <span>La Bóveda</span>
          <span className="mx-2 text-[#a4b4be]" aria-hidden>
            /
          </span>
          <span className="text-[#6d3bd7]">Terminal de liquidación</span>
        </div>
        <h1 className="text-3xl font-black tracking-tight text-[#26343d] sm:text-4xl">
          Auditoría ID:{' '}
          <span className="font-mono font-bold" style={monoStyle}>
            #{pick.id.toUpperCase()}
          </span>
        </h1>
      </div>

      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-7">
          <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-8">
            <div className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-start">
              <div>
                <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                  Especificación del activo
                </p>
                <h2 className="mb-2 text-2xl font-bold tracking-tight text-[#26343d] sm:text-3xl">
                  {pick.titulo}
                </h2>
                <p className="text-sm text-[#52616a]">
                  {pick.marketClass} · Pick CDM
                </p>
              </div>
              <div className="text-left sm:text-right">
                <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                  Mercado
                </p>
                <div className="inline-block rounded-lg bg-[#e9ddff] px-4 py-2 text-sm font-bold text-[#6d3bd7]">
                  {pick.marketClass}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-6 border-t border-[#a4b4be]/10 pt-6 sm:grid-cols-3">
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Precio de entrada
                </p>
                <p className="font-mono text-xl text-[#26343d]" style={monoStyle}>
                  {decimalCuota.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Capital en riesgo
                </p>
                <p
                  className="font-mono text-xl font-semibold text-[#6d3bd7]"
                  style={monoStyle}
                >
                  {Number.isFinite(stakeCop) ? formatCop(Math.round(stakeCop)) : '—'}
                </p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  PnL potencial
                </p>
                <p
                  className="font-mono text-xl font-semibold text-[#6d3bd7]"
                  style={monoStyle}
                >
                  {Number.isFinite(pnlPotential)
                    ? `+${formatCop(Math.round(pnlPotential))}`
                    : '—'}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-[#eef4fa] p-8">
            <div className="mb-6 flex items-center gap-3">
              <IconPsychology className="shrink-0 text-[#6d3bd7]" />
              <h3 className="text-lg font-bold tracking-tight text-[#26343d]">
                Traducción humana
              </h3>
            </div>
            <div className="space-y-4 text-sm leading-relaxed text-[#52616a]">
              <p>{pick.traduccionHumana}</p>
              <p>
                La sugerencia actúa como{' '}
                <span className="font-semibold text-[#26343d]">
                  neutralizador de varianza
                </span>
                : no se persigue solo el acierto puntual, sino la adherencia al
                protocolo de tamaño y registro.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6 lg:col-span-5">
          <div className="sticky top-24 rounded-xl border border-[#a4b4be]/15 bg-white p-8 shadow-[0px_20px_40px_rgba(38,52,61,0.06)]">
            <div className="mb-8 flex items-center justify-between gap-4">
              <h3 className="text-xl font-bold tracking-tight text-[#26343d]">
                Zona de liquidación
              </h3>
              <div className="flex items-center gap-2 rounded-full border border-[#6d3bd7]/20 bg-[#6d3bd7]/10 px-3 py-1">
                <Bt2ShieldCheckIcon className="h-4 w-4 text-[#6d3bd7]" />
                <span
                  className="font-mono text-xs font-bold tracking-tight text-[#6d3bd7]"
                  style={monoStyle}
                >
                  DP REWARD: +25
                </span>
              </div>
            </div>
            <p className="mb-8 text-sm leading-snug text-[#52616a]">
              Confirma el resultado de la posición para conciliar el ledger y
              actualizar tu disciplina.
            </p>
            <div className="mb-10 space-y-3">
              <button
                type="button"
                onClick={() => setOutcome('PROFIT')}
                className={[
                  'flex w-full items-center justify-between rounded-xl px-6 py-4 font-bold text-white transition-transform active:scale-[0.98]',
                  outcome === 'PROFIT'
                    ? 'bg-gradient-to-r from-[#6d3bd7] to-[#612aca] ring-2 ring-[#8B5CF6]'
                    : 'bg-gradient-to-r from-[#6d3bd7] to-[#612aca]',
                ].join(' ')}
              >
                <span>Profit</span>
                <IconTrendingUp className="text-white" />
              </button>
              <button
                type="button"
                onClick={() => setOutcome('LOSS')}
                className={[
                  'flex w-full items-center justify-between rounded-xl bg-[#ddeaf3] px-6 py-4 font-bold text-[#914d00] transition-colors hover:bg-[#d5e5ef] active:scale-[0.98]',
                  outcome === 'LOSS' ? 'ring-2 ring-[#914d00]/40' : '',
                ].join(' ')}
              >
                <span>Loss</span>
                <IconTrendingDown />
              </button>
              <button
                type="button"
                onClick={() => setOutcome('PUSH')}
                className={[
                  'flex w-full items-center justify-between rounded-xl bg-[#eef4fa] px-6 py-4 font-bold text-[#52616a] transition-colors hover:bg-[#ddeaf3] active:scale-[0.98]',
                  outcome === 'PUSH' ? 'ring-2 ring-[#6e7d86]/40' : '',
                ].join(' ')}
              >
                <span>Push / Void</span>
                <IconRestart />
              </button>
            </div>
            <div className="border-t border-[#a4b4be]/15 pt-8">
              <label
                htmlFor="bt2-settlement-reflection"
                className="mb-3 block text-xs font-semibold uppercase tracking-widest text-[#52616a]"
              >
                Estado emocional post-partido
              </label>
              <textarea
                id="bt2-settlement-reflection"
                rows={5}
                value={reflection}
                onChange={(e) => setReflection(e.target.value)}
                placeholder="Describe tu reacción a la varianza… ¿mantuviste el plan?"
                className="min-h-[120px] w-full rounded-xl border-0 bg-[#ddeaf3] p-4 text-sm text-[#26343d] placeholder:text-[#52616a]/40 focus:ring-1 focus:ring-[#6d3bd7]"
              />
              <p className="mt-2 text-[10px] italic text-[#52616a]">
                * Este dato alimenta el índice de equilibrio emocional del
                protocolo.
              </p>
            </div>
            <div className="mt-8 flex flex-wrap gap-4">
              <button
                type="button"
                disabled={!canSubmit}
                onClick={onRequestConfirm}
                className="rounded-xl bg-[#26343d] px-6 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Confirmar auditoría
              </button>
              <button
                type="button"
                onClick={() => navigate('/v2/vault')}
                className="py-3 text-sm font-semibold text-[#52616a] hover:text-[#26343d]"
              >
                Volver a la bóveda
              </button>
            </div>
          </div>
        </div>
      </div>

      <section className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-4">
        <div className="flex items-center rounded-xl border border-[#a4b4be]/10 bg-white p-6">
          <div className="mr-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#6d3bd7]/10">
            <IconWallet className="text-[#6d3bd7]" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
              Saldo vault (tesorería)
            </p>
            <p className="font-mono text-xl font-semibold text-[#26343d]" style={monoStyle}>
              {bankroll > 0 ? formatCop(Math.round(bankroll)) : '—'}
            </p>
          </div>
        </div>
        <div className="flex items-center rounded-xl border border-[#a4b4be]/10 bg-white p-6">
          <div className="mr-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#6d3bd7]/10">
            <IconAnalytics className="text-[#6d3bd7]" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
              Win rate (ledger)
            </p>
            <p className="font-mono text-xl font-semibold text-[#26343d]" style={monoStyle}>
              {ledger.length > 0 ? `${metrics.winRatePct.toFixed(1)}%` : '—'}
            </p>
          </div>
        </div>
        <div className="relative flex items-center justify-between overflow-hidden rounded-xl bg-[#6d3bd7] p-6 text-white md:col-span-2">
          <div className="relative z-10">
            <p className="text-[10px] font-semibold uppercase tracking-widest opacity-70">
              Discipline Shield
            </p>
            <p className="text-2xl font-black tracking-tight sm:text-3xl">
              {vaultLevelLabel(disciplinePoints)}
            </p>
          </div>
          <div className="relative z-10 text-right">
            <p className="font-mono text-3xl font-bold" style={monoStyle}>
              {disciplinePoints.toLocaleString('es-CO')}{' '}
              <span className="text-sm font-normal opacity-70">DP</span>
            </p>
          </div>
          <div className="absolute right-0 top-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-white/10 blur-3xl" />
        </div>
      </section>

      {confirmOpen ? (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-[#0a0f12]/40 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="bt2-settlement-confirm-title"
        >
          <div className="max-w-md rounded-xl border border-[#a4b4be]/30 bg-[#f6fafe] p-6 shadow-xl">
            <h2
              id="bt2-settlement-confirm-title"
              className="text-lg font-bold text-[#26343d]"
            >
              Confirmar impacto en bankroll
            </h2>
            <p className="mt-3 text-sm text-[#52616a]">
              Resultado:{' '}
              <span className="font-semibold text-[#26343d]">
                {outcome ? OUTCOME_LABEL[outcome] : ''}
              </span>
              . PnL estimado:{' '}
              <span className="font-mono text-[#26343d]" style={monoStyle}>
                {Number.isFinite(pnlPreview)
                  ? `${pnlPreview >= 0 ? '+' : ''}${Math.round(pnlPreview)} COP`
                  : '—'}
              </span>
              . Nuevo capital:{' '}
              <span className="font-mono text-[#26343d]" style={monoStyle}>
                {Number.isFinite(newBankrollPreview)
                  ? `${Math.round(newBankrollPreview)} COP`
                  : '—'}
              </span>
              . +25 DP.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                className="rounded-lg border border-[#a4b4be]/40 px-4 py-2 text-sm font-medium text-[#52616a]"
                onClick={() => setConfirmOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="rounded-lg bg-[#8B5CF6] px-4 py-2 text-sm font-semibold text-white"
                onClick={onConfirmAudit}
              >
                Persistir liquidación
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
