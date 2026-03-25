import { Link } from 'react-router-dom'
import { selectionShortLabel } from '@/lib/marketCopy'

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
  href: string
  eventLabel?: string | null
  league?: string | null
  market: string
  selection: string
  selectionDisplay?: string | null
  pickedValue?: number | null
  /** Resultado ya efectivo (usuario > sistema), como en el dashboard. */
  outcome?: 'win' | 'loss' | 'pending' | null
  userTaken?: boolean | null
  ordinal?: number
}

export function PickInboxRow({
  pickId,
  href,
  eventLabel,
  league,
  market,
  selection,
  selectionDisplay,
  pickedValue,
  outcome,
  userTaken,
  ordinal,
}: PickInboxRowProps) {
  const sel =
    selectionDisplay?.trim() ||
    selectionShortLabel(market, selection)
  const title = eventLabel?.trim() || `Pick ${pickId}`

  return (
    <Link
      to={href}
      className="block border-b border-app-line/90 transition-colors last:border-b-0 hover:bg-violet-50/50 focus-visible:bg-violet-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-300"
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
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {outcomePill(outcome)}
          {userTaken === true && (
            <span className="text-[10px] font-medium text-violet-800">Tomado</span>
          )}
          <span className="text-[10px] text-app-muted">Ficha →</span>
        </div>
      </div>
    </Link>
  )
}
