/**
 * US-FE-003 / US-FE-025 / US-FE-034: PickCard mock + API.
 * D-05-009 / D-05-010: preview traduccionHumana; Detalle → settlement ?phase=review; Tomar/Liquidar.
 */
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import type { VaultPickCdm } from '@/data/vaultMockPicks'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import {
  dsrConfidenceLabelEs,
  dsrSourceDescriptionEs,
} from '@/lib/bt2ProtocolLabels'
import { displayMarketLabelEs } from '@/lib/marketCanonicalDisplay'
import { getMarketLabelEs } from '@/lib/marketLabels'
import { isKickoffUtcInPast } from '@/lib/vaultKickoff'
import { unifiedApiModelReading } from '@/lib/vaultModelReading'
import { vaultPickEventPresentation } from '@/lib/vaultPickEventUi'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'

const KNOB = 40
const PAD = 6
/** D-05-009: extracto visible antes de compromiso / desbloqueo */
const TRADUCCION_PREVIEW_CHARS = 240
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

function excerptTraduccion(text: string, max = TRADUCCION_PREVIEW_CHARS): string {
  const t = text.trim()
  if (!t) return ''
  if (t.length <= max) return t
  return `${t.slice(0, max).trim()}…`
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
      dsrNarrativeEs: (p.dsrNarrativeEs ?? '').trim(),
      dsrSource: (p.dsrSource ?? '').trim(),
      dsrConfidenceLabel: (p.dsrConfidenceLabel ?? '').trim(),
      pipelineVersion: (p.pipelineVersion ?? '').trim(),
      modelCanonicalHint:
        [p.modelMarketCanonical, p.modelSelectionCanonical]
          .map((x) => (typeof x === 'string' ? x.trim() : ''))
          .filter(Boolean)
          .join(' · ') || '',
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
    dsrNarrativeEs: '',
    dsrSource: '',
    dsrConfidenceLabel: '',
    pipelineVersion: '',
    modelCanonicalHint: '',
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
}

