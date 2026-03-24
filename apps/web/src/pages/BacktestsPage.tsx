import { useInfiniteQuery } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'
import type { BacktestRunPage } from '@/types/api'

const PAGE = 20

export default function BacktestsPage() {
  const q = useInfiniteQuery({
    queryKey: ['backtest-runs'],
    initialPageParam: undefined as number | undefined,
    queryFn: async ({ pageParam }) => {
      const sp = new URLSearchParams({ limit: String(PAGE) })
      if (pageParam != null) sp.set('cursor', String(pageParam))
      return fetchJson<BacktestRunPage>(`/backtest-runs?${sp}`)
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  })

  const rows = q.data?.pages.flatMap((p) => p.items) ?? []

  return (
    <div>
      <h2 className="mb-1 text-xl font-semibold tracking-tight">Backtests</h2>
      <p className="mb-6 text-sm text-app-muted">
        Lectura de <code className="text-app-fg">backtest_runs</code> y métricas
        asociadas (solo UI; el runner sigue en Python).
      </p>

      {q.isError && (
        <p className="text-sm text-app-danger">
          {(q.error as Error).message}
        </p>
      )}

      <div className="space-y-6">
        {q.isLoading && (
          <p className="font-mono text-xs text-app-muted">Cargando…</p>
        )}
        {!q.isLoading &&
          rows.map((r) => (
            <article
              key={r.backtest_run_id}
              className="rounded-xl border border-app-line bg-app-card p-4 shadow-sm"
            >
              <div className="mb-2 flex flex-wrap items-baseline gap-3 font-mono text-xs">
                <span className="text-app-muted">#{r.backtest_run_id}</span>
                <span>
                  {r.range_start} → {r.range_end}
                </span>
                <span className="text-app-muted">{r.strategy_version}</span>
              </div>
              <pre className="max-h-64 overflow-auto font-mono text-[11px] leading-relaxed text-app-muted">
                {JSON.stringify(r.metrics_json ?? null, null, 2)}
              </pre>
            </article>
          ))}
      </div>

      <div className="mt-6">
        <button
          type="button"
          disabled={!q.hasNextPage || q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
          className="border border-app-line bg-transparent px-4 py-2 font-mono text-xs text-app-fg disabled:opacity-40"
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
