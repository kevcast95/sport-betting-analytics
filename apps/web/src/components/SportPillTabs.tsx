import { useUiSportsVisibility } from '@/contexts/UiSportsVisibilityContext'
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
  const { visible } = useUiSportsVisibility()
  const options = OPTIONS.filter((o) => visible[o.id])

  if (options.length === 0) return null

  return (
    <div
      className={[
        'flex flex-wrap gap-1 rounded-lg border border-violet-200/55 bg-white/90 p-1 shadow-sm',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      role="tablist"
      aria-label="Deporte"
    >
      {options.map((o) => {
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
                ? 'bg-violet-100/90 font-medium text-violet-950 ring-1 ring-violet-300/45 shadow-sm'
                : 'text-app-muted hover:bg-violet-50/70 hover:text-violet-950',
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
