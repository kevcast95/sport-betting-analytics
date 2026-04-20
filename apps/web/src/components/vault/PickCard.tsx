/**
 * US-FE-003 / US-FE-025 / US-FE-034: PickCard mock + API.
 * D-05-009 / D-05-010: preview traduccionHumana; Detalle → settlement ?phase=review; Tomar/Liquidar.
 */
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import type { VaultPickCdm } from '@/data/vaultMockPicks'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'
import {
  type Bt2VaultPickOut,
  bt2VaultPickUnlockEligible,
} from '@/lib/bt2Types'
import {
  formatEstimatedHitPct,
  labelActionTier,
  labelEvidenceQuality,
  labelPredictiveTier,
} from '@/lib/pickSignalLabels'
import { displayMarketLabelEs } from '@/lib/marketCanonicalDisplay'
import { getMarketLabelEs } from '@/lib/marketLabels'
import { isKickoffUtcInPast } from '@/lib/vaultKickoff'
import { modelWhyReading } from '@/lib/vaultModelReading'
import { vaultPickEventPresentation } from '@/lib/vaultPickEventUi'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'

const KNOB = 40
const PAD = 6
/** TZ por defecto hasta leer `bt2_user_settings.timezone` en app (T-139) */
const DEFAULT_EVENT_TZ = 'America/Bogota'

type AnyPick = VaultPickCdm | Bt2VaultPickOut

function isApiPick(p: AnyPick): p is Bt2VaultPickOut {
  return (
    'accessTier' in p &&
    (p.accessTier === 'standard' || p.accessTier === 'premium') &&
    'eventLabel' in p
  )
}

/** Un solo bloque estilo v1 (`razon`): por qué el modelo sugiere la lectura. */
function ModelWhyBlock(props: {
  title: string
  body: string
  lineClampClass: string
  reviewHref: string
  showReviewLink?: boolean
}) {
  const {
    title,
    body,
    lineClampClass,
    reviewHref,
    showReviewLink = true,
  } = props
  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-lg border border-[#6d3bd7]/15 bg-[#f6fafe]/90 p-3">
        <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
          {title}
        </p>
        <p className={`${lineClampClass} text-xs leading-relaxed text-[#26343d]`}>
          {body}
        </p>
      </div>
      {showReviewLink ? (
        <NavLink
          to={reviewHref}
          className="inline-block text-xs font-bold text-[#6d3bd7] underline-offset-2 hover:underline"
        >
          Ver ficha completa
        </NavLink>
      ) : null}
    </div>
  )
}

