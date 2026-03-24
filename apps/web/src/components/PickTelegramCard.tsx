import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  formatCOP,
  formatShortDateFromYMD,
  kickoffReadableCol,
} from '@/lib/formatDateTime'
import {
  describeMarketKind,
  describeSelectionPlain,
} from '@/lib/marketCopy'
import {
  confidenceTierFromLabel,
  tierLabelEs,
} from '@/lib/stakeSuggestion'

const DIV = 'border-t border-app-line'

type OddsRef = Record<string, unknown> | null | undefined

function refStr(ref: OddsRef, key: string): string | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = ref[key]
  if (v == null) return undefined
  return String(v)
}

function refNum(ref: OddsRef, key: string): number | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = ref[key]
  if (typeof v === 'number' && !Number.isNaN(v)) return v
  if (typeof v === 'string') {
    const n = Number.parseFloat(v.replace(',', '.'))
    return Number.isNaN(n) ? undefined : n
  }
  return undefined
}

export type PickCardData = {
  pick_id: number
  daily_run_id: number
  event_id: number
  market: string
  selection: string
  picked_value?: number | null
  odds_reference?: unknown
  event_label?: string | null
  league?: string | null
  kickoff_display?: string | null
  /** ISO UTC (Z); bloqueo tomé/monto +100 min tras inicio. */
  kickoff_at_utc?: string | null
  created_at_utc?: string
  result?: {
    outcome: string
    home_score?: number | null
    away_score?: number | null
    result_1x2?: string | null
  } | null
  user_taken?: boolean | null
  risk_category?: string | null
  decision_origin?: string | null
  stake_amount?: number | null
  /** Cierre manual (tablero); prioridad sobre validación automática. */
  user_outcome?: 'win' | 'loss' | 'pending' | null
  /** Solo pick_results / SofaScore (sin fusionar con user_outcome). */
  system_outcome?: 'win' | 'loss' | 'pending' | null
  /** Dashboard: texto legible de selección desde odds_reference */
  selection_display?: string | null
}

/** Resultado mostrado en UI y P/L: primero el usuario, luego sistema. */
function effectivePickOutcome(
  p: PickCardData,
): 'win' | 'loss' | 'pending' | null {
  const u = p.user_outcome
  if (u === 'win' || u === 'loss' || u === 'pending') return u
  const s = p.system_outcome ?? p.result?.outcome
  if (s === 'win' || s === 'loss' || s === 'pending') return s
  return null
}

function systemOutcomeRaw(p: PickCardData): 'win' | 'loss' | 'pending' | null {
  const s = p.system_outcome ?? p.result?.outcome
  if (s === 'win' || s === 'loss' || s === 'pending') return s
  return null
}

function outcomePill(outcome: string | undefined) {
  if (outcome === 'win')
    return (
      <span className="rounded-full border border-emerald-200 bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-900 shadow-sm">
        Ganada
      </span>
    )
  if (outcome === 'loss')
    return (
      <span className="rounded-full border border-red-200 bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-900 shadow-sm">
        Perdida
      </span>
    )
  return (
    <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-900 shadow-sm">
      Pendiente
    </span>
  )
}

function confTierBadgeClass(tier: ReturnType<typeof confidenceTierFromLabel>) {
  switch (tier) {
    case 'high':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'medium':
      return 'border-sky-200 bg-sky-50 text-sky-950'
    case 'low':
      return 'border-amber-200 bg-amber-50 text-amber-950'
    default:
      return 'border-neutral-200 bg-neutral-100 text-neutral-700'
  }
}

function isMarket1x2(market: string) {
  return String(market).trim().toUpperCase() === '1X2'
}

/** P/L simple si tomaste el pick y hay stake + cuota (solo cuando ya hay win/loss). */
function plEstimateLine(p: PickCardData): string | null {
  if (p.user_taken !== true) return null
  const stake = p.stake_amount
  const odds = p.picked_value
  if (stake == null || odds == null) return null
  const o = effectivePickOutcome(p)
  if (o === 'win')
    return `+${formatCOP(stake * (odds - 1))} (est.)`
  if (o === 'loss') return `−${formatCOP(stake)} (est.)`
  return null
}

