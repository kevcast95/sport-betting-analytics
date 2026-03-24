import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

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
export function effectivePickOutcome(
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
      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-800">
        Ganada
      </span>
    )
  if (outcome === 'loss')
    return (
      <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-800">
        Perdida
      </span>
    )
  return (
    <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
      Pendiente
    </span>
  )
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
    return `+${(stake * (odds - 1)).toFixed(2)} (est.)`
  if (o === 'loss') return `−${stake.toFixed(2)} (est.)`
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
    ? 'Cierre declarado por ti — no hace falta consultar SofaScore para este pick.'
    : sys != null
      ? 'Validación automática (1X2 / job validate_picks).'
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
          Puedes marcar ganado / perdido / pendiente en «Tu seguimiento» para no
          depender de validación externa. Si prefieres automático,{' '}
          {isMarket1x2(p.market)
            ? 'tras el partido puedes ejecutar validate_picks (1X2).'
            : 'el job solo cubre 1X2; el resto suele quedar manual.'}
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
            P/L con tu stake: {plLine}
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
            P/L con tu stake: {plLine}
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
          Lo marcaste como pendiente a propósito. Cuando quieras, actualiza el
          cierre en «Tu seguimiento».
        </p>
      ) : (
        <p className="mt-1 text-[10px] leading-relaxed text-amber-900/90">
          Partido no finalizado o sin marcador en SofaScore. Puedes cerrar a mano
          o volver a ejecutar validate_picks más tarde.
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
  /** Controles de tracking (tomé, riesgo, etc.): van dentro de la misma card */
  trackingSlot,
}: {
  p: PickCardData
  compact?: boolean
  detailHref?: string
  trackingSlot?: ReactNode
}) {
  const ref = p.odds_reference as OddsRef
  const selShow =
    p.selection_display ?? refStr(ref, 'selection_display') ?? p.selection
  const razon = refStr(ref, 'razon')
  const conf = refStr(ref, 'confianza')
  const edge = refNum(ref, 'edge_pct')
  const dateLine =
    p.created_at_utc && p.created_at_utc.length >= 10
      ? p.created_at_utc.slice(0, 10)
      : undefined
  const timeLine =
    p.created_at_utc && p.created_at_utc.length >= 16
      ? p.created_at_utc.slice(11, 16)
      : undefined

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
            <p className="font-semibold leading-snug text-app-fg">{title}</p>
            {(p.league || p.kickoff_display || dateLine) && (
              <p className="mt-0.5 text-[10px] leading-relaxed text-app-muted">
                {[p.league, p.kickoff_display].filter(Boolean).join(' · ')}
                {dateLine && (
                  <>
                    {(p.league || p.kickoff_display) && ' · '}
                    <span className="font-mono tabular-nums">{dateLine}</span>
                    {timeLine && (
                      <span className="font-mono tabular-nums">
                        {' '}
                        {timeLine} UTC
                      </span>
                    )}
                  </>
                )}
              </p>
            )}
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
          Pick
        </p>
        <p className="mt-0.5">
          <span className="text-app-muted">Mercado:</span>{' '}
          <span className="font-medium text-app-fg">{p.market}</span>
        </p>
        <p className="mt-0.5">
          <span className="text-app-muted">Selección:</span>{' '}
          <span className="font-medium text-app-fg">{selShow}</span>
        </p>
        {p.picked_value != null && (
          <p className="mt-0.5 font-mono tabular-nums">
            <span className="text-app-muted">Cuota:</span>{' '}
            <span className="text-app-fg">{p.picked_value}</span>
          </p>
        )}
        {(edge != null || conf) && (
          <p className={`mt-1 ${DIV} pt-1 text-app-muted`}>
            {edge != null && (
              <span className="font-mono tabular-nums">Edge {edge}%</span>
            )}
            {edge != null && conf && ' · '}
            {conf && <span>Conf. {conf}</span>}
          </p>
        )}
        {razon && (
          <p className={`mt-2 leading-relaxed text-app-fg ${DIV} pt-2`}>
            <span className="text-app-muted">Nota:</span> {razon}
          </p>
        )}
      </div>

      <OutcomeFeedbackBlock p={p} />

      {trackingSlot != null && (
        <div className={`${DIV} bg-neutral-50/70 px-3 py-3`}>
          <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-app-muted">
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
                  ? 'rounded bg-neutral-900 px-1.5 py-0.5 font-medium text-white'
                  : p.user_taken === false
                    ? 'rounded bg-neutral-100 px-1.5 py-0.5 text-app-muted'
                    : 'text-app-muted'
              }
            >
              {p.user_taken === true
                ? 'Tomado'
                : p.user_taken === false
                  ? 'No tomado'
                  : 'Tomado —'}
            </span>
            {p.risk_category && (
              <span className="rounded-full bg-violet-50 px-2 py-0.5 text-violet-800">
                {p.risk_category}
              </span>
            )}
            {p.decision_origin && (
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-900">
                {p.decision_origin}
              </span>
            )}
            {p.stake_amount != null && (
              <span className="font-mono tabular-nums text-app-muted">
                Stake {p.stake_amount}
              </span>
            )}
          </div>
        )}
        <Link
          to={href}
          className="mt-2 inline-block text-[11px] font-medium text-app-fg underline decoration-app-line underline-offset-2"
        >
          Ver ficha →
        </Link>
      </div>
    </article>
  )
}
