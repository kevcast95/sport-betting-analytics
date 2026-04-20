import type { CSSProperties, ReactNode } from 'react'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { UserResultClaimMenu } from '@/components/ledger/UserResultClaimMenu'
import { displayMarketLabelEs } from '@/lib/marketCanonicalDisplay'
import type { LedgerRow } from '@/store/useTradeStore'

function formatLedgerDate(iso: string): string {
  const d = new Date(iso)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}.${m}.${day}`
}

function roiRowPct(row: LedgerRow): number {
  if (row.stakeCop <= 0) return 0
  return (row.pnlCop / row.stakeCop) * 100
}

function protocolPillClass(marketClass: string): string {
  const m = marketClass || 'CDM'
  if (m.includes('ML') || m.includes('TOTAL'))
    return 'bg-[#e9ddff] text-[#6029c9]'
  if (m.includes('SPREAD') || m.includes('PLAYER'))
    return 'bg-[#d5e5ef] text-[#435368]'
  return 'bg-[#d3e4fe] text-[#314055]'
}

function outcomeDisplay(row: LedgerRow): { text: string; className: string } {
  const roi = roiRowPct(row)
  if (row.outcome === 'PROFIT') {
    return {
      text: `+${roi.toFixed(1)}% ROI`,
      className: 'font-mono font-bold text-[#6d3bd7]',
    }
  }
  if (row.outcome === 'PUSH') {
    return {
      text: `${roi.toFixed(1)}% PUSH`,
      className: 'font-mono font-bold text-[#52616a]',
    }
  }
  return {
    text: `${roi.toFixed(1)}% RECAP`,
    className: 'font-mono font-bold text-[#914d00]',
  }
}

function canReopenLiquidation(protocolStatus: string | undefined): boolean {
  return protocolStatus === 'won' || protocolStatus === 'lost' || protocolStatus === 'void'
}

export function LedgerTable(props: {
  rows: LedgerRow[]
  monoStyle: CSSProperties
  onViewDetails: (row: LedgerRow) => void
  onRefreshClaims?: () => void | Promise<void>
  /** Revierte settle en servidor; solo si `protocolPickStatus` es won/lost/void. */
  onReopenSettlement?: (bt2PickId: number) => void | Promise<void>
  pagination?: ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-white">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] border-collapse text-left">
          <thead>
            <tr className="bg-[#eef4fa] text-left">
              <th
                className="px-6 py-4 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]"
              >
                Fecha
              </th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Clase de mercado
              </th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Outcome
              </th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Tu criterio
              </th>
              <th className="px-6 py-4 text-center text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Discipline Points
              </th>
              <th className="px-6 py-4 text-right text-[10px] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                Acción
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#e5eff7]">
            {props.rows.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-16 text-center text-sm text-[#52616a]"
                >
                  No hay registros para este filtro.
                </td>
              </tr>
            ) : (
              props.rows.map((row) => {
                const mc = row.marketClass ?? 'CDM'
                const marketHuman = displayMarketLabelEs({
                  marketCanonicalLabelEs: row.marketCanonicalLabelEs,
                  marketClass: row.marketClass,
                })
                const od = outcomeDisplay(row)
                const dp = row.earnedDp ?? 0
                return (
                  <tr
                    key={`${row.pickId}-${row.settledAt}`}
                    className="group transition-colors hover:bg-[#f6fafe]"
                  >
                    <td
                      className="px-6 py-6 font-mono text-sm font-medium text-[#26343d]"
                      style={props.monoStyle}
                    >
                      {formatLedgerDate(row.settledAt)}
                    </td>
                    <td className="px-6 py-6">
                      <span
                        className={`inline-block rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${protocolPillClass(mc)}`}
                        title={mc}
                      >
                        {marketHuman}
                      </span>
                      <p className="mt-1 line-clamp-1 text-xs text-[#52616a]">
                        {row.titulo ?? row.pickId}
                      </p>
                    </td>
                    <td className="px-6 py-6">
                      <span className={od.className} style={props.monoStyle}>
                        {od.text}
                      </span>
                    </td>
                    <td className="px-6 py-6 align-top">
                      {row.bt2PickId != null && props.onRefreshClaims ? (
                        <UserResultClaimMenu
                          bt2PickId={row.bt2PickId}
                          claim={row.userResultClaim ?? null}
                          onDone={props.onRefreshClaims}
                        />
                      ) : (
                        <span className="text-[11px] text-[#a4b4be]">—</span>
                      )}
                    </td>
                    <td className="px-6 py-6 text-center">
                      <div className="inline-flex items-center gap-2 rounded-full border border-[#6d3bd7]/10 bg-[#d5e5ef]/30 px-3 py-1">
                        <Bt2ShieldCheckIcon className="h-4 w-4 shrink-0 text-[#6d3bd7]" />
                        <span
                          className="font-mono text-sm font-semibold text-[#26343d]"
                          style={props.monoStyle}
                        >
                          +{dp}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-6 text-right align-top">
                      <div className="flex flex-col items-end gap-2">
                        <button
                          type="button"
                          className="text-xs font-bold uppercase tracking-wider text-[#6d3bd7] underline-offset-4 hover:underline"
                          onClick={() => props.onViewDetails(row)}
                        >
                          Ver detalle
                        </button>
                        {row.bt2PickId != null &&
                        props.onReopenSettlement &&
                        canReopenLiquidation(row.protocolPickStatus) ? (
                          <button
                            type="button"
                            className="max-w-[11rem] text-[10px] font-semibold uppercase tracking-wide text-[#914d00] underline decoration-orange-300/70 underline-offset-4 hover:text-[#7c3f00]"
                            title="Revierte liquidación formal (bankroll + DP); el pick vuelve abierto para liquidar de nuevo."
                            onClick={() => void props.onReopenSettlement!(row.bt2PickId!)}
                          >
                            Reabrir liquidación
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      {props.pagination != null ? (
        <div className="flex items-center justify-between border-t border-[#a4b4be]/10 bg-[#eef4fa] px-6 py-4">
          {props.pagination}
        </div>
      ) : null}
    </section>
  )
}
