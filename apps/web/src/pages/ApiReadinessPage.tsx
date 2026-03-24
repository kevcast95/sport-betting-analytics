import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'
import type { DailyRunPage, DashboardBundleOut } from '@/types/api'

type Row = {
  runDate: string
  events: number
  rejected: number
  picks: number
  settled: number
  wins: number
}

function pct(n: number | null): string {
  if (n == null || Number.isNaN(n)) return '—'
  return `${(n * 100).toFixed(1)}%`
}

function semaforoLabel(score: number): {
  label: string
  tone: string
} {
  if (score >= 70) return { label: 'Listo para probar API paga', tone: 'text-emerald-700' }
  if (score >= 45) return { label: 'Zona intermedia (seguir validando)', tone: 'text-amber-700' }
  return { label: 'Aún temprano para pagar API', tone: 'text-neutral-700' }
}

export default function ApiReadinessPage() {
  const runsQ = useQuery({
    queryKey: ['api-readiness-runs'],
    queryFn: async () =>
      fetchJson<DailyRunPage>('/daily-runs?limit=30'),
  })

  const rowsQ = useQuery({
    queryKey: ['api-readiness-dashboard-rows', runsQ.data?.items?.map((x) => x.run_date).join(',')],
    enabled: (runsQ.data?.items?.length ?? 0) > 0,
    queryFn: async () => {
      const runDates = Array.from(
        new Set((runsQ.data?.items ?? []).map((x) => x.run_date)),
      )
      const bundles = await Promise.all(
        runDates.map((d) => fetchJson<DashboardBundleOut>(`/dashboard?run_date=${d}`)),
      )
      const out: Row[] = bundles.map((b) => {
        const s = b.summary
        const settled = s.outcome_wins + s.outcome_losses
        return {
          runDate: s.run_date,
          events: s.events_total ?? 0,
          rejected: s.selection_rejected ?? 0,
          picks: s.picks_total ?? 0,
          settled,
          wins: s.outcome_wins ?? 0,
        }
      })
      out.sort((a, b) => (a.runDate < b.runDate ? 1 : -1))
      return out
    },
  })

  const kpis = useMemo(() => {
    const rows = rowsQ.data ?? []
    if (!rows.length) {
      return {
        n: 0,
        events: 0,
        rejectedRate: null as number | null,
        picksPerDay: null as number | null,
        hitRate: null as number | null,
        score: 0,
      }
    }
    const n = rows.length
    const totalEvents = rows.reduce((a, r) => a + r.events, 0)
    const totalRejected = rows.reduce((a, r) => a + r.rejected, 0)
    const totalPicks = rows.reduce((a, r) => a + r.picks, 0)
    const totalSettled = rows.reduce((a, r) => a + r.settled, 0)
    const totalWins = rows.reduce((a, r) => a + r.wins, 0)

    const rejectedRate = totalEvents > 0 ? totalRejected / totalEvents : null
    const picksPerDay = totalPicks / n
    const hitRate = totalSettled > 0 ? totalWins / totalSettled : null

    // Score simple 0..100: +descartes altos, +baja producción de picks.
    const sr = rejectedRate == null ? 0 : Math.min(1, rejectedRate)
    const sp = Math.max(0, Math.min(1, (3 - picksPerDay) / 3))
    const sh = hitRate == null ? 0.5 : Math.max(0, Math.min(1, 0.6 - hitRate))
    const score = Math.round((sr * 0.5 + sp * 0.35 + sh * 0.15) * 100)

    return { n, events: totalEvents, rejectedRate, picksPerDay, hitRate, score }
  }, [rowsQ.data])

  const sem = semaforoLabel(kpis.score)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-app-fg md:text-3xl">
          API Readiness
        </h1>
        <p className="mt-1 text-sm text-app-muted">
          Decisión técnica para pasar de freemium a proveedor pago, con datos reales de operación.
        </p>
      </div>

      {(runsQ.isLoading || rowsQ.isLoading) && (
        <p className="text-sm text-app-muted">Cargando métricas…</p>
      )}

      {(runsQ.isError || rowsQ.isError) && (
        <p className="text-sm text-app-danger">
          Error cargando métricas de readiness.
        </p>
      )}

      {!runsQ.isLoading && !rowsQ.isLoading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-app-line bg-app-card p-4">
              <p className="text-xs text-app-muted">Ventana analizada</p>
              <p className="mt-2 font-mono text-xl tabular-nums">{kpis.n} días</p>
            </div>
            <div className="rounded-xl border border-app-line bg-app-card p-4">
              <p className="text-xs text-app-muted">Tasa descarte por data/filtros</p>
              <p className="mt-2 font-mono text-xl tabular-nums">{pct(kpis.rejectedRate)}</p>
            </div>
            <div className="rounded-xl border border-app-line bg-app-card p-4">
              <p className="text-xs text-app-muted">Picks por día</p>
              <p className="mt-2 font-mono text-xl tabular-nums">
                {kpis.picksPerDay == null ? '—' : kpis.picksPerDay.toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl border border-app-line bg-app-card p-4">
              <p className="text-xs text-app-muted">Hit-rate (settled)</p>
              <p className="mt-2 font-mono text-xl tabular-nums">{pct(kpis.hitRate)}</p>
            </div>
          </div>

          <div className="rounded-xl border border-app-line bg-app-card p-4">
            <p className="text-xs text-app-muted">Semáforo de compra API</p>
            <p className={`mt-2 text-lg font-semibold ${sem.tone}`}>
              {sem.label}
            </p>
            <p className="mt-1 text-xs text-app-muted">
              Score {kpis.score}/100. Regla actual: descartes altos + pocos picks diarios incrementan prioridad de proveedor pago.
            </p>
            <ul className="mt-3 space-y-1 text-xs text-app-muted">
              <li>• Mantener POC actual esta semana para validar estabilidad/ROI.</li>
              <li>• Si descarte &gt; 50% por 2 semanas, activar prueba freemium de API externa.</li>
            </ul>
          </div>

          <div className="rounded-xl border border-app-line bg-app-card p-4">
            <p className="mb-2 text-xs text-app-muted">Detalle diario (últimos runs)</p>
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="border-b border-app-line text-left text-app-muted">
                    <th className="px-2 py-1">Fecha</th>
                    <th className="px-2 py-1">Eventos</th>
                    <th className="px-2 py-1">Rechazados</th>
                    <th className="px-2 py-1">Picks</th>
                    <th className="px-2 py-1">Hit-rate</th>
                  </tr>
                </thead>
                <tbody>
                  {(rowsQ.data ?? []).map((r) => (
                    <tr key={r.runDate} className="border-b border-app-line/60">
                      <td className="px-2 py-1 font-mono">{r.runDate}</td>
                      <td className="px-2 py-1 font-mono tabular-nums">{r.events}</td>
                      <td className="px-2 py-1 font-mono tabular-nums">{r.rejected}</td>
                      <td className="px-2 py-1 font-mono tabular-nums">{r.picks}</td>
                      <td className="px-2 py-1 font-mono tabular-nums">
                        {pct(r.settled > 0 ? r.wins / r.settled : null)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

