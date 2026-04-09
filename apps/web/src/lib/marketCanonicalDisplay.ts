import { getMarketLabelEs } from '@/lib/marketLabels'

/** US-FE-054 — prioriza etiqueta canónica ES del API; fallback legible; sin inventar mapas locales. */
export function displayMarketLabelEs(input: {
  marketCanonicalLabelEs?: string | null
  marketLabelEs?: string | null
  marketClass?: string | null
  marketCanonical?: string | null
}): string {
  const canon = input.marketCanonicalLabelEs?.trim()
  if (canon) return canon
  const legacy = input.marketLabelEs?.trim()
  if (legacy) return legacy
  const mc = input.marketClass?.trim()
  if (mc) return getMarketLabelEs(mc)
  const code = input.marketCanonical?.trim()
  if (code) return code
  return '—'
}
