import type { ReactNode } from 'react'

export type BunkerViewHeaderProps = {
  title: string
  subtitle?: string
  onHelpClick?: () => void
  helpButtonLabel?: string
  rightActions?: ReactNode
}

/**
 * Cabecera unificada vistas V2 (Sprint 05.1 / T-174): título, subtítulo opcional,
 * ayuda contextual y acciones a la derecha.
 */
export function BunkerViewHeader({
  title,
  subtitle,
  onHelpClick,
  helpButtonLabel = 'Cómo funciona',
  rightActions,
}: BunkerViewHeaderProps) {
  return (
    <header className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1">
        <h1 className="text-3xl font-bold tracking-tighter text-[#26343d] sm:text-4xl">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 max-w-3xl text-sm text-[#52616a]">{subtitle}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-3">
        {onHelpClick ? (
          <button
            type="button"
            onClick={onHelpClick}
            className="inline-flex items-center gap-2 rounded-lg border border-[#a4b4be]/30 bg-white/70 px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86] transition-colors hover:border-[#8B5CF6]/30 hover:text-[#8B5CF6]"
            aria-label={`${helpButtonLabel} — abrir ayuda contextual`}
          >
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[#a4b4be]/35 bg-[#eef4fa] text-[11px] font-bold text-[#6d3bd7]"
              aria-hidden
            >
              ?
            </span>
            {helpButtonLabel}
          </button>
        ) : null}
        {rightActions}
      </div>
    </header>
  )
}
