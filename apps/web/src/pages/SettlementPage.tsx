import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'
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
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { getMarketLabelEs } from '@/lib/marketLabels'
import { ledgerAggregateMetrics } from '@/lib/ledgerAnalytics'
import {
  computeSettlementPnlCop,
  potentialProfitCop,
  type SettlementOutcome,
} from '@/lib/settlementPnL'
import {
  SETTLEMENT_MODE_LABEL_ES,
  SETTLEMENT_VERIFICATION_MODE,
} from '@/lib/bt2SettlementMode'
import { computeUnitValue } from '@/lib/treasuryMath'
import { useBankrollStore } from '@/store/useBankrollStore'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import { Navigate, useNavigate, useParams } from 'react-router-dom'

type AnyPick = {
  id: string
  marketClass: string
  marketLabelEs?: string
  eventLabel: string
  titulo: string
  suggestedDecimalOdds: number
  selectionSummaryEs: string
  traduccionHumana: string
  accessTier: string
}

const SETTLEMENT_TOUR = getTourScript('settlement')!

const OUTCOME_LABEL: Record<SettlementOutcome, string> = {
  PROFIT: 'Ganancia',
  LOSS: 'Pérdida',
  PUSH: 'Empate / Anulado',
}

// US-FE-022 T-057: umbrales de alineación entre cuota sugerida y cuota casa
const ALIGNMENT_ALIGNED = 0.02
const ALIGNMENT_CLOSE = 0.08

type OddsAlignment = 'alineada' | 'cercana' | 'desviada' | null

function computeOddsAlignment(
  suggested: number,
  book: number,
): OddsAlignment {
  if (!Number.isFinite(suggested) || !Number.isFinite(book) || book <= 0) {
    return null
  }
  const diff = Math.abs(suggested - book)
  if (diff <= ALIGNMENT_ALIGNED) return 'alineada'
  if (diff <= ALIGNMENT_CLOSE) return 'cercana'
  return 'desviada'
}

const ALIGNMENT_STYLE: Record<
  NonNullable<OddsAlignment>,
  { label: string; badge: string; micro: string }
