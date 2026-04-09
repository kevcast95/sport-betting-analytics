/**
 * Sprint 05.2 / US-FE-050 — switcher Mezcla | Mañana | Tarde | Noche (filtro cliente, sin nuevo GET).
 */
import type { VaultBandTab } from '@/lib/vaultTimeBand'
import { VAULT_BAND_TABS, VAULT_BAND_TAB_LABELS_ES } from '@/lib/vaultTimeBand'

export type VaultBandSwitcherProps = {
  value: VaultBandTab
  onChange: (tab: VaultBandTab) => void
  disabled?: boolean
}

export function VaultBandSwitcher({
  value,
  onChange,
  disabled,
}: VaultBandSwitcherProps) {
  return (
    <div
      role="tablist"
      aria-label="Franja horaria de la bóveda"
      className="flex flex-wrap gap-1 rounded-xl border border-[#a4b4be]/25 bg-[#eef4fa]/60 p-1"
    >
      {VAULT_BAND_TABS.map((tab) => {
        const selected = value === tab
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={selected}
            disabled={disabled}
            onClick={() => onChange(tab)}
            className={`rounded-lg px-3 py-2 text-[11px] font-bold uppercase tracking-wide transition-colors ${
              selected
                ? 'bg-white text-[#8B5CF6] shadow-sm'
                : 'text-[#52616a] hover:bg-white/70'
            } disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {VAULT_BAND_TAB_LABELS_ES[tab]}
          </button>
        )
      })}
    </div>
  )
}
