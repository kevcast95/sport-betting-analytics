import { Link } from 'react-router-dom'

export type Crumb = { label: string; to?: string }

/**
 * Migas ligeras para no perder contexto al venir del dashboard o entre run / ficha.
 */
export function ViewContextBar({
  crumbs,
}: {
  crumbs: Crumb[]
}) {
  if (crumbs.length === 0) return null
  return (
    <nav
      className="mb-4 flex flex-wrap items-center gap-x-1 gap-y-0.5 text-[11px] text-app-muted"
      aria-label="Ubicación"
    >
      {crumbs.map((c, i) => (
        <span key={`${c.label}-${i}`} className="inline-flex items-center gap-1">
          {i > 0 && <span className="text-app-line" aria-hidden>/</span>}
          {c.to ? (
            <Link
              to={c.to}
              className="text-violet-800 underline decoration-violet-200/80 underline-offset-2 hover:text-violet-950"
            >
              {c.label}
            </Link>
          ) : (
            <span className="font-medium text-app-fg">{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