> = {
  alineada: {
    label: 'Alineada',
    badge: 'bg-[#d1fae5] text-[#065f46]',
    micro: 'Tu cuota coincide con la sugerida. Condiciones óptimas para ejecutar.',
  },
  cercana: {
    label: 'Cercana',
    badge: 'bg-[#fef9c3] text-[#854d0e]',
    micro: 'Diferencia menor al 8 %. Revisa el ticket antes de confirmar.',
  },
  desviada: {
    label: 'Desviada',
    badge: 'bg-[#fee2e2] text-[#9b1c1c]',
    micro: 'Tu cuota difiere notablemente de la sugerida. Reconsiderado el tamaño.',
  },
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

  // Buscar pick: API primero. En entorno dev, fallback a mock local si no hay pick API.
  const apiPicks = useVaultStore((s) => s.apiPicks)
  const takenApiPicks = useVaultStore((s) => s.takenApiPicks)
  const pick: AnyPick | null = useMemo(() => {
    const apiPick = apiPicks.find((p) => p.id === pickId)
    if (apiPick) return apiPick
    if (import.meta.env.DEV) {
      const mockPick = vaultMockPicks.find((p) => p.id === pickId)
      if (mockPick) return { ...mockPick, marketLabelEs: undefined }
    }
    return null
  }, [pickId, apiPicks])

  // bt2PickId para settlement API (null si es mock o no tomado aún)
  const bt2PickRecord = useMemo(
    () => takenApiPicks.find((r) => r.vaultPickId === pickId) ?? null,
    [takenApiPicks, pickId],
  )

  const stationLocked = useSessionStore(selectStationLocked)
  const unlockedPickIds = useVaultStore((s) => s.unlockedPickIds)
  const unlocked = useMemo(() => {
    const apiPick = apiPicks.find((p) => p.id === pickId)
    if (apiPick?.accessTier === 'standard') return true
    if (apiPick?.accessTier === 'premium') {
      return takenApiPicks.some((r) => r.vaultPickId === pickId)
    }
    if (import.meta.env.DEV) {
      const mockPick = vaultMockPicks.find((x) => x.id === pickId)
      if (mockPick?.accessTier === 'open') return true
      return unlockedPickIds.includes(pickId)
    }
    return false
  }, [unlockedPickIds, pickId, apiPicks, takenApiPicks])
  const settled = useTradeStore((s) => s.settledPickIds.includes(pickId))
  const ledger = useTradeStore((s) => s.ledger)
  const finalizeSettlement = useTradeStore((s) => s.finalizeSettlement)
  const settleApiPick = useTradeStore((s) => s.settleApiPick)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)

  const bankroll = useBankrollStore((s) => s.confirmedBankrollCop)
  const stakePct = useBankrollStore((s) => s.selectedStakePct)

  const [outcome, setOutcome] = useState<SettlementOutcome | null>(null)
  const [reflection, setReflection] = useState('')
  const [bookOddsRaw, setBookOddsRaw] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [settling, setSettling] = useState(false)
  const [settleError, setSettleError] = useState<string | null>(null)
  const [earnedDpFinal, setEarnedDpFinal] = useState<number | null>(null)

  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('settlement'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    if (!hasSeenTour) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour])

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

  // US-FE-022: cuota sugerida directamente del CDM
  const suggestedOdds = pick?.suggestedDecimalOdds ?? Number.NaN
  const marketLabelEs = pick
    ? (pick.marketLabelEs || getMarketLabelEs(pick.marketClass))
    : '—'

  // T-057: cuota capturada en casa
  const bookOddsParsed = parseFloat(bookOddsRaw.replace(',', '.'))
  const bookOdds = Number.isFinite(bookOddsParsed) && bookOddsParsed > 1
    ? bookOddsParsed
    : Number.NaN

  // Cuota efectiva: usa cuota casa si existe, si no la sugerida
  const activeOdds = Number.isFinite(bookOdds) ? bookOdds : suggestedOdds

  const oddsAlignment = computeOddsAlignment(suggestedOdds, bookOdds)

  const stakeCop = computeUnitValue(bankroll, stakePct)
  const pnlPreview =
    outcome != null && Number.isFinite(activeOdds) && Number.isFinite(stakeCop)
      ? computeSettlementPnlCop(stakeCop, activeOdds, outcome)
      : Number.NaN
  const pnlPotential = Number.isFinite(activeOdds) && Number.isFinite(stakeCop)
    ? potentialProfitCop(stakeCop, activeOdds)
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

  const onConfirmAudit = async () => {
    if (!canSubmit || outcome == null || settling) return
    setSettling(true)
    setSettleError(null)
    setConfirmOpen(false)

    let res: { ok: boolean; earnedDp?: number; reason?: string }

    if (bt2PickRecord) {
      // US-FE-028: flujo real con API
      res = await settleApiPick({
        vaultPickId: pickId,
        bt2PickId: bt2PickRecord.bt2PickId,
        outcome,
        reflection,
        stakeCop,
        decimalCuota: activeOdds,
        bookDecimalOdds: Number.isFinite(bookOdds) ? bookOdds : undefined,
        market: bt2PickRecord.market,
        selection: bt2PickRecord.selection,
      })
    } else {
      // Flujo local (mock picks)
      res = finalizeSettlement({
        pickId,
        outcome,
        reflection,
        stakeCop,
        decimalCuota: activeOdds,
        bookDecimalOdds: Number.isFinite(bookOdds) ? bookOdds : undefined,
      })
    }

    setSettling(false)

    if (!res.ok) {
      if ('reason' in res && res.reason === 'api_error') {
        setSettleError('Error al conectar con el servidor. Verifica tu conexión.')
      }
      return
    }

    const dp = res.earnedDp ?? 0
    setEarnedDpFinal(dp)
    console.info(
      `[BT2] settlement mode: ${SETTLEMENT_VERIFICATION_MODE} · pick ${pickId} · +${dp} DP`,
    )
    setToast(
      dp > 0
        ? `Protocolo cumplido. +${dp} DP acreditados.`
        : 'Protocolo cumplido. La disciplina es el verdadero profit.',
    )
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

      {settleError ? (
        <div
          className="fixed bottom-24 left-1/2 z-[80] max-w-md -translate-x-1/2 rounded-lg border border-[#fee2e2] bg-[#fff1f2] px-5 py-3 text-center text-sm font-medium text-[#9b1c1c] shadow-lg lg:bottom-8"
          role="alert"
        >
          {settleError}
          <button
            type="button"
            className="ml-3 text-xs font-semibold underline"
            onClick={() => setSettleError(null)}
          >
            Cerrar
          </button>
        </div>
      ) : null}

      <div className="mb-10 lg:mb-12">
        <div className="mb-2 flex items-center justify-between gap-4">
          <div className="flex items-center text-xs font-semibold uppercase tracking-widest text-[#52616a]">
            <span>La Bóveda</span>
            <span className="mx-2 text-[#a4b4be]" aria-hidden>
              /
            </span>
            <span className="text-[#6d3bd7]">Terminal de liquidación</span>
          </div>
          <button
            type="button"
            onClick={() => { resetTour('settlement'); setTourOpen(true) }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#a4b4be]/30 bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] transition-colors hover:border-[#8B5CF6]/30 hover:text-[#8B5CF6]"
            title="Ver cómo funciona esta vista"
          >
            <span aria-hidden className="text-[11px]">?</span>
            Cómo funciona
          </button>
        </div>
        {/* US-FE-022: evento como título principal, pick.titulo como subtítulo */}
        <h1 className="text-3xl font-black tracking-tight text-[#26343d] sm:text-4xl">
          {pick.eventLabel}
        </h1>
        <p className="mt-1 text-sm font-medium text-[#52616a]">
          Auditoría ID:{' '}
          <span className="font-mono font-bold" style={monoStyle}>
            #{pick.id.toUpperCase()}
          </span>
        </p>
      </div>

      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-7">
          <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-8">
            <div className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-start">
              <div>
                <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                  Especificación del activo
                </p>
                {/* US-FE-024: label explícito «Mercado» + tipo + selección */}
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Mercado
                </p>
                <div
                  className="mb-1 inline-block rounded-lg bg-[#e9ddff] px-4 py-2 text-sm font-bold text-[#6d3bd7]"
                  title={pick.marketClass}
                >
                  {marketLabelEs}
                </div>
                {pick.selectionSummaryEs ? (
                  <p className="mb-3 text-sm font-semibold text-[#26343d]">
                    {pick.selectionSummaryEs}
                  </p>
                ) : null}
                {/* Tesis/narrativa del modelo como subtítulo */}
                <p className="text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                  Sugerencia del modelo
                </p>
                <h2 className="mt-1 text-lg font-bold tracking-tight text-[#26343d]">
                  {pick.titulo}
                </h2>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-6 border-t border-[#a4b4be]/10 pt-6 sm:grid-cols-3">
              {/* US-FE-022: "Cuota decimal sugerida" */}
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Cuota decimal sugerida
                </p>
                <p className="font-mono text-xl text-[#26343d]" style={monoStyle}>
                  {Number.isFinite(suggestedOdds) ? suggestedOdds.toFixed(2) : '—'}
                </p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Capital en riesgo
                </p>
                <p
                  className="font-mono text-xl font-semibold text-[#914d00]"
                  style={monoStyle}
                >
                  {Number.isFinite(stakeCop) ? formatCop(Math.round(stakeCop)) : '—'}
                </p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Retorno potencial
                </p>
                <p
                  className="font-mono text-xl font-semibold text-[#059669]"
                  style={monoStyle}
                >
                  {Number.isFinite(pnlPotential)
                    ? `+${formatCop(Math.round(pnlPotential))}`
                    : '—'}
                </p>
              </div>
            </div>
          </div>

          {/* US-FE-022: "Lectura del modelo" (antes "Traducción humana") */}
          <div className="rounded-xl bg-[#eef4fa] p-8">
            <div className="mb-6 flex items-center gap-3">
              <IconPsychology className="shrink-0 text-[#6d3bd7]" />
              <h3 className="text-lg font-bold tracking-tight text-[#26343d]">
                Lectura del modelo
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
                  Recompensa: +10/+5 DP
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
                <span>Ganancia</span>
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
                <span>Pérdida</span>
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
                <span>Empate / Anulado</span>
                <IconRestart />
              </button>
            </div>

            {/* US-FE-022 T-057: cuota decimal en la casa */}
            <div className="mb-6 border-t border-[#a4b4be]/15 pt-6">
              <label
                htmlFor="bt2-book-odds"
                className="mb-1 block text-xs font-semibold uppercase tracking-widest text-[#52616a]"
              >
                Cuota decimal en tu casa
              </label>
              <p className="mb-3 text-[10px] text-[#6e7d86]">
                Introduce la cuota que tomaste. Se usará para calcular el retorno real.
              </p>
              <input
                id="bt2-book-odds"
                type="text"
                inputMode="decimal"
                value={bookOddsRaw}
                onChange={(e) => setBookOddsRaw(e.target.value)}
                placeholder={Number.isFinite(suggestedOdds) ? suggestedOdds.toFixed(2) : '1.90'}
                className="w-full rounded-xl border border-[#a4b4be]/30 bg-[#f6fafe] px-4 py-3 font-mono text-base text-[#26343d] placeholder:text-[#52616a]/40 focus:border-[#6d3bd7] focus:outline-none focus:ring-1 focus:ring-[#6d3bd7]"
                style={monoStyle}
              />
              {/* Alineación cuota sugerida vs cuota casa */}
              {oddsAlignment ? (
                <div className="mt-3 rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest ${ALIGNMENT_STYLE[oddsAlignment].badge}`}
                    >
                      {ALIGNMENT_STYLE[oddsAlignment].label}
                    </span>
                    <span className="font-mono text-xs text-[#52616a]" style={monoStyle}>
                      Sugerida: {suggestedOdds.toFixed(2)} · Casa: {bookOdds.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[10px] text-[#52616a]">
                    {ALIGNMENT_STYLE[oddsAlignment].micro}
                  </p>
                </div>
              ) : null}
              {/* Si no hay cuota casa, aviso de cuota activa */}
              {!Number.isFinite(bookOdds) && Number.isFinite(suggestedOdds) ? (
                <p className="mt-2 text-[10px] italic text-[#6e7d86]">
                  Sin cuota casa: se usará la cuota sugerida ({suggestedOdds.toFixed(2)}) para el cálculo.
                </p>
              ) : null}
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
            {/* US-FE-013: nota visible de modo confianza (criterio §6.1) */}
            <div className="mt-6 rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] px-4 py-3">
              <p className="text-[11px] leading-relaxed text-[#52616a]">
                <span className="font-semibold text-[#26343d]">
                  Modo confianza activo.
                </span>{' '}
                {SETTLEMENT_MODE_LABEL_ES[SETTLEMENT_VERIFICATION_MODE]}
              </p>
            </div>

            <div className="mt-4 flex flex-wrap gap-4">
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
            <p className="font-mono text-xl font-semibold text-[#059669]" style={monoStyle}>
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
              Tasa de éxito
            </p>
            <p className="font-mono text-xl font-semibold text-[#26343d]" style={monoStyle}>
              {ledger.length > 0 ? `${metrics.winRatePct.toFixed(1)}%` : '—'}
            </p>
          </div>
        </div>
        <div className="relative flex items-center justify-between overflow-hidden rounded-xl bg-[#6d3bd7] p-6 text-white md:col-span-2">
          <div className="relative z-10">
            <p className="text-[10px] font-semibold uppercase tracking-widest opacity-70">
              Escudo de disciplina
            </p>
            <p className="text-2xl font-black tracking-tight sm:text-3xl">
              {vaultLevelLabel(disciplinePoints)}
            </p>
          </div>
          <div className="relative z-10 text-right">
            <p className="font-mono text-3xl font-bold" style={monoStyle}>
              {(disciplinePoints ?? 0).toLocaleString('es-CO')}{' '}
              <span className="text-sm font-normal opacity-70">DP</span>
            </p>
          </div>
          <div className="absolute right-0 top-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-white/10 blur-3xl" />
        </div>
      </section>

      {/* US-FE-021 (T-054): tour contextual */}
      <ViewTourModal
        open={tourOpen}
        title={SETTLEMENT_TOUR.title}
        steps={SETTLEMENT_TOUR.steps}
        onComplete={() => { setTourOpen(false); markTourSeen('settlement') }}
      />

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
              . Resultado neto estimado:{' '}
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
              {bt2PickRecord ? '. +10 DP si ganancia, +5 DP si pérdida.' : '. DP según resultado.'}
            </p>
            {Number.isFinite(bookOdds) ? (
              <p className="mt-2 text-[11px] text-[#52616a]">
                Cuota usada:{' '}
                <span className="font-mono font-semibold" style={monoStyle}>
                  {bookOdds.toFixed(2)}
                </span>{' '}
                (cuota en casa).
              </p>
            ) : (
              <p className="mt-2 text-[11px] text-[#52616a]">
                Cuota usada:{' '}
                <span className="font-mono font-semibold" style={monoStyle}>
                  {Number.isFinite(suggestedOdds) ? suggestedOdds.toFixed(2) : '—'}
                </span>{' '}
                (cuota sugerida por el sistema).
              </p>
            )}
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
                disabled={settling}
                className="flex items-center gap-2 rounded-lg bg-[#8B5CF6] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                onClick={() => void onConfirmAudit()}
              >
                {settling ? (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : null}
                Persistir liquidación
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