export function CommitStandardPick({
  stationLocked,
  disabled,
  onCommitted,
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
      aria-label="Tomar este pick estándar (sin coste en DP)"
    >
      Tomar pick
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

export type PickCardProps = {
  pick: AnyPick
  /** POST /bt2/picks registrado para este ítem de bóveda */
  pickTaken: boolean
  /**
   * Desbloqueo premium pagado (API). En mock/open no aplica; el padre puede pasar true.
   */
  premiumUnlocked: boolean
  disciplinePoints: number
  /** Slider premium → POST /vault/premium-unlock */
  onPremiumUnlock: (pickId: string) => void
  /** Tomar / registrar → POST /bt2/picks */
  onTakePick: (pickId: string) => void
  /**
   * Sprint 05.2 — cupo diario 3+2: bloquea solo **Tomar**, no el desbloqueo premium.
   */
  takeBlockedByDailyQuota?: boolean
}

export function PickCard({
  pick,
  pickTaken,
  premiumUnlocked,
  disciplinePoints,
  onPremiumUnlock,
  onTakePick,
  takeBlockedByDailyQuota = false,
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
  const premiumOpen = !isPremium || premiumUnlocked
  const showPreviewOnly = !pickTaken && !premiumOpen
  const premiumLockedSurface = isPremium && showPreviewOnly
  const unifiedApiBody = isApi
    ? unifiedApiModelReading({
        dsrNarrativeEs: d.dsrNarrativeEs,
        traduccionHumana: d.traduccionHumana,
      })
    : null
  const previewText =
    unifiedApiBody != null
      ? excerptTraduccion(unifiedApiBody.body)
      : d.traduccionHumana
        ? excerptTraduccion(d.traduccionHumana)
        : ''
  const hideDsrBecausePremiumLocked =
    isPremium && !pickTaken && !premiumUnlocked
  const dsrMetaLine = [
    d.dsrConfidenceLabel
      ? `Confianza simbólica: ${dsrConfidenceLabelEs(d.dsrConfidenceLabel)}`
      : '',
    dsrSourceDescriptionEs(d.dsrSource),
    d.pipelineVersion ? `Versión pipeline: ${d.pipelineVersion}` : '',
  ]
    .filter(Boolean)
    .join(' · ')

  const takeBlockedVisual = kickoffPast
  const takeBlockedTitle =
    'El evento ya inició según el horario de kickoff; tomar o desbloquear no está disponible.'
  const takeDisabled =
    unavailable || kickoffPast || takeBlockedByDailyQuota
  const kickoffUnavailableCopy =
    unavailable && isApi && isKickoffUtcInPast(d.kickoffUtc)

  const articleClass = [
    eventUi.dimCard || takeBlockedVisual || (unavailable && isApi)
      ? 'opacity-50 saturate-75'
      : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <article
      title={takeBlockedVisual ? takeBlockedTitle : undefined}
      className={`relative flex min-h-[220px] flex-col rounded-xl border border-[#a4b4be]/30 bg-white/85 p-5 shadow-sm ${articleClass}`}
      data-pick-id={d.id}
    >
      <header className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p
            className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]"
            title={d.marketRaw}
          >
            {d.marketLabel}
          </p>
          {d.selectionSummaryEs ? (
            <p className="mt-0.5 text-xs font-semibold text-[#26343d]">
              {d.selectionSummaryEs}
            </p>
          ) : null}
          {d.modelCanonicalHint && !premiumLockedSurface ? (
            <p
              className="mt-0.5 font-mono text-[9px] leading-snug text-[#6e7d86]"
              title="Sugerencia DSR (mercado y selección canónicos)"
            >
              Modelo (canónico): {d.modelCanonicalHint}
            </p>
          ) : null}
          <h2 className="mt-1 text-base font-bold leading-snug tracking-tight text-[#26343d]">
            {d.eventLabel}
          </h2>
          {!premiumLockedSurface ? (
            <p className="mt-0.5 text-[11px] leading-snug text-[#52616a]">
              {d.titulo}
            </p>
          ) : null}
          <p className="mt-1 font-mono text-[10px] text-[#6e7d86]">
            Inicio (tu zona):{' '}
            <span className="text-[#26343d]">{eventStartLabel ?? '—'}</span>
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {isSettled ? (
            <span className="rounded-full bg-[#e5e7eb] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#374151]">
              Liquidado
            </span>
          ) : null}
          {pickTaken && !isSettled ? (
            <span className="rounded-full bg-[#dbeafe] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#1d4ed8]">
              En juego
            </span>
          ) : null}
          {isPremium && premiumUnlocked && !pickTaken && !isSettled ? (
            <span className="rounded-full bg-[#ede9fe] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#6d28d9]">
              Premium abierto
            </span>
          ) : null}
          {takeBlockedVisual ? (
            <span
              className="max-w-[9rem] rounded-full bg-[#fef3c7] px-2 py-0.5 text-center text-[8px] font-bold uppercase leading-tight tracking-wider text-[#92400e]"
              title={takeBlockedTitle}
            >
              {kickoffPast ? 'Kickoff pasado' : 'Tomar no disponible'}
            </span>
          ) : null}
          {unavailable && isApi && !takeBlockedVisual ? (
            <span
              className="max-w-[9rem] rounded-full bg-[#fee2e2] px-2 py-0.5 text-center text-[8px] font-bold uppercase leading-tight tracking-wider text-[#9b1c1c]"
              title={
                kickoffUnavailableCopy
                  ? 'Kickoff del evento ya pasó (servidor).'
                  : 'Evento no disponible para registro.'
              }
            >
              {kickoffUnavailableCopy ? 'Kickoff pasado' : 'No disponible'}
            </span>
          ) : null}
          {d.edgeBps && !premiumLockedSurface ? (
            <span className="rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] px-2 py-1 font-mono text-xs font-bold tabular-nums text-[#26343d]">
              +{(d.edgeBps / 100).toFixed(2)}%
            </span>
          ) : null}
          {isPickFreeAccess(d.accessTier) ? (
            <span className="rounded-full bg-[#d1fae5] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#065f46]">
              Estándar
            </span>
          ) : (
            <span className="rounded-full bg-[#e9ddff] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#6d3bd7]">
              Premium
            </span>
          )}
          {eventUi.statusLabel ? (
            <span className={eventUi.badgeClass}>{eventUi.statusLabel}</span>
          ) : null}
        </div>
      </header>

      {!pickTaken ? (
        <>
          {showPreviewOnly ? (
            premiumLockedSurface ? (
              <div className="mt-auto rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa]/70 p-3">
                <p className="mb-2 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                  Antes del desbloqueo (solo datos de mercado)
                </p>
                <dl className="space-y-1.5 text-xs">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <dt className="text-[#6e7d86]">Inicio (tu zona)</dt>
                    <dd className="font-mono text-[11px] font-semibold tabular-nums text-[#26343d]">
                      {eventStartLabel ?? '—'}
                    </dd>
                  </div>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <dt className="text-[#6e7d86]">Cuota sugerida</dt>
                    <dd className="font-mono text-sm font-bold tabular-nums text-[#26343d]">
                      {d.suggestedDecimalOdds.toFixed(2)}
                    </dd>
                  </div>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <dt className="text-[#6e7d86]">Coste desbloqueo</dt>
                    <dd className="font-mono text-sm font-bold tabular-nums text-[#6d3bd7]">
                      {d.unlockCostDp} DP
                    </dd>
                  </div>
                </dl>
              </div>
            ) : (
              <div className="relative mt-auto min-h-[88px] flex-1 overflow-hidden rounded-lg border border-[#26343d]/10 bg-[#f6fafe]/80 p-3">
                <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                  Vista previa · modelo
                </p>
                <p className="mb-2 font-mono text-[10px] text-[#52616a]">
                  Inicio: <span className="font-semibold text-[#26343d]">{eventStartLabel ?? '—'}</span>
                  {eventUi.statusLabel ? (
                    <>
                      {' '}
                      ·{' '}
                      <span className="text-[#6e7d86]">{eventUi.statusLabel}</span>
                    </>
                  ) : null}
                </p>
                <p className="line-clamp-4 text-xs leading-relaxed text-[#26343d]">
                  {previewText ||
                    'Sin criterio DSR ni extracto de lectura en este pick.'}
                </p>
                {dsrMetaLine && !premiumLockedSurface ? (
                  <p className="mt-2 font-mono text-[9px] leading-snug text-[#6e7d86]">
                    {dsrMetaLine}
                  </p>
                ) : null}
              </div>
            )
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="mt-auto flex flex-1 flex-col gap-2"
            >
              {isApi && !hideDsrBecausePremiumLocked && unifiedApiBody ? (
                <div className="rounded-lg border border-[#6d3bd7]/15 bg-[#f6fafe]/90 p-3">
                  <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                    {unifiedApiBody.title}
                  </p>
                  <p className="line-clamp-6 text-xs leading-relaxed text-[#26343d]">
                    {unifiedApiBody.body}
                  </p>
                  {dsrMetaLine ? (
                    <p className="mt-2 font-mono text-[9px] leading-snug text-[#6e7d86]">
                      {dsrMetaLine}
                    </p>
                  ) : null}
                </div>
              ) : !isApi && d.traduccionHumana ? (
                <div className="rounded-lg border border-[#26343d]/10 bg-[#f6fafe]/80 p-3">
                  <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                    Lectura del modelo
                  </p>
                  <p className="line-clamp-6 text-xs leading-relaxed text-[#26343d]">
                    {d.traduccionHumana}
                  </p>
                </div>
              ) : null}
            </motion.div>
          )}

          {!pickTaken && (unavailable || kickoffPast) ? (
            <p className="mt-3 text-center text-xs font-semibold text-[#9b1c1c]">
              {kickoffPast
                ? 'El partido ya inició según el horario del evento; no puedes registrar ni desbloquear esta señal.'
                : kickoffUnavailableCopy
                  ? 'El partido ya inició; no es posible registrar el pick (protocolo).'
                  : 'Este evento no está disponible para registro en el protocolo.'}
            </p>
          ) : null}
          {takeBlockedByDailyQuota && !pickTaken ? (
            <p className="mt-2 text-center text-[11px] font-medium text-[#92400e]">
              {isPickFreeAccess(d.accessTier)
                ? 'Cupo diario de señales estándar agotado (3 por día operativo).'
                : 'Cupo diario de señales premium agotado (2 por día operativo).'}
            </p>
          ) : null}

          {isPickFreeAccess(d.accessTier) ? (
            <div className="mt-3 grid grid-cols-2 gap-2">
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
          ) : showPreviewOnly ? (
            <div className="mt-3">
              {unavailable ? (
                <div className="flex min-h-[44px] items-center justify-center rounded-lg border border-[#a4b4be]/25 bg-[#f6fafe] px-3 py-3 text-center text-sm font-semibold text-[#6e7d86]">
                  No disponible para registro
                </div>
              ) : (
                <SlideToUnlock
                  stationLocked={stationLocked}
                  insufficientDp={insufficient}
                  costDp={d.unlockCostDp}
                  disabled={unavailable || kickoffPast}
                  onUnlocked={() => onPremiumUnlock(d.id)}
                />
              )}
            </div>
          ) : (
            <div className="mt-3 grid grid-cols-2 gap-2">
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
          )}
        </>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="mt-2 flex flex-1 flex-col gap-3"
        >
          {isApi && !hideDsrBecausePremiumLocked && unifiedApiBody ? (
            <div className="rounded-lg border border-[#6d3bd7]/15 bg-[#f6fafe]/90 p-3">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#6e7d86]">
                {unifiedApiBody.title}
              </p>
              <p className="line-clamp-5 text-sm leading-relaxed text-[#26343d]">
                {unifiedApiBody.body}
              </p>
              {dsrMetaLine ? (
                <p className="mt-2 font-mono text-[9px] leading-snug text-[#6e7d86]">
                  {dsrMetaLine}
                </p>
              ) : null}
              <NavLink
                to={`/v2/settlement/${d.id}?phase=review`}
                className="mt-2 inline-block text-xs font-bold text-[#6d3bd7] underline-offset-2 hover:underline"
              >
                Ver ficha completa
              </NavLink>
            </div>
          ) : !isApi && d.traduccionHumana ? (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#6e7d86]">
                Lectura del modelo
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
            ) : d.externalSearchUrl ? (
              <a
                href={d.externalSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 rounded-lg border border-[#a4b4be]/20 bg-[#eef4fa] p-2 text-center text-[10px] font-semibold text-[#6d3bd7] hover:bg-[#e9ddff]/30"
              >
                Ver resultado ↗
              </a>
            ) : null}
          </div>

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
