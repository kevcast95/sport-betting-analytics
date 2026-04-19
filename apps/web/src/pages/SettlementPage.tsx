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
import { VektorShortDisclaimer } from '@/components/vault/VektorShortDisclaimer'
import { vaultMockPicks } from '@/data/vaultMockPicks'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { modelPredictionResultEs } from '@/lib/bt2ProtocolLabels'
import {
  formatEstimatedHitPct,
  labelActionTier,
  labelEvidenceQuality,
  labelPredictiveTier,
} from '@/lib/pickSignalLabels'
import { displayMarketLabelEs } from '@/lib/marketCanonicalDisplay'
import { MODEL_WHY_TITLE_ES, modelWhyReading } from '@/lib/vaultModelReading'
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
import type { LedgerRow } from '@/store/useTradeStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import {
  CommitStandardPick,
  SlideToUnlock,
} from '@/components/vault/PickCard'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'
import { useVaultStore } from '@/store/useVaultStore'
import {
  Navigate,
  NavLink,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom'

type AnyPick = {
  id: string
  marketClass: string
  marketLabelEs?: string
  marketCanonical?: string
  marketCanonicalLabelEs?: string
  eventLabel: string
  titulo: string
  suggestedDecimalOdds: number
  selectionSummaryEs: string
  traduccionHumana: string
  accessTier: string
  isAvailable?: boolean
  /** D-05-011 — ISO UTC desde GET /bt2/vault/picks */
  kickoffUtc?: string
  unlockCostDp?: number
  eventId?: number
  dsrNarrativeEs?: string
  dsrSource?: string
  /** @deprecated Legacy; usar las 4 dimensiones de señal. */
  dsrConfidenceLabel?: string
  estimatedHitProbability?: number | null
  evidenceQuality?: string | null
  predictiveTier?: string | null
  actionTier?: string | null
  /** S6.1 — solo mostrar si existe en snapshot API. */
  dataCompletenessScore?: number | null
  pipelineVersion?: string
  modelMarketCanonical?: string
  modelSelectionCanonical?: string
  modelPredictionResult?: string | null
}

const DEFAULT_EVENT_TZ = 'America/Bogota'

function formatEventStartUtc(
  isoUtc: string | undefined,
  timeZone = DEFAULT_EVENT_TZ,
): string | null {
  if (isoUtc == null || typeof isoUtc !== 'string' || isoUtc.trim() === '') {
    return null
  }
  const d = Date.parse(isoUtc)
  if (Number.isNaN(d)) return null
  try {
    return new Intl.DateTimeFormat('es-CO', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone,
    }).format(new Date(d))
  } catch {
    return null
  }
}

