import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { ListPagination } from '@/components/ListPagination'
import { useParams } from 'react-router-dom'
import { SportHiddenInUiMessage } from '@/components/SportHiddenInUiMessage'
import { ViewContextBar } from '@/components/ViewContextBar'
import { useUiSportsVisibility } from '@/contexts/UiSportsVisibilityContext'
import { fetchJson } from '@/lib/api'
import { useListPageSize } from '@/hooks/useListPageSize'
import type { DailyRunEventsInspectOut } from '@/types/api'

function pretty(v: unknown): string {
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

export default function RunEventsPage() {
  const { isRunSportVisible } = useUiSportsVisibility()
  const { dailyRunId } = useParams()
  const runId = Number(dailyRunId)
  const [eventQuery, setEventQuery] = useState('')
  const [pickQuery, setPickQuery] = useState('')
  const [eventListPage, setEventListPage] = useState(0)
  const { pageSize: eventPageSize, setPageSize: setEventPageSize } =
    useListPageSize()

  useEffect(() => {
    setEventListPage(0)
  }, [eventQuery, pickQuery, eventPageSize])

  const q = useQuery({
    queryKey: ['run-events', runId],
    enabled: Number.isFinite(runId) && runId > 0,
    queryFn: () =>
      fetchJson<DailyRunEventsInspectOut>(`/daily-runs/${runId}/events?limit=1000`),
  })

  const filteredItems = useMemo(() => {
    const items = q.data?.items ?? []
    const eq = eventQuery.trim().toLowerCase()
    const pq = pickQuery.trim().toLowerCase()
    return items.filter((e) => {
      const eventText = [
        String(e.event_id),
        e.event_label ?? '',
        e.league ?? '',
        e.model_skip_reason ?? '',
        e.pipeline_skip_summary ?? '',
      ]
        .join(' ')
        .toLowerCase()
      if (eq && !eventText.includes(eq)) return false
      if (!pq) return true
      if (!e.in_ds_input) return false
      return eventText.includes(pq)
    })
  }, [q.data?.items, eventQuery, pickQuery])

  const eventTotal = filteredItems.length

  useEffect(() => {
    const maxP =
      eventTotal <= 0 ? 0 : Math.max(0, Math.ceil(eventTotal / eventPageSize) - 1)
    if (eventListPage > maxP) setEventListPage(maxP)
  }, [eventTotal, eventPageSize, eventListPage])

  const eventPageSafe =
    eventTotal <= 0
      ? 0
      : Math.min(
          eventListPage,
          Math.max(0, Math.ceil(eventTotal / eventPageSize) - 1),
        )
  const eventsPageSlice = useMemo(() => {
    const start = eventPageSafe * eventPageSize
    return filteredItems.slice(start, start + eventPageSize)
  }, [filteredItems, eventPageSafe, eventPageSize])

  if (
    q.isSuccess &&
    q.data?.sport != null &&
    String(q.data.sport).trim() !== '' &&
    !isRunSportVisible(String(q.data.sport))
  ) {
    return (
      <div>
        <ViewContextBar
          crumbs={[
            { label: 'Inicio', to: '/' },
            {
              label: `Ejecución ${q.data.run_date}`,
              to: `/runs/${runId}/picks`,
            },
            { label: 'Eventos' },
          ]}
        />
        <div className="mt-4">
          <SportHiddenInUiMessage sportLabel={String(q.data.sport)} />
        </div>
      </div>
    )
  }

  return (
    <div>
      {q.data ? (
        <ViewContextBar
          crumbs={[
            { label: 'Inicio', to: '/' },
            {
              label: `Ejecución ${q.data.run_date}`,
              to: `/runs/${runId}/picks`,
            },
            { label: 'Eventos' },
          ]}
        />
      ) : null}
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
          <div className="mb-3 grid gap-2 sm:grid-cols-2">
            <label className="text-xs text-app-muted">
              Buscar evento
              <input
                type="text"
                value={eventQuery}
                onChange={(e) => setEventQuery(e.target.value)}
                placeholder="event_id, jugador, torneo..."
                className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-1.5 text-xs text-app-fg shadow-sm"
              />
            </label>
            <label className="text-xs text-app-muted">
              Buscar en eventos con pick
              <input
                type="text"
                value={pickQuery}
                onChange={(e) => setPickQuery(e.target.value)}
                placeholder="filtra solo en picks (evento/torneo)"
                className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-1.5 text-xs text-app-fg shadow-sm"
              />
            </label>
          </div>
          <p className="mb-2 text-xs text-app-muted">
            <span className="font-mono text-app-fg">{q.data.total_events}</span> eventos en
            este run · tras filtros:{' '}
            <span className="font-mono text-app-fg">{filteredItems.length}</span>.
          </p>
          <ListPagination
            className="mb-4"
            idPrefix="run-events"
            page={eventPageSafe}
            pageSize={eventPageSize}
            total={eventTotal}
            onPageChange={setEventListPage}
            onPageSizeChange={setEventPageSize}
          />

          <div className="space-y-3">
            {eventsPageSlice.map((e) => (
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
                  <span className="text-app-muted" title="Hay al menos un pick guardado en SQLite para este run">
                    pick en DB: {e.in_ds_input ? 'sí' : 'no'}
                  </span>
                </div>

                {(e.model_skip_reason || e.pipeline_skip_summary) && (
                  <div className="mt-2 space-y-1 rounded border border-app-line bg-neutral-950/40 p-2 text-xs text-app-fg">
                    {e.model_skip_reason ? (
                      <p>
                        <span className="font-mono text-app-muted">Modelo: </span>
                        {e.model_skip_reason}
                      </p>
                    ) : null}
                    {e.pipeline_skip_summary ? (
                      <p>
                        <span className="font-mono text-app-muted">Pipeline: </span>
                        {e.pipeline_skip_summary}
                      </p>
                    ) : null}
                  </div>
                )}

                {!e.model_skip_reason &&
                  !e.pipeline_skip_summary &&
                  !e.in_ds_input && (
                    <p className="mt-2 text-xs text-app-muted">
                      Sin feedback del modelo: este evento no tiene fila persistida de análisis LLM.
                      La lista muestra todos los partidos con features en el run; solo los que entraron
                      en <span className="font-mono">ds_input</span> de la ventana y se mergearon en{' '}
                      <span className="font-mono">telegram_payload</span> al ejecutar{' '}
                      <span className="font-mono">persist_picks</span> guardan motivo aquí.
                    </p>
                  )}

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

