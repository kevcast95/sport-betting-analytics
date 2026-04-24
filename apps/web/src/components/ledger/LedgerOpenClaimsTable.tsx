import type { CSSProperties } from 'react'
import { displayMarketLabelEs } from '@/lib/marketCanonicalDisplay'
import type { OpenPickSelfRow } from '@/store/useTradeStore'
import { UserResultClaimMenu } from '@/components/ledger/UserResultClaimMenu'

function formatOpened(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}.${m}.${day}`
}

export function LedgerOpenClaimsTable(props: {
  rows: OpenPickSelfRow[]
  monoStyle: CSSProperties
  onRefreshClaims: () => void | Promise<void>
  /** Título del bloque (distinto si son solo picks de bóveda vs huérfanos). */
  title?: string
  subtitle?: string
  /** Borde más neutro para filas secundarias. */
  variant?: 'default' | 'muted'
  /** Anidado bajo details (acordeón): evita doble margen inferior. */
  noSectionMargin?: boolean
}) {
  if (props.rows.length === 0) return null

  const title =
    props.title ?? 'Sin liquidación formal en protocolo'
  const subtitle =
    props.subtitle ??
    'Marcá tu criterio operativo (fuente propia u otra web). Esto guarda solo una etiqueta en servidor; no liquida el pick ni mueve bankroll ni DP. Para impacto económico tenés que usar la pantalla Liquidación (/v2/settlement) con el marcador correcto.'
  const border =
    props.variant === 'muted'
      ? 'border-[#a4b4be]/25 bg-[#f6fafe]'
      : 'border-amber-200/60 bg-amber-50/40'

  return (
    <section
      className={`${props.noSectionMargin ? 'mb-0' : 'mb-10'} overflow-hidden rounded-xl border ${border}`}
    >
      <div
        className={`border-b px-6 py-4 ${props.variant === 'muted' ? 'border-[#a4b4be]/20 bg-[#eef4fa]/80' : 'border-amber-200/50 bg-amber-100/40'}`}
      >
        <p
          className={`text-xs font-bold uppercase tracking-wider ${props.variant === 'muted' ? 'text-[#52616a]' : 'text-[#92400e]'}`}
        >
          {title}
        </p>
        <p
          className={`mt-1 text-sm ${props.variant === 'muted' ? 'text-[#52616a]' : 'text-[#78350f]'}`}
        >
          {subtitle}
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-left">
          <thead>
            <tr className="bg-white/80 text-left">
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Registro
              </th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Evento
              </th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Tu criterio
              </th>
            </tr>
          </thead>
          <tbody
            className={`divide-y ${props.variant === 'muted' ? 'divide-[#e5eff7]' : 'divide-amber-200/40'}`}
          >
            {props.rows.map((row) => {
              const mh = displayMarketLabelEs({
                marketCanonicalLabelEs: row.marketCanonicalLabelEs,
                marketClass: row.marketClass,
              })
              return (
                <tr key={`open-${row.bt2PickId}`} className="bg-white/90">
                  <td
                    className="px-6 py-4 font-mono text-sm text-[#26343d]"
                    style={props.monoStyle}
                  >
                    {formatOpened(row.openedAt)}
                    <span className="ml-2 font-mono text-[10px] text-[#6e7d86]">
                      #{row.bt2PickId}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm font-semibold text-[#26343d]">{row.eventLabel}</p>
                    <p className="mt-0.5 text-xs text-[#6d3bd7]">
                      {mh} · {row.selectionSummaryEs}
                    </p>
                  </td>
                  <td className="px-6 py-4">
                    <UserResultClaimMenu
                      bt2PickId={row.bt2PickId}
                      claim={row.userResultClaim}
                      onDone={props.onRefreshClaims}
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