export function OutcomeFeedbackBlock({
  p,
  className = 'mx-3 mb-2',
}: {
  p: PickCardData
  className?: string
}) {
  const eff = effectivePickOutcome(p)
  const sys = systemOutcomeRaw(p)
  const plLine = plEstimateLine(p)
  const scoreLine =
    p.result &&
    (p.result.home_score != null || p.result.away_score != null)
      ? `Marcador ${p.result.home_score ?? '—'} — ${p.result.away_score ?? '—'}`
      : null
  const manual =
    p.user_outcome === 'win' ||
    p.user_outcome === 'loss' ||
    p.user_outcome === 'pending'
  const manualVsSys =
    manual &&
    sys != null &&
    eff != null &&
    sys !== 'pending' &&
    eff !== 'pending' &&
    sys !== eff

  const sourceLine = manual
    ? 'Usamos el resultado que marcaste tú en «Tu seguimiento».'
    : sys != null
      ? 'El resultado lo tomamos del marcador cuando el sistema ya pudo validarlo.'
      : null

  if (eff == null) {
    return (
      <div
        className={`${className} rounded-lg border border-dashed border-app-line bg-neutral-50 px-3 py-2.5`}
      >
        <p className="text-[11px] font-semibold text-app-fg">
          Resultado: sin datos aún
        </p>
        <p className="mt-1 text-[10px] leading-relaxed text-app-muted">
          Puedes marcar en «Tu seguimiento» si quedó ganada, perdida o pendiente.
          {isMarket1x2(p.market)
            ? ' En apuestas al resultado del partido (1-X-2) el sistema a veces puede cerrarlo solo cuando hay marcador final.'
            : ' En mercados distintos al marcador final suele tocarse a mano.'}
        </p>
      </div>
    )
  }

  if (eff === 'win') {
    return (
      <div
        className={`${className} rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5`}
      >
        <p className="text-xs font-semibold text-emerald-900">Has ganado este pick</p>
        {sourceLine && (
          <p className="mt-1 text-[10px] leading-relaxed text-emerald-900/85">
            {sourceLine}
          </p>
        )}
        {manualVsSys && (
          <p className="mt-1 text-[10px] leading-relaxed text-amber-900">
            El sistema tenía{' '}
            {sys === 'win' ? 'ganada' : 'perdida'}; mostramos tu cierre.
          </p>
        )}
        {scoreLine && (
          <p className="mt-1 font-mono text-[11px] text-emerald-800 tabular-nums">
            {scoreLine}
            {p.result?.result_1x2
              ? ` · 1X2 final ${p.result.result_1x2}`
              : ''}
          </p>
        )}
        {plLine && (
          <p className="mt-1 font-mono text-[11px] font-medium text-emerald-900 tabular-nums">
            Con tu monto apostado (estimado): {plLine}
          </p>
        )}
      </div>
    )
  }

  if (eff === 'loss') {
    return (
      <div
        className={`${className} rounded-lg border border-red-200 bg-red-50 px-3 py-2.5`}
      >
        <p className="text-xs font-semibold text-red-900">Has perdido este pick</p>
        {sourceLine && (
          <p className="mt-1 text-[10px] leading-relaxed text-red-900/85">
            {sourceLine}
          </p>
        )}
        {manualVsSys && (
          <p className="mt-1 text-[10px] leading-relaxed text-amber-900">
            El sistema tenía{' '}
            {sys === 'win' ? 'ganada' : 'perdida'}; mostramos tu cierre.
          </p>
        )}
        {scoreLine && (
          <p className="mt-1 font-mono text-[11px] text-red-800/90 tabular-nums">
            {scoreLine}
            {p.result?.result_1x2
              ? ` · 1X2 final ${p.result.result_1x2}`
              : ''}
          </p>
        )}
        {plLine && (
          <p className="mt-1 font-mono text-[11px] font-medium text-red-900 tabular-nums">
            Con tu monto apostado (estimado): {plLine}
          </p>
        )}
      </div>
    )
  }

  return (
    <div
      className={`${className} rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-2.5`}
    >
      <p className="text-xs font-semibold text-amber-950">Resultado pendiente</p>
      {manual ? (
        <p className="mt-1 text-[10px] leading-relaxed text-amber-900/90">
          Lo dejaste en pendiente a propósito. Cuando quieras, cámbialo en «Tu
          seguimiento».
        </p>
      ) : (
        <p className="mt-1 text-[10px] leading-relaxed text-amber-900/90">
          Aún no hay resultado claro (partido en curso o sin datos). Puedes
          cerrarlo a mano cuando sepas qué pasó.
        </p>
      )}
      {scoreLine && (
        <p className="mt-1 font-mono text-[10px] text-amber-900/80 tabular-nums">
          {scoreLine}
        </p>
      )}
    </div>
  )
}

