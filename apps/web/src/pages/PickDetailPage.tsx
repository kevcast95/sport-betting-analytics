import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  OutcomeFeedbackBlock,
  type PickCardData,
} from '@/components/PickTelegramCard'
import { fetchJson } from '@/lib/api'
import type { PickDetail, PickStatusPatchResponse } from '@/types/api'

function pickDetailToFeedbackCard(p: PickDetail): PickCardData {
  const ro = p.result?.outcome
  return {
    pick_id: p.pick_id,
    daily_run_id: p.daily_run_id,
    event_id: p.event_id,
    market: p.market,
    selection: p.selection,
    picked_value: p.picked_value,
    odds_reference: p.odds_reference,
    user_outcome: p.user_outcome ?? undefined,
    system_outcome:
      ro === 'win' || ro === 'loss' || ro === 'pending' ? ro : undefined,
    result: p.result
      ? {
          outcome: p.result.outcome,
          home_score: p.result.home_score,
          away_score: p.result.away_score,
          result_1x2: p.result.result_1x2,
        }
      : null,
  }
}

type OddsRef = Record<string, unknown> | null | undefined

function refStr(ref: OddsRef, key: string): string | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = ref[key]
  if (v == null) return undefined
  return String(v)
}

function refNum(ref: OddsRef, key: string): number | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = ref[key]
  if (typeof v === 'number' && !Number.isNaN(v)) return v
  if (typeof v === 'string') {
    const n = Number.parseFloat(v.replace(',', '.'))
    return Number.isNaN(n) ? undefined : n
  }
  return undefined
}

const DIV = 'border-t border-app-line'

export default function PickDetailPage() {
  const { pickId } = useParams<{ pickId: string }>()
  const id = Number(pickId)
  const invalid = Number.isNaN(id)
  const qc = useQueryClient()

  const q = useQuery({
    queryKey: ['pick', id],
    enabled: !invalid,
    queryFn: () => fetchJson<PickDetail>(`/picks/${id}`),
  })

  const voidMutation = useMutation({
    mutationFn: () =>
      fetchJson<PickStatusPatchResponse>(`/picks/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'void' }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['pick', id] })
      void qc.invalidateQueries({ queryKey: ['picks'] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
      void qc.invalidateQueries({ queryKey: ['board'] })
    },
  })

  if (invalid) {
    return <p className="text-sm text-app-muted">Pick inválido.</p>
  }

  if (q.isLoading) {
    return <p className="text-sm text-app-muted">Cargando…</p>
  }

  if (q.isError) {
    return (
      <p className="text-sm text-app-danger">
        {(q.error as Error).message}
      </p>
    )
  }

  const p = q.data!
  const ref = p.odds_reference as OddsRef
  const selShow =
    refStr(ref, 'selection_display') ?? p.selection
  const razon = refStr(ref, 'razon')
  const conf = refStr(ref, 'confianza')
  const edge = refNum(ref, 'edge_pct')
  const title =
    p.event_label?.trim() || `Evento ${p.event_id}`
  const dateCreated =
    p.created_at_utc.length >= 10 ? p.created_at_utc.slice(0, 10) : '—'
  const timeCreated =
    p.created_at_utc.length >= 16 ? p.created_at_utc.slice(11, 19) : ''

  return (
    <div className="mx-auto max-w-lg">
      <p className="mb-4 text-xs text-app-muted">
        <Link
          to={`/runs/${p.daily_run_id}/picks`}
          className="font-medium text-app-fg underline decoration-app-line underline-offset-2"
        >
          ← Run {p.daily_run_id}
        </Link>
        <span className="mx-2 text-app-line">·</span>
        <Link
          to="/"
          className="text-app-muted underline decoration-app-line underline-offset-2"
        >
          Dashboard
        </Link>
      </p>

      <article className="overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
        <header className="border-b border-app-line px-4 py-3">
          <h1 className="text-base font-semibold leading-snug text-app-fg">
            {title}
          </h1>
          <p className="mt-1 text-xs text-app-muted">
            {[p.league, p.kickoff_display].filter(Boolean).join(' · ')}
          </p>
          <p className="mt-1 font-mono text-[11px] text-app-muted tabular-nums">
            pick #{p.pick_id} · event {p.event_id}
            <br />
            creado {dateCreated}
            {timeCreated ? ` ${timeCreated} UTC` : ''}
          </p>
        </header>

        <OutcomeFeedbackBlock
          p={pickDetailToFeedbackCard(p)}
          className="mx-4 mt-3"
        />

        <section className="space-y-0 px-4 py-3 text-sm">
          <p className="text-[10px] font-medium uppercase tracking-wide text-app-muted">
            Análisis (como Telegram)
          </p>
          <p className="mt-2">
            <span className="text-app-muted">Mercado:</span>{' '}
            <span className="font-medium">{p.market}</span>
          </p>
          <p className="mt-1">
            <span className="text-app-muted">Selección:</span>{' '}
            <span className="font-medium">{selShow}</span>
          </p>
          {p.picked_value != null && (
            <p className="mt-1 font-mono tabular-nums">
              <span className="text-app-muted">Cuota:</span> {p.picked_value}
            </p>
          )}
          {(edge != null || conf) && (
            <p className={`mt-3 text-xs text-app-muted ${DIV} pt-3`}>
              {edge != null && <span className="font-mono">Edge {edge}%</span>}
              {edge != null && conf && ' · '}
              {conf && <span>Confianza {conf}</span>}
            </p>
          )}
          {razon && (
            <p className={`mt-3 text-sm leading-relaxed text-app-fg ${DIV} pt-3`}>
              <span className="text-app-muted">Razón:</span> {razon}
            </p>
          )}
        </section>

        <footer className={`${DIV} bg-neutral-50/60 px-4 py-3 text-xs`}>
          <p className="font-mono text-[11px] text-app-muted">
            Estado pick: {p.status} · idempotencia{' '}
            <span className="break-all">{p.idempotency_key}</span>
          </p>
          {p.status === 'pending' && (
            <button
              type="button"
              disabled={voidMutation.isPending}
              onClick={() => voidMutation.mutate()}
              className="mt-3 rounded-lg border border-app-line bg-app-card px-3 py-2 text-xs font-medium text-app-fg disabled:opacity-40"
            >
              {voidMutation.isPending ? 'Enviando…' : 'Anular pick (void)'}
            </button>
          )}
          {voidMutation.isError && (
            <p className="mt-2 text-xs text-app-danger">
              {(voidMutation.error as Error).message}
            </p>
          )}
        </footer>
      </article>

      <details className="mt-8 rounded-lg border border-app-line bg-app-card p-3 text-xs">
        <summary className="cursor-pointer font-medium text-app-muted">
          JSON técnico (resultado API / odds_reference)
        </summary>
        <pre className="mt-3 overflow-x-auto rounded-lg border border-app-line bg-app-bg p-3 font-mono text-[10px] leading-relaxed">
          {JSON.stringify(
            { result: p.result, odds_reference: p.odds_reference },
            null,
            2,
          )}
        </pre>
      </details>
    </div>
  )
}
