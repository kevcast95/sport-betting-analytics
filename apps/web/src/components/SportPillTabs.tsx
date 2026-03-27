import {
  type DashboardSport,
  useDashboardUrlState,
} from '@/hooks/useDashboardUrlState'

const OPTIONS: { id: DashboardSport; label: string }[] = [
  { id: 'football', label: 'Fútbol' },
  { id: 'tennis', label: 'Tenis' },
]

type SportPillTabsProps = {
  className?: string
}

export function SportPillTabs({ className = '' }: SportPillTabsProps) {
  const { sport, setSport } = useDashboardUrlState()

  return (
    <div
      className={[
        'flex flex-wrap gap-1 rounded-lg border border-app-line bg-app-card/90 p-1',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      role="tablist"
      aria-label="Deporte"
    >
      {OPTIONS.map((o) => {
        const active = sport === o.id
        return (
          <button
            key={o.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={[
              'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              active
                ? 'bg-violet-100 font-semibold text-violet-950 shadow-sm'
                : 'text-app-muted hover:bg-violet-50/60 hover:text-app-fg',
            ].join(' ')}
            onClick={() => setSport(o.id)}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