export function PickTelegramCard({
  p,
  compact,
  detailHref,
  /** Día del run (YYYY-MM-DD): mismo calendario que el listado / histórico. */
  runDate,
  /** 1-based en el carrusel o lista del día. */
  pickOrdinal,
  /** Controles de tracking (tomé, riesgo, etc.): van dentro de la misma card */
  trackingSlot,
}: {
  p: PickCardData
  compact?: boolean
  detailHref?: string
  runDate?: string | null
  pickOrdinal?: number
  trackingSlot?: ReactNode
}) {
  const ref = p.odds_reference as OddsRef
  const selShow =
    p.selection_display ?? refStr(ref, 'selection_display') ?? p.selection
  const razon = refStr(ref, 'razon')
  const conf = refStr(ref, 'confianza')
  const edge = refNum(ref, 'edge_pct')
  const oddsSource = refStr(ref, 'odds_source')
  const tier = confidenceTierFromLabel(conf)
  const confChipText =
    conf?.trim() && conf.trim().length > 0
      ? `Confianza del modelo: ${conf.trim()}`
      : tierLabelEs(tier)
  const kickoffCol = kickoffReadableCol(p.kickoff_display ?? null)

  const title =
    p.event_label?.trim() ||
    `Evento ${p.event_id}`

  const href = detailHref ?? `/picks/${p.pick_id}`

  return (
    <article
      className={`flex h-full min-w-[18rem] max-w-[22rem] shrink-0 flex-col rounded-xl border border-app-line bg-app-card shadow-sm ${
        compact ? 'text-[11px]' : 'text-xs'
      }`}
    >
      <div className={`border-b border-app-line px-3 py-2 ${compact ? 'py-1.5' : ''}`}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            {pickOrdinal != null && pickOrdinal > 0 && (
              <p className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-800">
                Pick {pickOrdinal}
              </p>
            )}
            <p className="font-semibold leading-snug text-app-fg">{title}</p>
            {p.league?.trim() ? (
              <p className="mt-0.5 text-[10px] leading-relaxed text-app-muted">
                {p.league.trim()}
              </p>
            ) : null}
            {kickoffCol ? (
              <p className="mt-0.5 text-[10px] leading-relaxed text-app-fg">
                <span className="text-app-muted">Inicio del partido: </span>
                <span className="font-mono font-medium tabular-nums">
                  {kickoffCol}
                </span>
              </p>
            ) : null}
            {runDate?.trim() ? (
              <p className="mt-0.5 text-[10px] text-app-muted">
                Día del análisis (calendario del run):{' '}
                <span className="font-mono text-app-fg tabular-nums">
                  {formatShortDateFromYMD(runDate.trim())}
                </span>
              </p>
            ) : null}
          </div>
          {outcomePill(effectivePickOutcome(p) ?? 'pending')}
        </div>
        {p.result &&
          (p.result.home_score != null || p.result.away_score != null) && (
            <p className="mt-1 font-mono text-[11px] text-app-muted tabular-nums">
              Marcador: {p.result.home_score ?? '—'} — {p.result.away_score ?? '—'}
              {p.result.result_1x2
                ? ` · 1X2 final ${p.result.result_1x2}`
                : ''}
            </p>
          )}
      </div>

      <div className="flex flex-1 flex-col gap-0 px-3 py-2">
        <p className="text-[10px] font-medium uppercase tracking-wide text-app-muted">
          Apuesta
        </p>
        <p className="mt-0.5">
          <span className="inline-block rounded border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-violet-900">
            {p.market.trim()}
          </span>
        </p>
        <p className="mt-1 text-[10px] leading-relaxed text-app-fg">
          {describeMarketKind(p.market)}
        </p>
        <p className="mt-1.5">
          <span className="text-app-muted">Código en el boletín:</span>{' '}
          <span className="font-mono font-medium text-app-fg">{selShow}</span>
        </p>
        <p className="mt-0.5 text-[10px] leading-relaxed text-sky-950">
          <span className="font-medium text-sky-900">Resumen:</span>{' '}
          {describeSelectionPlain(p.market, p.selection, p.event_label)}
        </p>
        {p.picked_value != null && (
          <p className="mt-0.5 font-mono tabular-nums">
            <span className="text-app-muted">Cuota (pago si aciertas):</span>{' '}
            <span className="text-app-fg">{p.picked_value}</span>
            {oddsSource === 'scraped_sofascore' ? (
              <span className="ml-1 font-sans text-[9px] font-normal text-app-muted">
                · snapshot SofaScore (ingesta)
              </span>
            ) : null}
          </p>
        )}
        {((conf?.trim() || tier !== 'unknown') || edge != null) && (
          <div
            className={`mt-2 flex flex-wrap items-center gap-1.5 ${DIV} pt-2`}
          >
            {(conf?.trim() || tier !== 'unknown') && (
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${confTierBadgeClass(tier)}`}
              >
                {confChipText}
              </span>
            )}
            {edge != null && (
              <span className="rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 font-mono text-[10px] font-medium text-teal-950 tabular-nums">
                Ventaja que ve el modelo: {edge}%
              </span>
            )}
          </div>
        )}
        {razon && (
          <p className={`mt-2 leading-relaxed text-app-fg ${DIV} pt-2`}>
            <span className="text-app-muted">Por qué lo sugiere el modelo:</span>{' '}
            {razon}
          </p>
        )}
      </div>

      <OutcomeFeedbackBlock p={p} />

      {trackingSlot != null && (
        <div className={`${DIV} bg-gradient-to-b from-violet-50/90 to-sky-50/40 px-3 py-3`}>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-violet-900">
            Tu seguimiento
          </p>
          {trackingSlot}
        </div>
      )}

      <div className={`mt-auto ${DIV} px-3 py-2`}>
        {trackingSlot == null && (
          <div className="flex flex-wrap items-center gap-2 text-[10px]">
            <span
              className={
                p.user_taken === true
                  ? 'rounded-md border border-violet-300 bg-violet-600 px-1.5 py-0.5 font-medium text-white shadow-sm'
                  : p.user_taken === false
                    ? 'rounded-md border border-neutral-200 bg-neutral-100 px-1.5 py-0.5 text-app-muted'
                    : 'text-app-muted'
              }
            >
              {p.user_taken === true
                ? 'Tomado'
                : p.user_taken === false
                  ? 'No tomado'
                  : 'Tomado —'}
            </span>
            {p.decision_origin && (
              <span className="rounded-full border border-amber-200 bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-950">
                {p.decision_origin}
              </span>
            )}
            {p.stake_amount != null && (
              <span className="rounded-full border border-cyan-200 bg-cyan-50 px-2 py-0.5 font-mono text-[10px] font-medium text-cyan-950 tabular-nums">
                {formatCOP(p.stake_amount)}
              </span>
            )}
          </div>
        )}
        <Link
          to={href}
          className="mt-2 inline-block text-[11px] font-semibold text-violet-800 underline decoration-violet-300 underline-offset-2 hover:text-violet-950"
        >
          Ver ficha →
        </Link>
      </div>
    </article>
  )
}
