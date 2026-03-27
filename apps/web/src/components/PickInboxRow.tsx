import { Link } from 'react-router-dom'
import { kickoffReadableCol } from '@/lib/formatDateTime'
import { selectionShortLabel } from '@/lib/marketCopy'
import { sofascoreEventUrl } from '@/lib/sofascoreUrls'
import {
  confidenceTierFromLabel,
  type ConfidenceTier,
} from '@/lib/stakeSuggestion'

function confTierBadgeClass(tier: ConfidenceTier) {
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

function outcomePill(outcome: 'win' | 'loss' | 'pending' | null | undefined) {
  if (outcome === 'win')
    return (
      <span className="rounded-full border border-emerald-200 bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-900">
        Ganada
      </span>
    )
  if (outcome === 'loss')
    return (
      <span className="rounded-full border border-red-200 bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-900">
        Perdida
      </span>
    )
  return (
    <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
      Pendiente
    </span>
  )
}

export type PickInboxRowProps = {
  pickId: number
  /** Para abrir el partido en SofaScore en otra pestaña. */
  eventId?: number | null
  href: string
  eventLabel?: string | null
  league?: string | null
  market: string
  selection: string
  selectionDisplay?: string | null
  pickedValue?: number | null
  kickoffDisplay?: string | null
  executionSlotLabelEs?: string | null
  confidence?: string | null
  /** Resultado ya efectivo (usuario > sistema), como en el dashboard. */
  outcome?: 'win' | 'loss' | 'pending' | null
  userTaken?: boolean | null
  ordinal?: number
  /** Cierre rápido sin entrar a la ficha (solo si hay usuario). */
  onQuickOutcome?: (o: 'win' | 'loss' | 'pending') => void
  quickOutcomePending?: boolean
  /** Volver a automático (usa pick_results del sistema). */
  onQuickAutoOutcome?: () => void
  quickAutoOutcomePending?: boolean
}

export function PickInboxRow({
  pickId,
  eventId,
  href,
  eventLabel,
  league,
  market,
  selection,
  selectionDisplay,
  pickedValue,
  kickoffDisplay,
  executionSlotLabelEs,
  confidence,
  outcome,
  userTaken,
  ordinal,
  onQuickOutcome,
  quickOutcomePending,
  onQuickAutoOutcome,
  quickAutoOutcomePending,
}: PickInboxRowProps) {
  const sel =
    selectionDisplay?.trim() ||
    selectionShortLabel(market, selection)
  const title = eventLabel?.trim() || `Pick ${pickId}`
  const kickoffCol = kickoffReadableCol(kickoffDisplay ?? null)
  const tier = confidenceTierFromLabel(confidence ?? null)
  const showQuick = Boolean(onQuickOutcome)

  const ssUrl =
    eventId != null && Number.isFinite(eventId)
      ? sofascoreEventUrl(Number(eventId))
      : null

  return (
    <div className="flex border-b border-app-line/90 last:border-b-0">
      <Link
        to={href}
        className="min-w-0 flex-1 transition-colors hover:bg-violet-50/50 focus-visible:bg-violet-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-300"
      >
        <div className="flex items-start gap-3 px-3 py-2.5 sm:px-4 sm:py-3">
          {ordinal != null && (
            <span className="mt-0.5 w-6 shrink-0 text-right font-mono text-[10px] tabular-nums text-app-muted">
              {ordinal}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-app-fg">{title}</p>
            <p className="mt-0.5 line-clamp-2 text-xs text-app-muted">
              <span className="font-mono text-[10px] text-violet-900">{market}</span>
              <span className="text-app-line"> · </span>
              {sel}
              {pickedValue != null && (
                <>
                  <span className="text-app-line"> · </span>
                  <span className="font-mono tabular-nums">@{pickedValue}</span>
                </>
              )}
            </p>
            {league?.trim() && (
              <p className="mt-1 truncate text-[10px] text-app-muted">{league}</p>
            )}
            {(kickoffCol || confidence) && (
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {kickoffCol && (
                  <span
                    className="cursor-help font-mono text-[10px] tabular-nums text-app-muted underline decoration-dotted decoration-app-line/60 underline-offset-2"
                    title="Horario según SofaScore en el momento de la ingesta del run. Si el torneo reprogramó después, puede no coincidir con la web actual hasta volver a capturar el día o refrescar el evento."
                  >
                    ⏰ {kickoffCol}
                  </span>
                )}
                {confidence && confidence.trim().length > 0 && (
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${confTierBadgeClass(
                      tier,
                    )}`}
                  >
                    {`Confianza: ${confidence.trim()}`}
                  </span>
                )}
                {executionSlotLabelEs && executionSlotLabelEs.trim().length > 0 && (
                  <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-900">
                    Banda: {executionSlotLabelEs}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1 pr-1 sm:pr-2">
            {outcomePill(outcome)}
            {userTaken === true && (
              <span className="text-[10px] font-medium text-violet-800">Tomado</span>
            )}
          </div>
        </div>
      </Link>
      <div className="flex w-[4.75rem] shrink-0 flex-col justify-center gap-1 border-l border-app-line/80 bg-app-card/30 px-2 py-2 sm:w-[5.25rem]">
        <Link
          to={href}
          className="text-center text-[10px] font-medium text-app-muted underline decoration-app-line underline-offset-2 hover:text-app-fg"
        >
          Ficha →
        </Link>
        {ssUrl ? (
          <a
            href={ssUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-center text-[10px] font-medium text-sky-800 underline decoration-sky-200 underline-offset-2 hover:text-sky-950"
            title="Abrir partido en SofaScore (validar marcador / horario)"
          >
            SofaScore ↗
          </a>
        ) : null}
      </div>
      {showQuick && (
        <div
          className="flex w-[5.5rem] shrink-0 flex-col justify-center gap-1 border-l border-app-line/80 bg-app-card/50 px-1.5 py-2 sm:w-auto sm:flex-row sm:items-center sm:gap-0.5 sm:px-2"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="mb-0.5 text-center text-[8px] font-medium uppercase tracking-wide text-app-muted sm:hidden">
            Cierre
          </p>
          {onQuickAutoOutcome ? (
            <button
              type="button"
              title="Volver a automático (usar el resultado del sistema)"
              disabled={quickAutoOutcomePending || userTaken !== true}
              onClick={(e) => {
                e.preventDefault()
                onQuickAutoOutcome()
              }}
              className={[
                'rounded border px-1.5 py-1 text-[10px] font-semibold tabular-nums transition-colors sm:min-w-[1.75rem]',
                userTaken === true
                  ? quickAutoOutcomePending
                    ? 'border-app-line bg-white text-app-muted opacity-40'
                    : 'border-violet-300 bg-violet-100 text-violet-950'
                  : 'border-app-line bg-white text-app-muted opacity-40',
              ].join(' ')}
            >
              <span className="sm:hidden">Auto</span>
              <span className="hidden sm:inline">Auto</span>
            </button>
          ) : null}
          {(['win', 'loss', 'pending'] as const).map((o) => {
            const label = o === 'win' ? 'G' : o === 'loss' ? 'P' : '…'
            const titleBtn =
              o === 'win' ? 'Marcar ganada' : o === 'loss' ? 'Marcar perdida' : 'Marcar pendiente'
            const effective = outcome ?? 'pending'
            const active = effective === o
            return (
              <button
                key={o}
                type="button"
                title={titleBtn}
                disabled={quickOutcomePending}
                onClick={(e) => {
                  e.preventDefault()
                  onQuickOutcome!(o)
                }}
                className={[
                  'rounded border px-1.5 py-1 text-[10px] font-semibold tabular-nums transition-colors sm:min-w-[1.75rem]',
                  active
                    ? 'border-violet-400 bg-violet-100 text-violet-950'
                    : 'border-app-line bg-white text-app-muted hover:border-violet-200 hover:text-app-fg',
                  quickOutcomePending ? 'opacity-40' : '',
                ].join(' ')}
              >
                <span className="sm:hidden">
                  {o === 'win' ? 'Gané' : o === 'loss' ? 'Perdí' : 'Pend.'}
                </span>
                <span className="hidden sm:inline">{label}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
