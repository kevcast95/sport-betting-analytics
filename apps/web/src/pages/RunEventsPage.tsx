import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { fetchJson } from '@/lib/api'
import type { DailyRunEventsInspectOut } from '@/types/api'

function pretty(v: unknown): string {
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

export default function RunEventsPage() {
  const { dailyRunId } = useParams()
  const runId = Number(dailyRunId)

  const q = useQuery({
    queryKey: ['run-events', runId],
    enabled: Number.isFinite(runId) && runId > 0,
    queryFn: () =>
      fetchJson<DailyRunEventsInspectOut>(`/daily-runs/${runId}/events?limit=1000`),
  })

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold tracking-tight">Eventos del run</h2>
        <p className="mt-1 max-w-xl text-sm text-app-muted">
          Inspector técnico: contexto, diagnósticos y snapshot procesado por
          evento.
        </p>
      </div>

      {q.isLoading && <p className="text-sm text-app-muted">Cargando eventos…</p>}
      {q.isError && <p className="text-sm text-app-danger">{(q.error as Error).message}</p>}

      {q.data && (
        <>
          <p className="mb-4 text-xs text-app-muted">
            <span className="font-mono text-app-fg">{q.data.total_events}</span>{' '}
            eventos en este run.
          </p>

          <div className="space-y-3">
            {q.data.items.map((e) => (
              <div key={e.event_id} className="rounded-lg border border-app-line bg-app-card p-3">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-mono text-app-fg">event_id {e.event_id}</span>
                  <span className="text-app-fg">{e.event_label ?? 'Partido sin título'}</span>
                  <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-neutral-700">
                    {e.league ?? 'Liga n/d'}
                  </span>
                  {e.h2h_summary && (
                    <span className="rounded bg-sky-100 px-1.5 py-0.5 text-sky-800">
                      {e.h2h_summary}
                    </span>
                  )}
                  <span
                    className={`rounded px-1.5 py-0.5 ${
                      e.passed_candidate_filters
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {e.passed_candidate_filters ? 'filtro OK' : `descartado: ${e.reject_reason ?? '—'}`}
                  </span>
                  <span className="rounded bg-violet-100 px-1.5 py-0.5 text-violet-800">
                    tier: {e.selection_tier ?? '—'}
                  </span>
                  <span className="text-app-muted">match_state: {e.match_state ?? '—'}</span>
                  <span className="text-app-muted">en picks: {e.in_ds_input ? 'sí' : 'no'}</span>
                </div>

                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-app-fg">event_context</summary>
                  <pre className="mt-1 max-h-56 overflow-auto rounded bg-neutral-950 p-2 text-[10px] text-neutral-100">
                    {pretty(e.event_context)}
                  </pre>
                </details>

                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-app-fg">diagnostics</summary>
                  <pre className="mt-1 max-h-56 overflow-auto rounded bg-neutral-950 p-2 text-[10px] text-neutral-100">
                    {pretty(e.diagnostics)}
                  </pre>
                </details>

                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-app-fg">processed (snapshot)</summary>
                  <pre className="mt-1 max-h-72 overflow-auto rounded bg-neutral-950 p-2 text-[10px] text-neutral-100">
                    {pretty(e.processed)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

