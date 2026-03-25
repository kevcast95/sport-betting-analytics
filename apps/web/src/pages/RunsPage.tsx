import { useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { SportPillTabs } from '@/components/SportPillTabs'
import { fetchJson } from '@/lib/api'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import type { DailyRunPage } from '@/types/api'
import { formatCalendarDateEs } from '@/lib/formatDateTime'

const PAGE = 20

export default function RunsPage() {
  const { sport } = useDashboardUrlState()

  const q = useInfiniteQuery({
    queryKey: ['daily-runs', sport],
    initialPageParam: undefined as number | undefined,
    queryFn: async ({ pageParam }) => {
      const sp = new URLSearchParams({ limit: String(PAGE), sport })
      if (pageParam != null) sp.set('cursor', String(pageParam))
      return fetchJson<DailyRunPage>(`/daily-runs?${sp}`)
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  })

  const rows = q.data?.pages.flatMap((p) => p.items) ?? []

  return (
    <div>
      <SportPillTabs className="mb-4 max-w-md" />
      <h2 className="mb-1 text-xl font-semibold tracking-tight">
        Ejecuciones diarias
      </h2>
      <p className="mb-6 max-w-xl text-sm text-app-muted">
        Cada fila es un run guardado en la base. Desde el{' '}
        <span className="text-app-fg">dashboard</span> puedes saltar directo al
        tablero o al inspector de eventos del día que estés viendo, sin pasar
        obligatoriamente por aquí. Lista paginada por cursor (
        <code className="rounded bg-neutral-100 px-1 font-mono text-xs">
          daily_run_id
        </code>
        ). Filtro opcional:{' '}
        <code className="rounded bg-neutral-100 px-1 font-mono text-xs">
          ?sport=football
        </code>{' '}
        o{' '}
        <code className="rounded bg-neutral-100 px-1 font-mono text-xs">
          ?sport=tennis
        </code>
        .
      </p>

      {q.isError && (
        <p className="text-sm text-app-danger">
          {(q.error as Error).message}
        </p>
      )}

      <div className="overflow-x-auto rounded-xl border border-app-line bg-app-card shadow-sm">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-app-line text-left text-app-muted">
              <th className="p-2 font-normal">ID</th>
              <th className="p-2 font-normal">Fecha</th>
              <th className="p-2 font-normal">Deporte</th>
              <th className="p-2 font-normal">Estado</th>
              <th className="p-2 text-right font-normal">Vistas</th>
            </tr>
          </thead>
          <tbody>
            {q.isLoading && (
              <tr>
                <td colSpan={5} className="p-4 text-app-muted">
                  Cargando…
                </td>
              </tr>
            )}
            {!q.isLoading &&
              rows.map((r) => (
                <tr
                  key={r.daily_run_id}
                  className="border-b border-app-line/80 hover:bg-neutral-50/80"
                >
                  <td className="p-2">{r.daily_run_id}</td>
                  <td className="p-2 text-app-fg">
                    <span className="font-mono text-xs tabular-nums text-violet-900">
                      {r.run_date}
                    </span>
                    <br />
                    <span className="text-[10px] leading-tight text-app-muted">
                      {formatCalendarDateEs(r.run_date)}
                    </span>
                  </td>
                  <td className="p-2">{r.sport}</td>
                  <td className="p-2">{r.status}</td>
                  <td className="p-2 text-right">
                    <div className="inline-flex flex-wrap items-center justify-end gap-x-3 gap-y-1">
                      <Link
                        to={`/runs/${r.daily_run_id}/events`}
                        className="whitespace-nowrap text-app-fg underline decoration-app-line underline-offset-4 hover:decoration-app-fg"
                      >
                        Inspector
                      </Link>
                      <Link
                        to={`/runs/${r.daily_run_id}/picks`}
                        className="whitespace-nowrap text-app-fg underline decoration-app-line underline-offset-4 hover:decoration-app-fg"
                      >
                        Picks
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4">
        <button
          type="button"
          disabled={!q.hasNextPage || q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
          className="rounded-lg border border-app-line bg-app-card px-4 py-2 text-xs font-medium text-app-fg disabled:opacity-40"
        >
          {q.isFetchingNextPage
            ? 'Cargando…'
            : q.hasNextPage
              ? 'Cargar más'
              : 'No hay más'}
        </button>
      </div>
    </div>
  )
}
