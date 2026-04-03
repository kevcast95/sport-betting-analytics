import type { ReactNode } from 'react'

/** “?” en círculo: marca ayuda sin gritar. */
export function HelpCueIcon({ className = '' }: { className?: string }) {
  return (
    <span
      className={[
        'flex size-4 shrink-0 items-center justify-center rounded-full border border-violet-300/80 bg-white/90 text-[9px] font-bold leading-none text-violet-700',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      aria-hidden
    >
      ?
    </span>
  )
}

/** Texto de ayuda dentro de cards: colapsado por defecto */
export function CardExplain({
  summary,
  children,
  className = '',
}: {
  summary: string
  children: ReactNode
  className?: string
}) {
  return (
    <details
      className={[
        'group mt-2 rounded-md border border-violet-200/50 bg-violet-50/35 [&_summary::-webkit-details-marker]:hidden',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <summary className="flex cursor-pointer list-none items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium text-violet-900 [list-style:none] [&::-webkit-details-marker]:hidden">
        <HelpCueIcon />
        <span>{summary}</span>
      </summary>
      <div className="border-t border-violet-100/80 px-2.5 py-2 text-[11px] leading-relaxed text-app-muted">
        {children}
      </div>
    </details>
  )
}