/** Resumen colapsable: 4 dimensiones (pick desbloqueado, API con datos). */
function PickSignalCollapsibleEs({
  estimatedHit,
  evidenceQ,
  predictiveQ,
  actionQ,
}: {
  estimatedHit: number | null | undefined
  evidenceQ: string | null | undefined
  predictiveQ: string | null | undefined
  actionQ: string | null | undefined
}) {
  const [open, setOpen] = useState(false)
  const hasData =
    estimatedHit != null ||
    (evidenceQ && evidenceQ.length > 0) ||
    (predictiveQ && predictiveQ.length > 0) ||
    (actionQ && actionQ.length > 0)
  if (!hasData) return null
  return (
    <div className="mt-2 rounded-lg border border-[#a4b4be]/20 bg-white/80">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wide text-[#52616a]"
      >
        <span>Señales del modelo</span>
        <span className="font-mono text-[10px] text-[#6e7d86]">{open ? '−' : '+'}</span>
      </button>
      {open ? (
        <div className="space-y-2 border-t border-[#eef4fa] px-3 py-3 text-[11px] leading-snug text-[#26343d]">
          <p>
            <span className="font-semibold text-[#52616a]">Probabilidad estimada · </span>
            {formatEstimatedHitPct(estimatedHit ?? null)}
            <span className="block text-[10px] font-normal text-[#6e7d86]">
              Idea orientativa del modelo sobre la opción; no es probabilidad garantizada.
            </span>
          </p>
          <p>
            <span className="font-semibold text-[#52616a]">Respaldo del análisis · </span>
            {labelEvidenceQuality(evidenceQ)}
            <span className="block text-[10px] font-normal text-[#6e7d86]">
              Qué tan completos están los datos que respaldan esta lectura.
            </span>
          </p>
          <p>
            <span className="font-semibold text-[#52616a]">Fuerza del pick · </span>
            {labelPredictiveTier(predictiveQ)}
            <span className="block text-[10px] font-normal text-[#6e7d86]">
              Posición relativa frente al resto de señales del día.
            </span>
          </p>
          <p>
            <span className="font-semibold text-[#52616a]">Acceso · </span>
            {labelActionTier(actionQ)}
            <span className="block text-[10px] font-normal text-[#6e7d86]">
              Cómo se ofrece en la bóveda (libre o con DP premium).
            </span>
          </p>
        </div>
      ) : null}
    </div>
  )
}

/**
 * T-139 / US-BE-019: solo si el API envía ISO UTC; si no, retorna null (no inventar hora).
 */
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

function pickDisplay(p: AnyPick) {
  if (isApiPick(p)) {
    return {
      id: p.id,
      marketLabel: displayMarketLabelEs({
        marketCanonicalLabelEs: p.marketCanonicalLabelEs,
        marketLabelEs: p.marketLabelEs,
        marketClass: p.marketClass,
        marketCanonical: p.marketCanonical,
      }),
      marketRaw: p.marketClass,
      selectionSummaryEs: p.selectionSummaryEs,
      eventLabel: p.eventLabel,
      titulo: p.titulo,
      accessTier: p.accessTier as 'standard' | 'premium',
      suggestedDecimalOdds: p.suggestedDecimalOdds,
      edgeBps: p.edgeBps || null,
      traduccionHumana: p.traduccionHumana || null,
      curvaEquidad: p.curvaEquidad?.length > 1 ? p.curvaEquidad : null,
      isAvailable: p.isAvailable,
      externalSearchUrl: p.externalSearchUrl || null,
      unlockCostDp: p.unlockCostDp || VAULT_UNLOCK_COST_DP,
      kickoffUtc: p.kickoffUtc,
      eventStatus: p.eventStatus ?? null,
      premiumUnlocked: p.premiumUnlocked === true,
      contentUnlocked: p.contentUnlocked === true,
      userPickCommitment:
        p.userPickCommitment === 'taken' || p.userPickCommitment === 'not_taken'
          ? p.userPickCommitment
          : null,
      dsrNarrativeEs: (p.dsrNarrativeEs ?? '').trim(),
      dsrSource: (p.dsrSource ?? '').trim(),
      estimatedHitProbability: p.estimatedHitProbability ?? null,
      evidenceQuality: p.evidenceQuality ?? null,
      predictiveTier: p.predictiveTier ?? null,
      actionTier: p.actionTier ?? null,
      unlockEligible: bt2VaultPickUnlockEligible(p),
    }
  }
  return {
    id: p.id,
    marketLabel: getMarketLabelEs(p.marketClass),
    marketRaw: p.marketClass,
    selectionSummaryEs: p.selectionSummaryEs,
    eventLabel: p.eventLabel,
    titulo: p.titulo,
    accessTier: p.accessTier as 'open' | 'premium',
    suggestedDecimalOdds: p.suggestedDecimalOdds,
    edgeBps: p.edgeBps,
    traduccionHumana: p.traduccionHumana,
    curvaEquidad: p.curvaEquidad,
    isAvailable: true,
    externalSearchUrl: null,
    unlockCostDp: VAULT_UNLOCK_COST_DP,
    kickoffUtc: undefined as string | undefined,
    eventStatus: null as string | null,
    premiumUnlocked: false,
    contentUnlocked: true,
    userPickCommitment: null as 'taken' | 'not_taken' | null,
    dsrNarrativeEs: '',
    dsrSource: '',
    estimatedHitProbability: null,
    evidenceQuality: null,
    predictiveTier: null,
    actionTier: null,
    unlockEligible: true,
  }
}

function isPickFreeAccess(tier: string): boolean {
  return tier === 'standard' || tier === 'open'
}

function EquitySparkline({
  values,
  className,
}: {
  values: number[]
  className?: string
}) {
  if (values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const w = 240
  const h = 56
  const p = 6
  const span = max - min || 1
  const pts = values.map((v, i) => {
    const x = p + (i / (values.length - 1)) * (w - p * 2)
    const y = h - p - ((v - min) / span) * (h - p * 2)
    return `${x},${y}`
  })
  return (
    <svg
      className={className}
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
        points={pts.join(' ')}
      />
    </svg>
  )
}

export type CommitStandardPickProps = {
  stationLocked: boolean
  disabled: boolean
  onCommitted: () => void
  /** Texto del botón (default: registrar stake en ledger). */
  buttonLabel?: string
}

export function CommitStandardPick({
  stationLocked,
  disabled,
  onCommitted,
  buttonLabel = 'Registrar en protocolo',
}: CommitStandardPickProps) {
  if (stationLocked) {
    return (
      <div className="rounded-lg border border-[#8B5CF6]/30 bg-[#e9ddff]/25 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-[#6d3bd7]">
          Estación cerrada: no puedes registrar nuevas señales hasta el próximo ciclo
        </p>
      </div>
    )
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onCommitted}
      className="w-full rounded-lg border border-[#059669]/40 bg-[#ecfdf5] py-3 text-center text-sm font-bold text-[#065f46] transition-colors hover:bg-[#d1fae5] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-45"
      aria-label={buttonLabel}
    >
      {buttonLabel}
    </button>
  )
}

export type SlideToUnlockProps = {
  stationLocked: boolean
  insufficientDp: boolean
  costDp: number
  disabled: boolean
  onUnlocked: () => void
}

export function SlideToUnlock({
  stationLocked,
  insufficientDp,
  costDp,
  disabled,
  onUnlocked,
}: SlideToUnlockProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [maxX, setMaxX] = useState(0)
  const x = useMotionValue(0)
  const labelOpacity = useTransform(x, [0, maxX * 0.35], [1, 0.25])

  useLayoutEffect(() => {
    const el = trackRef.current
    if (!el) return
    const measure = () => {
      const w = el.clientWidth
      setMaxX(Math.max(0, w - KNOB - PAD * 2))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const onDragEnd = useCallback(() => {
    if (disabled) return
    const current = x.get()
    const threshold = maxX * 0.88
    if (maxX <= 0 || current < threshold) {
      void animate(x, 0, { type: 'spring', stiffness: 520, damping: 38 })
      return
    }
    onUnlocked()
    void animate(x, 0, { duration: 0.2 })
  }, [maxX, onUnlocked, x, disabled])

  if (stationLocked) {
    return (
      <div className="rounded-full border border-[#8B5CF6]/30 bg-[#e9ddff]/25 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-[#6d3bd7]">
          Estación cerrada: sin nuevos desbloqueos hasta el próximo ciclo
        </p>
      </div>
    )
  }

  if (insufficientDp) {
    return (
      <div className="rounded-full border border-[#a4b4be]/40 bg-[#eef4fa]/80 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-[#9e3f4e]">
          Disciplina insuficiente para desbloquear
        </p>
        <p className="mt-1 font-mono text-[10px] tabular-nums text-[#52616a]">
          Se requieren {costDp} DP
        </p>
      </div>
    )
  }

  return (
    <div
      ref={trackRef}
      className={`relative h-12 w-full overflow-hidden rounded-full border border-[#a4b4be]/35 bg-white/90 shadow-inner ${disabled ? 'pointer-events-none opacity-45' : ''}`}
    >
      <motion.span
        style={{ opacity: labelOpacity }}
        className="pointer-events-none absolute inset-0 flex items-center justify-center px-12 text-center text-[11px] font-bold uppercase tracking-wider text-[#6e7d86]"
      >
        Deslizar para desbloquear señal premium · {costDp} DP
      </motion.span>
      <motion.div
        className="absolute top-[6px] left-[6px] flex h-10 w-10 cursor-grab items-center justify-center rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#612aca] text-white shadow-md shadow-[#8B5CF6]/25 active:cursor-grabbing"
        style={{ x }}
        drag={disabled ? false : 'x'}
        dragConstraints={{ left: 0, right: maxX }}
        dragElastic={0}
        dragMomentum={false}
        onDragEnd={onDragEnd}
        whileTap={disabled ? undefined : { scale: 0.97 }}
        aria-label="Deslizar para desbloquear señal premium"
      >
        <span className="text-xs font-bold">→</span>
      </motion.div>
    </div>
  )
}

export type VaultCardVariant = 'disponible' | 'liberado' | 'cerrado'

export type PickCardProps = {
  pick: AnyPick
  /** Tab actual: define acciones permitidas en la tarjeta. */
  vaultCardVariant?: VaultCardVariant
  /** POST /bt2/picks registrado para este ítem de bóveda */
  pickTaken: boolean
  disciplinePoints: number
  /** Slider premium → POST /vault/premium-unlock */
  onPremiumUnlock: (pickId: string) => void
  /** Liberar estándar → POST /vault/standard-unlock */
  onStandardUnlock?: (pickId: string) => void
  /** Marcación tomó / no tomó tras liberar */
  onCommitment?: (pickId: string, c: 'taken' | 'not_taken') => void
  /** Registrar stake → POST /bt2/picks */
  onTakePick: (pickId: string) => void
}

export function UnlockStandardAction({
  stationLocked,
  disabled,
  onUnlocked,
}: {
  stationLocked: boolean
  disabled: boolean
  onUnlocked: () => void
}) {
  if (stationLocked) {
    return (
      <div className="rounded-lg border border-[#059669]/25 bg-[#ecfdf5]/40 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-[#065f46]">
          Estación cerrada: no puedes liberar hasta el próximo ciclo
        </p>
      </div>
    )
  }
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onUnlocked}
      className="w-full rounded-lg border border-[#059669]/40 bg-[#ecfdf5] py-3 text-center text-sm font-bold text-[#065f46] transition-colors hover:bg-[#d1fae5] disabled:cursor-not-allowed disabled:opacity-45"
    >
      Liberar contenido
    </button>
  )
}

export function PickCard({
  pick,
  vaultCardVariant = 'disponible',
  pickTaken,
  disciplinePoints,
  onPremiumUnlock,
  onStandardUnlock,
  onCommitment: _onCommitment,
  onTakePick,
}: PickCardProps) {
  const d = pickDisplay(pick)
  const insufficient = disciplinePoints < d.unlockCostDp
  const isSettled = useTradeStore((s) => s.settledPickIds.includes(d.id))
  const stationLocked = useSessionStore(selectStationLocked)
  const isApi = isApiPick(pick)

  const unavailable = d.isAvailable === false
  const eventUi = vaultPickEventPresentation(
    d.eventStatus,
    d.isAvailable,
    isApi,
  )
  const eventStartLabel = formatEventStartUtc(d.kickoffUtc)
  /**
   * D-05.2-001: si hay `kickoffUtc` válido y ya pasó, bloqueamos Tomar y desbloqueo premium
   * aunque el BE tarde en poner `isAvailable: false` (refuerzo coherente con POST 422).
   */
  const kickoffPast = !pickTaken && isKickoffUtcInPast(d.kickoffUtc)
  const isPremium = !isPickFreeAccess(d.accessTier)
  const contentUnlocked = d.contentUnlocked === true
  const showPreviewOnly = isApi && !contentUnlocked
  const hideDsrBecausePremiumLocked =
    isPremium && !contentUnlocked
  const modelWhy = isApi
    ? modelWhyReading({
        dsrNarrativeEs: d.dsrNarrativeEs,
        traduccionHumana: d.traduccionHumana,
        dsrSource: d.dsrSource,
      })
    : null
  const showApiModelWhy = isApi && !hideDsrBecausePremiumLocked && modelWhy != null

  const takeBlockedVisual = kickoffPast
  const takeBlockedTitle =
    'El evento ya inició según el horario de kickoff; tomar o desbloquear no está disponible.'
  const takeDisabled = unavailable || kickoffPast
  const kickoffUnavailableCopy =
    unavailable && isApi && isKickoffUtcInPast(d.kickoffUtc)



  return (
    <article
      className={`relative flex min-h-[220px] flex-col rounded-xl border border-[#a4b4be]/30 bg-white/85 p-5 shadow-sm`}
      data-pick-id={d.id}
    >
      {takeBlockedVisual ? <span className="sr-only">{takeBlockedTitle}</span> : null}

      {/* S6.1 §5.1: 1. Partido → 2. Competición → 3. Fecha/hora local */}
      <div className="mb-3 min-w-0">
        <h2 className="text-base font-bold leading-snug tracking-tight text-[#26343d]">
          {d.eventLabel}
        </h2>
        {d.titulo ? (
          <p className="mt-1 text-[12px] leading-snug text-[#52616a]">{d.titulo}</p>
        ) : null}
        <p className="mt-1 font-mono text-[10px] text-[#6e7d86]">
          Inicio (tu zona):{' '}
          <span className="text-[#26343d]">{eventStartLabel ?? '—'}</span>
        </p>
      </div>

      {/* Mercado general (sin selección exacta hasta liberar — el API envía selección vacía en preview). */}
      <div className="mb-3 space-y-1">
        <p
          className="text-[11px] font-semibold uppercase tracking-wide text-[#52616a]"
          title={d.marketRaw}
        >
          {d.marketLabel}
        </p>
        {d.selectionSummaryEs ? (
          <p className="text-sm font-semibold leading-snug text-[#26343d]">
            {d.selectionSummaryEs}
          </p>
        ) : null}
      </div>

      {/* Cuota sugerida solo tras liberar */}
      {!pickTaken && contentUnlocked ? (
        <div className="mb-3 rounded-lg border border-[#a4b4be]/25 bg-[#f6fafe]/90 px-3 py-2.5">
          <p className="text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
            Cuota sugerida
          </p>
          <p className="font-mono text-lg font-bold tabular-nums text-[#26343d]">
            {d.suggestedDecimalOdds.toFixed(2)}
          </p>
        </div>
      ) : null}

      {/* Chips en fila (§5); también con pick tomado (Liquidado / En juego) */}
      <div
        className="mb-3 flex flex-wrap items-center gap-1.5"
        role="list"
        aria-label="Estado del pick"
      >
        {isPickFreeAccess(d.accessTier) ? (
          <span
            role="listitem"
            className="rounded-full bg-[#d1fae5] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#065f46]"
          >
            Estándar
          </span>
        ) : (
          <span
            role="listitem"
            className="rounded-full bg-[#e9ddff] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#6d3bd7]"
          >
            Premium
          </span>
        )}
        {eventUi.statusLabel ? (
          <span role="listitem" className={eventUi.badgeClass}>
            {eventUi.statusLabel}
          </span>
        ) : null}
        {isSettled ? (
          <span
            role="listitem"
            className="rounded-full bg-[#e5e7eb] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#374151]"
          >
            Liquidado
          </span>
        ) : null}
        {pickTaken && !isSettled ? (
          <span
            role="listitem"
            className="rounded-full bg-[#dbeafe] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#1d4ed8]"
          >
            En juego
          </span>
        ) : null}
        {isPremium && contentUnlocked && !pickTaken && !isSettled ? (
          <span
            role="listitem"
            className="rounded-full bg-[#ede9fe] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#6d28d9]"
          >
            Premium abierto
          </span>
        ) : null}
        {d.userPickCommitment === 'taken' ? (
          <span
            role="listitem"
            className="rounded-full bg-[#dbeafe] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#1d4ed8]"
          >
            Tomaste la apuesta
          </span>
        ) : null}
        {d.userPickCommitment === 'not_taken' ? (
          <span
            role="listitem"
            className="rounded-full bg-[#f3f4f6] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#4b5563]"
          >
            No tomaste la apuesta
          </span>
        ) : null}
        {!pickTaken && takeBlockedVisual ? (
          <span
            role="listitem"
            className="max-w-[10rem] rounded-full bg-[#fef3c7] px-2 py-0.5 text-center text-[8px] font-bold uppercase leading-tight tracking-wider text-[#92400e]"
          >
            {kickoffPast ? 'Partido empezado' : 'Tomar no disponible'}
          </span>
        ) : null}
        {!pickTaken && unavailable && isApi && !takeBlockedVisual ? (
          <span
            role="listitem"
            className="max-w-[10rem] rounded-full bg-[#fef3c7] px-2 py-0.5 text-center text-[8px] font-bold uppercase leading-tight tracking-wider text-[#92400e]"
            title={
              kickoffUnavailableCopy
                ? 'Kickoff del evento ya pasó (servidor).'
                : 'Evento no disponible para registro.'
            }
          >
            {kickoffUnavailableCopy ? 'Kickoff pasado' : 'No disponible'}
          </span>
        ) : null}
      </div>

      {/* Búsqueda externa del partido: siempre visible (API) para contrastar previa/resultado */}
      {isApi && d.externalSearchUrl ? (
        <div className="mb-3 rounded-lg border border-[#a4b4be]/20 bg-[#eef4fa]/70 px-3 py-2">
          <a
            href={d.externalSearchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] font-bold text-[#6d3bd7] underline-offset-2 hover:underline"
          >
            Buscar partido en Google ↗
          </a>
          <p className="mt-0.5 text-[9px] leading-snug text-[#6e7d86]">
            Referencia externa para confirmar horario, alineaciones o resultado.
          </p>
        </div>
      ) : null}

      {!pickTaken ? (
        <>
          {showPreviewOnly ? (
            <div className="relative mt-auto min-h-[72px] flex-1 overflow-hidden rounded-lg border border-[#26343d]/10 bg-[#f6fafe]/80 p-3">
              <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                Vista previa (sin selección ni cuota completas)
              </p>
              {isPremium ? (
                <p className="text-xs font-semibold text-[#6d3bd7]">
                  Premium · coste liberación {d.unlockCostDp} DP
                </p>
              ) : (
                <p className="text-xs font-semibold text-[#065f46]">Libre · sin DP</p>
              )}
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="mt-auto flex flex-1 flex-col gap-2"
            >
              {showApiModelWhy && modelWhy ? (
                <ModelWhyBlock
                  title={modelWhy.title}
                  body={modelWhy.body}
                  lineClampClass="line-clamp-6"
                  reviewHref={`/v2/settlement/${d.id}?phase=review`}
                  showReviewLink={false}
                />
              ) : !isApi && d.traduccionHumana ? (
                <div className="rounded-lg border border-[#26343d]/10 bg-[#f6fafe]/80 p-3">
                  <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                    Por qué lo sugiere el modelo
                  </p>
                  <p className="line-clamp-6 text-xs leading-relaxed text-[#26343d]">
                    {d.traduccionHumana}
                  </p>
                </div>
              ) : null}
              {isApi && contentUnlocked ? (
                <PickSignalCollapsibleEs
                  estimatedHit={d.estimatedHitProbability}
                  evidenceQ={d.evidenceQuality}
                  predictiveQ={d.predictiveTier}
                  actionQ={d.actionTier}
                />
              ) : null}
            </motion.div>
          )}

          {vaultCardVariant === 'disponible' && showPreviewOnly && d.unlockEligible ? (
            <div className="mt-3">
              {isPremium ? (
                <SlideToUnlock
                  stationLocked={stationLocked}
                  insufficientDp={insufficient}
                  costDp={d.unlockCostDp}
                  disabled={!d.unlockEligible || kickoffPast}
                  onUnlocked={() => onPremiumUnlock(d.id)}
                />
              ) : (
                <UnlockStandardAction
                  stationLocked={stationLocked}
                  disabled={kickoffPast}
                  onUnlocked={() => onStandardUnlock?.(d.id)}
                />
              )}
            </div>
          ) : null}

          {vaultCardVariant === 'liberado' && contentUnlocked ? (
            <div className="mt-3 space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <NavLink
                  to={`/v2/settlement/${d.id}?phase=review`}
                  className="flex min-h-[44px] items-center justify-center rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2.5 text-center text-sm font-bold text-[#26343d] transition-colors hover:bg-[#eef4fa]"
                >
                  Detalle
                </NavLink>
                <div className="min-w-0">
                  {unavailable ? (
                    <div className="flex min-h-[44px] items-center justify-center rounded-lg border border-[#a4b4be]/25 bg-[#f6fafe] px-2 text-center text-[10px] font-semibold text-[#6e7d86]">
                      No disponible
                    </div>
                  ) : (
                    <CommitStandardPick
                      stationLocked={stationLocked}
                      disabled={takeDisabled}
                      onCommitted={() => onTakePick(d.id)}
                    />
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="mt-2 flex flex-1 flex-col gap-3"
        >
          <div className="flex items-center gap-4 rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] px-3 py-2">
            <div>
              <p className="text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                Cuota sugerida
              </p>
              <p className="font-mono text-base font-semibold text-[#26343d]">
                {d.suggestedDecimalOdds.toFixed(2)}
              </p>
            </div>
            {d.curvaEquidad ? (
              <div className="flex-1 rounded-lg border border-[#a4b4be]/20 bg-[#eef4fa] p-2">
                <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                  Curva de equity (CDM)
                </p>
                <EquitySparkline
                  values={d.curvaEquidad}
                  className="h-10 w-full text-[#059669]"
                />
              </div>
            ) : null}
          </div>

          {showApiModelWhy && modelWhy ? (
            <ModelWhyBlock
              title={modelWhy.title}
              body={modelWhy.body}
              lineClampClass="line-clamp-5"
              reviewHref={`/v2/settlement/${d.id}?phase=review`}
            />
          ) : !isApi && d.traduccionHumana ? (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#6e7d86]">
                Por qué lo sugiere el modelo
              </p>
              <p className="line-clamp-5 text-sm leading-relaxed text-[#26343d]">
                {d.traduccionHumana}
              </p>
              <NavLink
                to={`/v2/settlement/${d.id}?phase=review`}
                className="mt-2 inline-block text-xs font-bold text-[#6d3bd7] underline-offset-2 hover:underline"
              >
                Ver ficha completa
              </NavLink>
            </div>
          ) : null}
          {isApi && contentUnlocked ? (
            <PickSignalCollapsibleEs
              estimatedHit={d.estimatedHitProbability}
              evidenceQ={d.evidenceQuality}
              predictiveQ={d.predictiveTier}
              actionQ={d.actionTier}
            />
          ) : null}

          {isSettled ? (
            <div className="space-y-2">
              <p className="rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-2 text-center text-xs font-semibold text-[#52616a]">
                Archivado en ledger
              </p>
              <NavLink
                to={`/v2/settlement/${d.id}`}
                className="flex min-h-[44px] w-full items-center justify-center rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2.5 text-center text-sm font-bold text-[#26343d] transition-colors hover:bg-[#eef4fa]"
              >
                Ver ficha (solo lectura)
              </NavLink>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <NavLink
                to={`/v2/settlement/${d.id}`}
                className="flex min-h-[44px] items-center justify-center rounded-lg border border-[#8B5CF6]/35 bg-[#e9ddff]/25 px-3 py-2.5 text-center text-sm font-bold text-[#6d3bd7] transition-colors hover:bg-[#e9ddff]/45"
              >
                Liquidar
              </NavLink>
              <NavLink
                to={`/v2/settlement/${d.id}?phase=review`}
                className="flex min-h-[44px] items-center justify-center rounded-lg border border-[#a4b4be]/30 bg-white px-3 py-2.5 text-center text-sm font-bold text-[#26343d] hover:bg-[#eef4fa]"
              >
                Detalle
              </NavLink>
            </div>
          )}
        </motion.div>
      )}
    </article>
  )
}
