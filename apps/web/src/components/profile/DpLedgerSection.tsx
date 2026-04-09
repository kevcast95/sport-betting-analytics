/**
 * US-FE-031 (T-126): movimientos DP desde GET /bt2/user/dp-ledger.
 */
import { useCallback, useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { bt2FetchJson } from '@/lib/api'
import type { Bt2DpLedgerOut } from '@/lib/bt2Types'
import { dpLedgerReasonLabelEs } from '@/lib/dpLedgerLabels'

type LoadState = 'idle' | 'loading' | 'error' | 'empty' | 'ready'

function formatDelta(n: number): string {
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n.toLocaleString('es-CO')}`
}

export function DpLedgerSection({ monoStyle }: { monoStyle: CSSProperties }) {
  const [state, setState] = useState<LoadState>('idle')
  const [entries, setEntries] = useState<
    Bt2DpLedgerOut['entries']
  >([])

  const load = useCallback(async () => {
    setState('loading')
    try {
      const data = await bt2FetchJson<Bt2DpLedgerOut>(
        '/bt2/user/dp-ledger?limit=100',
      )
      setEntries(data.entries ?? [])
      setState(data.entries?.length ? 'ready' : 'empty')
    } catch {
      setState('error')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <section
      className="rounded-xl border border-[#a4b4be]/20 bg-white p-8 shadow-sm"
      aria-label="Movimientos de Discipline Points"
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xs font-bold uppercase tracking-widest text-[#52616a]">
          Movimientos DP (servidor)
        </h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg border border-[#a4b4be]/30 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[#6e7d86] hover:border-[#8B5CF6]/40 hover:text-[#6d3bd7]"
        >
          Actualizar
        </button>
      </div>

      {state === 'loading' || state === 'idle' ? (
        <p className="text-sm text-[#52616a]">Cargando movimientos…</p>
      ) : null}

      {state === 'error' ? (
        <p className="text-sm text-[#9b1c1c]">
          No se pudo cargar el historial. Revisa la sesión o inténtalo de nuevo.
        </p>
      ) : null}

      {state === 'empty' ? (
        <p className="text-sm text-[#52616a]">
          Aún no hay movimientos en tu ledger. El saldo puede ser 0 hasta que
          acredites DP (onboarding, liquidaciones, etc.).
        </p>
      ) : null}

      {state === 'ready' ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-[#a4b4be]/20 text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                <th className="pb-2 pr-4">Fecha</th>
                <th className="pb-2 pr-4">Motivo</th>
                <th className="pb-2 pr-4 text-right">Δ DP</th>
                <th className="pb-2 text-right">Saldo tras</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr
                  key={e.id}
                  className="border-b border-[#a4b4be]/10 last:border-0"
                >
                  <td
                    className="py-3 pr-4 font-mono text-xs text-[#52616a]"
                    style={monoStyle}
                  >
                    {new Date(e.created_at).toLocaleString('es-CO', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </td>
                  <td className="py-3 pr-4 text-[#26343d]">
                    {dpLedgerReasonLabelEs(e.reason)}
                  </td>
                  <td
                    className={`py-3 pr-4 text-right font-mono text-sm font-semibold tabular-nums ${
                      e.delta_dp >= 0 ? 'text-[#059669]' : 'text-[#9e3f4e]'
                    }`}
                    style={monoStyle}
                  >
                    {formatDelta(e.delta_dp)}
                  </td>
                  <td
                    className="py-3 text-right font-mono text-sm tabular-nums text-[#26343d]"
                    style={monoStyle}
                  >
                    {e.balance_after_dp.toLocaleString('es-CO')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