/** D-05-010: bloqueo de «Tomar» solo con instante contractual; `isAvailable` manda cierre. */
function isEventStartInPast(isoUtc: string | undefined): boolean {
  if (isoUtc == null || typeof isoUtc !== 'string' || isoUtc.trim() === '') {
    return false
  }
  const d = Date.parse(isoUtc)
  if (Number.isNaN(d)) return false
  return Date.now() >= d
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

/** T-145 / US-FE-036: ficha settlement cuando el pick ya no está en el snapshot del día. */
function anyPickFromLedgerRow(row: LedgerRow, vaultPickId: string): AnyPick {
  const sug = row.suggestedDecimalOdds
  const odds =
    sug != null && Number.isFinite(sug) && sug > 1 ? sug : row.decimalCuota
  return {
    id: vaultPickId,
    marketClass: row.marketClass ?? '—',
    marketLabelEs: displayMarketLabelEs({
      marketCanonicalLabelEs: row.marketCanonicalLabelEs,
      marketClass: row.marketClass,
    }),
    marketCanonicalLabelEs: row.marketCanonicalLabelEs,
    eventLabel: row.eventLabel ?? vaultPickId,
    titulo: row.titulo ?? '—',
    suggestedDecimalOdds: Number.isFinite(odds) && odds > 1 ? odds : Number.NaN,
    selectionSummaryEs: row.selectionSummaryEs ?? '',
    traduccionHumana: '',
    accessTier: 'standard',
    isAvailable: true,
    kickoffUtc: undefined,
    unlockCostDp: undefined,
    eventId: undefined,
    modelPredictionResult: row.modelPredictionResult ?? null,
  }
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
  const [searchParams] = useSearchParams()
  const isReviewPhase = searchParams.get('phase') === 'review'

  // Buscar pick: API primero. En entorno dev, fallback a mock local si no hay pick API.
  const apiPicks = useVaultStore((s) => s.apiPicks)
  const unlockedPickIds = useVaultStore((s) => s.unlockedPickIds)
  const takeApiPick = useVaultStore((s) => s.takeApiPick)
  const tryUnlockPick = useVaultStore((s) => s.tryUnlockPick)
  const takenApiPicks = useVaultStore((s) => s.takenApiPicks)
  const pick: AnyPick | null = useMemo(() => {
    const apiPick = apiPicks.find((p) => p.id === pickId)
    if (apiPick) return apiPick
    if (import.meta.env.DEV) {
      const mockPick = vaultMockPicks.find((p) => p.id === pickId)
      if (mockPick) {
        return {
          ...mockPick,
          marketLabelEs: undefined,
          isAvailable: true,
        }
      }
    }
    return null
  }, [pickId, apiPicks])

  // bt2PickId para settlement API (null si es mock o no tomado aún)
  const bt2PickRecord = useMemo(
    () => takenApiPicks.find((r) => r.vaultPickId === pickId) ?? null,
    [takenApiPicks, pickId],
  )

  const stationLocked = useSessionStore(selectStationLocked)
  const unlocked = useMemo(() => {
    const apiPick = apiPicks.find((p) => p.id === pickId)
    if (apiPick?.accessTier === 'standard' || apiPick?.accessTier === 'premium') {
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
  const ledgerRowForPick = useMemo(() => {
    const rows = ledger.filter((r) => r.pickId === pickId)
    if (rows.length === 0) return null
    return [...rows].sort(
      (a, b) =>
        new Date(b.settledAt).getTime() - new Date(a.settledAt).getTime(),
    )[0]
  }, [ledger, pickId])

  const displayPick = useMemo((): AnyPick | null => {
    if (pick) return pick
    if (ledgerRowForPick) return anyPickFromLedgerRow(ledgerRowForPick, pickId)
    return null
  }, [pick, ledgerRowForPick, pickId])

  const finalizeSettlement = useTradeStore((s) => s.finalizeSettlement)
  const settleApiPick = useTradeStore((s) => s.settleApiPick)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const hydrateLedgerFromApi = useTradeStore((s) => s.hydrateLedgerFromApi)

  const bankroll = useBankrollStore((s) => s.confirmedBankrollCop)
  const stakePct = useBankrollStore((s) => s.selectedStakePct)

  const [outcome, setOutcome] = useState<SettlementOutcome | null>(null)
  const [reflection, setReflection] = useState('')
  const [bookOddsRaw, setBookOddsRaw] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [settling, setSettling] = useState(false)
  const [settleError, setSettleError] = useState<string | null>(null)
  const [reviewTakeError, setReviewTakeError] = useState<string | null>(null)
  const [reviewTaking, setReviewTaking] = useState(false)

  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('settlement'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    if (isReviewPhase) return
    if (!hasSeenTour) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour, isReviewPhase])

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  const isApiRouteBlocked = useMemo(() => {
    if (settled) return false
    const apiPick = apiPicks.find((p) => p.id === pickId)
    if (!apiPick) return false
    const mockFallback =
      import.meta.env.DEV && vaultMockPicks.some((x) => x.id === pickId)
    if (mockFallback) return false
    // D-05-010: revisión pre-toma sin POST /bt2/picks aún
    if (isReviewPhase) return false
    return !bt2PickRecord
  }, [apiPicks, pickId, bt2PickRecord, isReviewPhase, settled])

  const apiPickMatch = useMemo(
    () => apiPicks.find((p) => p.id === pickId) ?? null,
    [apiPicks, pickId],
  )
  const isDevMockPick =
    import.meta.env.DEV && vaultMockPicks.some((x) => x.id === pickId)

  const premiumReviewAllowed = useMemo(() => {
    if (!displayPick || displayPick.accessTier !== 'premium') return true
    if (apiPickMatch?.accessTier === 'premium') {
      return apiPickMatch.premiumUnlocked === true
    }
    if (isDevMockPick) {
      return unlockedPickIds.includes(pickId)
    }
    return false
  }, [displayPick, apiPickMatch, isDevMockPick, unlockedPickIds, pickId])

  const showReviewTakeCtas =
    isReviewPhase &&
    !settled &&
    displayPick != null &&
    displayPick.isAvailable !== false &&
    ((apiPickMatch != null &&
      !bt2PickRecord &&
      (apiPickMatch.accessTier === 'standard' ||
        apiPickMatch.premiumUnlocked)) ||
      (isDevMockPick &&
        displayPick.accessTier === 'premium' &&
        !unlockedPickIds.includes(pickId)))

  const showReviewTakenBridge =
    isReviewPhase && !settled && unlocked && !showReviewTakeCtas

  const showLiquidationForm = unlocked && !isReviewPhase && !settled

  const eventStartLabel = displayPick
    ? formatEventStartUtc(displayPick.kickoffUtc)
    : null
  const takeBlockedAfterStart =
    displayPick != null &&
    displayPick.isAvailable !== false &&
    isEventStartInPast(displayPick.kickoffUtc)

  const premiumUnlockCost = displayPick?.unlockCostDp ?? VAULT_UNLOCK_COST_DP
  const insufficientDpPremium = disciplinePoints < premiumUnlockCost
  const isFreeAccessTier =
    displayPick?.accessTier === 'standard' ||
    (import.meta.env.DEV && displayPick?.accessTier === 'open')

  const reviewTakeUsesCommitOnly =
    isFreeAccessTier ||
    (apiPickMatch?.accessTier === 'premium' &&
      apiPickMatch.premiumUnlocked === true) ||
    (isDevMockPick &&
      displayPick?.accessTier === 'premium' &&
      unlockedPickIds.includes(pickId))

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const metrics = useMemo(() => ledgerAggregateMetrics(ledger), [ledger])

  // US-FE-022: cuota sugerida directamente del CDM
  const suggestedOdds = displayPick?.suggestedDecimalOdds ?? Number.NaN
  const marketLabelEs = displayPick
    ? displayMarketLabelEs({
        marketCanonicalLabelEs: displayPick.marketCanonicalLabelEs,
        marketLabelEs: displayPick.marketLabelEs,
        marketClass: displayPick.marketClass,
        marketCanonical: displayPick.marketCanonical,
      })
    : '—'

  const modelVsPickLabel =
    settled && ledgerRowForPick?.modelPredictionResult != null
      ? modelPredictionResultEs(ledgerRowForPick.modelPredictionResult)
      : null

  const settlementModelWhy = useMemo(() => {
    if (!apiPickMatch || !displayPick) return null
    return modelWhyReading({
      dsrNarrativeEs: (displayPick.dsrNarrativeEs ?? '').trim(),
      traduccionHumana: displayPick.traduccionHumana ?? null,
      dsrSource: displayPick.dsrSource,
    })
  }, [apiPickMatch, displayPick])

  const settlementPickSignals = useMemo(() => {
    if (!apiPickMatch || !displayPick) return null
    const est = displayPick.estimatedHitProbability
    const ev = displayPick.evidenceQuality
    const pr = displayPick.predictiveTier
    const ac = displayPick.actionTier
    if (
      est == null &&
      !(ev && String(ev).trim()) &&
      !(pr && String(pr).trim()) &&
      !(ac && String(ac).trim())
    ) {
      return null
    }
    return { est, ev, pr, ac }
  }, [apiPickMatch, displayPick])

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

  if (!displayPick) return <Navigate to="/v2/vault" replace />
  // Premium: revisión solo si `premiumUnlocked` (vault) o mock desbloqueado; no confundir con pick tomado.
  if (
    !settled &&
    isReviewPhase &&
    displayPick.accessTier === 'premium' &&
    !premiumReviewAllowed
  ) {
    return (
      <Navigate
        to="/v2/vault"
        replace
        state={{
          settlementBlocked:
            'Desbloquea la señal premium en la bóveda (slider DP) antes de abrir la ficha completa.',
        }}
      />
    )
  }
  if (isApiRouteBlocked) {
    return (
      <Navigate
        to="/v2/vault"
        replace
        state={{
          settlementBlocked:
            'Registra primero la señal en la bóveda (compromiso / desbloqueo) antes de liquidar.',
        }}
      />
    )
  }
  // D-05-010: la revisión pre-toma permite ver la ficha aunque la estación esté cerrada;
  // takeApiPick / UI siguen bloqueando el registro.
  if (!settled && stationLocked && !isReviewPhase) {
    return <Navigate to="/v2/vault" replace />
  }
  if (!settled && !unlocked) {
    if (!(isReviewPhase && !bt2PickRecord)) {
      return <Navigate to="/v2/vault" replace />
    }
  }

  const showReadOnlySettled = settled

  const showReviewUnavailableOnly =
    isReviewPhase && displayPick.isAvailable === false

  const onTakeFromReview = async () => {
    if (reviewTaking) return
    setReviewTakeError(null)
    setReviewTaking(true)
    try {
      if (apiPickMatch) {
        const res = await takeApiPick(apiPickMatch)
        if (res.ok) {
          void hydrateLedgerFromApi()
          navigate(`/v2/settlement/${pickId}`, { replace: true })
          return
        }
        if (res.reason === 'insufficient_dp_premium' && res.premiumDetail) {
          setReviewTakeError(res.premiumDetail.message)
        } else if (res.reason === 'insufficient_dp') {
          setReviewTakeError(
            'Saldo DP insuficiente para desbloquear esta señal premium.',
          )
        } else if (res.reason === 'premium_not_unlocked') {
          setReviewTakeError(
            'Desbloquea primero la señal premium en la bóveda (slider).',
          )
        } else if (res.reason === 'station_locked') {
          setReviewTakeError(
            'Estación cerrada: no puedes registrar señales en este ciclo.',
          )
        } else if (res.reason === 'pick_unavailable') {
          setReviewTakeError('Este pick no está disponible para registro.')
        } else if (res.reason === 'insufficient_bankroll') {
          setReviewTakeError(
            res.apiMessage ??
              'Bankroll insuficiente para el stake de esta señal.',
          )
        } else if (res.reason === 'already_unlocked') {
          navigate(`/v2/settlement/${pickId}`, { replace: true })
        } else {
          setReviewTakeError(
            'No se pudo registrar la señal. Reintenta o revisa tu conexión.',
          )
        }
      } else if (import.meta.env.DEV && isDevMockPick) {
        const res = tryUnlockPick(pickId)
        if (res.ok) {
          navigate(`/v2/settlement/${pickId}`, { replace: true })
        } else if (res.reason === 'station_locked') {
          setReviewTakeError(
            'Estación cerrada: no puedes registrar señales en este ciclo.',
          )
        } else if (res.reason === 'insufficient_dp') {
          setReviewTakeError('Disciplina insuficiente para desbloquear.')
        } else if (res.reason === 'already_unlocked') {
          navigate(`/v2/settlement/${pickId}`, { replace: true })
        } else {
          setReviewTakeError('No se pudo desbloquear.')
        }
      }
    } finally {
      setReviewTaking(false)
    }
  }

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
        setSettleError(
          'No se pudo registrar la liquidación en el servidor. Revisa la conexión. Si el API responde 422, el mercado o la selección pueden no admitir el resultado enviado (p. ej. void o mapeo no soportado — US-FE-039 / T-150).',
        )
      }
      return
    }

    const dp = res.earnedDp ?? 0
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

      <BunkerViewHeader
        title={displayPick.eventLabel}
        subtitle={`La Bóveda · ${
          isReviewPhase ? 'Revisión de señal' : 'Terminal de liquidación'
        }`}
        onHelpClick={() => {
          resetTour('settlement')
          setTourOpen(true)
        }}
      />

      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-7">
          <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-8">
            <div className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-start">
              <div>
                <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-[#52616a]">
                  Especificación del activo
                </p>
                {displayPick.titulo ? (
                  <>
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                      Competición
                    </p>
                    <p className="mb-4 text-sm font-semibold text-[#26343d]">
                      {displayPick.titulo}
                    </p>
                  </>
                ) : null}
                {eventStartLabel ? (
                  <p className="mb-4 font-mono text-xs text-[#52616a]">
                    Inicio del evento (tu zona):{' '}
                    <span className="font-semibold text-[#26343d]">
                      {eventStartLabel}
                    </span>
                  </p>
                ) : null}
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#52616a]">
                  Mercado
                </p>
                <div
                  className="mb-1 inline-block rounded-lg bg-[#e9ddff] px-4 py-2 text-sm font-bold text-[#6d3bd7]"
                  title={displayPick.marketClass}
                >
                  {marketLabelEs}
                </div>
                {displayPick.selectionSummaryEs ? (
                  <p className="mb-3 text-sm font-semibold text-[#26343d]">
                    {displayPick.selectionSummaryEs}
                  </p>
                ) : null}
                {modelVsPickLabel ? (
                  <p className="mb-3 rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa]/80 px-3 py-2 text-xs font-semibold text-[#435368]">
                    Resultado vs modelo (liquidado):{' '}
                    <span className="font-mono text-[#26343d]">
                      {modelVsPickLabel}
                    </span>
                  </p>
                ) : null}
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

          {/* Misma regla que v1 / PickCard: un solo párrafo “por qué” (`razon`). */}
          <div className="space-y-4 rounded-xl bg-[#eef4fa] p-8">
            {settlementModelWhy ? (
              <div className="rounded-xl border border-[#6d3bd7]/20 bg-white/90 p-6 shadow-sm">
                <div className="mb-3 flex items-center gap-3">
                  <IconPsychology className="shrink-0 text-[#6d3bd7]" />
                  <h3 className="text-lg font-bold tracking-tight text-[#26343d]">
                    {settlementModelWhy.title}
                  </h3>
                </div>
                <p className="text-sm leading-relaxed text-[#26343d]">
                  {settlementModelWhy.body}
                </p>
              </div>
            ) : null}
            {!apiPickMatch && displayPick.traduccionHumana?.trim() ? (
              <div className="rounded-xl border border-[#a4b4be]/25 bg-white/80 p-6">
                <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-[#52616a]">
                  {MODEL_WHY_TITLE_ES}
                </h3>
                <p className="text-sm leading-relaxed text-[#26343d]">
                  {displayPick.traduccionHumana}
                </p>
              </div>
            ) : null}
            {settlementPickSignals ? (
              <div className="rounded-xl border border-[#a4b4be]/25 bg-white/90 p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-[#52616a]">
                  Señales del modelo
                </h3>
                <dl className="grid gap-4 text-sm text-[#26343d] sm:grid-cols-2">
                  <div>
                    <dt className="text-[11px] font-semibold text-[#52616a]">
                      Probabilidad estimada
                    </dt>
                    <dd className="mt-1 font-mono text-lg" style={monoStyle}>
                      {formatEstimatedHitPct(settlementPickSignals.est)}
                    </dd>
                    <p className="mt-2 text-xs leading-snug text-[#6e7d86]">
                      Es una lectura orientativa del modelo sobre la opción; no garantiza el
                      resultado del partido.
                    </p>
                  </div>
                  <div>
                    <dt className="text-[11px] font-semibold text-[#52616a]">
                      Respaldo del análisis
                    </dt>
                    <dd className="mt-1 font-semibold text-[#26343d]">
                      {labelEvidenceQuality(settlementPickSignals.ev)}
                    </dd>
                    <p className="mt-2 text-xs leading-snug text-[#6e7d86]">
                      Indica qué tan completos y consistentes están los datos que sustentan
                      esta lectura (incluye chequeos internos del consenso numérico).
                    </p>
                  </div>
                  <div>
                    <dt className="text-[11px] font-semibold text-[#52616a]">
                      Fuerza del pick
                    </dt>
                    <dd className="mt-1 font-semibold text-[#26343d]">
                      {labelPredictiveTier(settlementPickSignals.pr)}
                    </dd>
                    <p className="mt-2 text-xs leading-snug text-[#6e7d86]">
                      Posición relativa frente al resto de señales del día en el ranking
                      interno; no es un nivel de acceso del producto.
                    </p>
                  </div>
                  <div>
                    <dt className="text-[11px] font-semibold text-[#52616a]">Acceso</dt>
                    <dd className="mt-1 font-semibold text-[#26343d]">
                      {labelActionTier(settlementPickSignals.ac)}
                    </dd>
                    <p className="mt-2 text-xs leading-snug text-[#6e7d86]">
                      Cómo se ofrece en la bóveda: lectura libre o desbloqueo premium con DP,
                      según las reglas del día.
                    </p>
                  </div>
                </dl>
              </div>
            ) : null}
          </div>

          <div className="rounded-xl border border-[#a4b4be]/20 bg-white/90 px-5 py-4">
            <VektorShortDisclaimer />
          </div>
        </div>

        <div className="space-y-6 lg:col-span-5">
          <div className="sticky top-24 rounded-xl border border-[#a4b4be]/15 bg-white p-8 shadow-[0px_20px_40px_rgba(38,52,61,0.06)]">
            {showReviewUnavailableOnly ? (
              <>
                <h3 className="text-xl font-bold tracking-tight text-[#26343d]">
                  Señal no disponible
                </h3>
                <p className="mt-4 text-sm leading-snug text-[#52616a]">
                  El servidor marcó este pick como no disponible; no se puede registrar
                  una nueva posición.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/v2/vault')}
                  className="mt-6 py-3 text-sm font-semibold text-[#52616a] hover:text-[#26343d]"
                >
                  Volver a la bóveda
                </button>
              </>
            ) : showReviewTakeCtas ? (
              <>
                <h3 className="text-xl font-bold tracking-tight text-[#26343d]">
                  Registrar en el protocolo
                </h3>
                <p className="mt-4 text-sm leading-snug text-[#52616a]">
                  Confirma la lectura del modelo y registra la señal; mismo efecto que
                  «Tomar» en la tarjeta de la bóveda.
                </p>
                {reviewTakeError ? (
                  <p
                    className="mt-4 rounded-lg border border-[#fee2e2] bg-[#fff1f2] px-3 py-2 text-sm text-[#9b1c1c]"
                    role="alert"
                  >
                    {reviewTakeError}
                  </p>
                ) : null}
                {takeBlockedAfterStart ? (
                  <p className="mt-4 text-sm font-semibold text-[#914d00]">
                    El evento ya inició según la hora del protocolo: «Tomar» está
                    desactivado (D-05-010 / US-BE-019).
                  </p>
                ) : null}
                <div className="mt-6">
                  {reviewTakeUsesCommitOnly ? (
                    <CommitStandardPick
                      stationLocked={stationLocked}
                      disabled={takeBlockedAfterStart || reviewTaking}
                      onCommitted={() => void onTakeFromReview()}
                    />
                  ) : (
                    <SlideToUnlock
                      stationLocked={stationLocked}
                      insufficientDp={insufficientDpPremium}
                      costDp={premiumUnlockCost}
                      disabled={takeBlockedAfterStart || reviewTaking}
                      onUnlocked={() => void onTakeFromReview()}
                    />
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => navigate('/v2/vault')}
                  className="mt-6 py-3 text-sm font-semibold text-[#52616a] hover:text-[#26343d]"
                >
                  Volver a la bóveda
                </button>
              </>
            ) : showReviewTakenBridge ? (
              <>
                <h3 className="text-xl font-bold tracking-tight text-[#26343d]">
                  Señal en el protocolo
                </h3>
                <p className="mt-4 text-sm leading-snug text-[#52616a]">
                  Ya registraste esta posición. Continúa a liquidación cuando el evento
                  haya cerrado.
                </p>
                <NavLink
                  to={`/v2/settlement/${pickId}`}
                  className="mt-6 block rounded-xl border border-[#8B5CF6]/35 bg-[#e9ddff]/25 py-3 text-center text-sm font-bold text-[#6d3bd7] transition-colors hover:bg-[#e9ddff]/45"
                >
                  Ir a liquidación
                </NavLink>
                <button
                  type="button"
                  onClick={() => navigate('/v2/vault')}
                  className="mt-3 w-full py-3 text-sm font-semibold text-[#52616a] hover:text-[#26343d]"
                >
                  Volver a la bóveda
                </button>
              </>
            ) : showReadOnlySettled ? (
              <>
                <h3 className="text-xl font-bold tracking-tight text-[#26343d]">
                  Liquidación archivada
                </h3>
                <p className="mt-4 text-sm leading-snug text-[#52616a]">
                  Vista solo lectura (US-FE-036 / D-05-013). Los datos mostrados provienen del
                  registro local o del ledger sincronizado.
                </p>
                {ledgerRowForPick ? (
                  <dl className="mt-6 space-y-3 text-sm text-[#26343d]">
                    <div>
                      <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                        Resultado declarado
                      </dt>
                      <dd className="mt-1 font-semibold">
                        {OUTCOME_LABEL[ledgerRowForPick.outcome]}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                        Resultado neto (COP)
                      </dt>
                      <dd className="mt-1 font-mono tabular-nums" style={monoStyle}>
                        {formatCop(Math.round(ledgerRowForPick.pnlCop))}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                        Stake
                      </dt>
                      <dd className="mt-1 font-mono tabular-nums" style={monoStyle}>
                        {formatCop(Math.round(ledgerRowForPick.stakeCop))}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                        Cuota efectiva
                      </dt>
                      <dd className="mt-1 font-mono tabular-nums" style={monoStyle}>
                        {ledgerRowForPick.decimalCuota.toFixed(2)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                        Reflexión registrada
                      </dt>
                      <dd className="mt-1 text-[#52616a] leading-relaxed">
                        {ledgerRowForPick.reflection || '—'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                        Liquidado
                      </dt>
                      <dd className="mt-1 font-mono text-xs text-[#52616a]">
                        {new Date(ledgerRowForPick.settledAt).toLocaleString('es-CO')}
                      </dd>
                    </div>
                    {ledgerRowForPick.earnedDp != null ? (
                      <div>
                        <dt className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                          DP liquidación
                        </dt>
                        <dd className="mt-1 font-mono font-semibold text-[#6d3bd7]">
                          +{ledgerRowForPick.earnedDp} DP
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                ) : (
                  <p className="mt-4 text-sm text-[#6e7d86]">
                    No hay fila de ledger local para este ID; sincroniza o abre desde el libro mayor.
                  </p>
                )}
                <NavLink
                  to="/v2/ledger"
                  className="mt-6 block rounded-xl border border-[#a4b4be]/30 bg-white py-3 text-center text-sm font-bold text-[#26343d] transition-colors hover:bg-[#eef4fa]"
                >
                  Ir al libro mayor
                </NavLink>
                <button
                  type="button"
                  onClick={() => navigate('/v2/vault')}
                  className="mt-3 w-full py-3 text-sm font-semibold text-[#52616a] hover:text-[#26343d]"
                >
                  Volver a la bóveda
                </button>
              </>
            ) : showLiquidationForm ? (
              <>
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
                  Recompensa: +10 DP (gestión)
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
                placeholder="¿Cómo viviste el resultado frente al plan de tamaño y registro?"
                className="min-h-[120px] w-full rounded-xl border-0 bg-[#ddeaf3] p-4 text-sm text-[#26343d] placeholder:text-[#52616a]/40 focus:ring-1 focus:ring-[#6d3bd7]"
              />
              <p className="mt-2 text-[10px] italic text-[#52616a]">
                * Este dato alimenta el índice de equilibrio emocional del
                protocolo.
              </p>
            </div>
            {/* US-FE-013: nota visible de modo confianza (criterio §6.1) */}
            <div className="mt-6 space-y-3">
              <div className="rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] px-4 py-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                  Modo de verificación
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-[#52616a]">
                  <span className="font-semibold text-[#26343d]">
                    {SETTLEMENT_VERIFICATION_MODE === 'trust'
                      ? 'MVP · Confianza.'
                      : 'Verificado.'}{' '}
                  </span>
                  {SETTLEMENT_MODE_LABEL_ES[SETTLEMENT_VERIFICATION_MODE]}
                </p>
              </div>
              {SETTLEMENT_VERIFICATION_MODE === 'verified' ? (
                <div className="rounded-lg border border-[#fde68a] bg-[#fffbeb] px-4 py-3 text-[11px] leading-snug text-[#92400e]">
                  Con cruce canónico activo, aquí se mostrará el estado de discrepancia y la fuente
                  del resultado según contrato (US-FE-038); no usar estados inventados hasta que el
                  API los exponga.
                </div>
              ) : null}
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
              </>
            ) : null}
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
              {bt2PickRecord
                ? '. +10 DP por registrar la liquidación con reflexión (ganancia, pérdida o empate/anulado).'
                : '. DP según resultado.'}
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
