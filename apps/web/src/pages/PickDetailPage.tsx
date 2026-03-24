import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  OutcomeFeedbackBlock,
  type PickCardData,
} from '@/components/PickTelegramCard'
import {
  PickTrackingControls,
  type PickSavePayload,
} from '@/components/PickTrackingControls'
import { fetchJson } from '@/lib/api'
import {
  formatShortDateFromYMD,
  kickoffReadableCol,
} from '@/lib/formatDateTime'
import {
  describeMarketKind,
  describeSelectionPlain,
} from '@/lib/marketCopy'
import { useBankrollCOP } from '@/hooks/useBankrollCOP'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { PickDetail, PickStatusPatchResponse, TrackingBoardOut } from '@/types/api'

type BoardPick = TrackingBoardOut['picks'][number]

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
    event_label: p.event_label,
    league: p.league,
    kickoff_display: p.kickoff_display,
    created_at_utc: p.created_at_utc,
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

function mergedFeedbackCard(
  detail: PickDetail,
  boardPick: BoardPick | undefined,
): PickCardData {
  const base = pickDetailToFeedbackCard(detail)
  if (!boardPick) return base
  return {
    ...base,
    user_taken: boardPick.user_taken ?? base.user_taken,
    user_outcome: boardPick.user_outcome ?? base.user_outcome,
    decision_origin: boardPick.decision_origin ?? base.decision_origin,
    stake_amount: boardPick.stake_amount ?? base.stake_amount,
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
  const { userId } = useTrackingUser()
  const { bankrollCOP } = useBankrollCOP(userId)

  const q = useQuery({
    queryKey: ['pick', id],
    enabled: !invalid,
    queryFn: () => fetchJson<PickDetail>(`/picks/${id}`),
  })

  const p = q.data

  const boardQ = useQuery({
    queryKey: ['board', p?.daily_run_id, userId],
    enabled: !!p && userId != null,
    queryFn: () =>
      fetchJson<TrackingBoardOut>(
        `/daily-runs/${p!.daily_run_id}/board?user_id=${userId}`,
      ),
  })

  const boardPick = p
    ? boardQ.data?.picks.find((x) => x.pick_id === p.pick_id)
    : undefined

  const savePickM = useMutation({
    mutationFn: async (payload: PickSavePayload) => {
      if (userId == null) throw new Error('user')
      const body: Record<string, unknown> = { taken: payload.taken }
      if (payload.decision_origin !== undefined)
        body.decision_origin = payload.decision_origin || null
      if (payload.stake_amount !== undefined)
        body.stake_amount = payload.stake_amount
      if (payload.userOutcome === 'auto') body.user_outcome_auto = true
      else if (
        payload.userOutcome === 'win' ||
        payload.userOutcome === 'loss' ||
        payload.userOutcome === 'pending'
      ) {
        body.user_outcome = payload.userOutcome
      }
      return fetchJson(`/users/${userId}/picks/${payload.pickId}/taken`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    },
    onSuccess: () => {
      if (p) {
        void qc.invalidateQueries({ queryKey: ['board', p.daily_run_id, userId] })
      }
      void qc.invalidateQueries({ queryKey: ['pick', id] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
      if (userId != null) {
        void qc.invalidateQueries({ queryKey: ['user', userId] })
      }
    },
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

  const pick = q.data!
  const ref = pick.odds_reference as OddsRef
  const selShow =
    refStr(ref, 'selection_display') ?? pick.selection
  const razon = refStr(ref, 'razon')
  const conf = refStr(ref, 'confianza')
  const edge = refNum(ref, 'edge_pct')
  const title =
    pick.event_label?.trim() || `Evento ${pick.event_id}`
  const runDateLabel = pick.run_date?.trim()
    ? formatShortDateFromYMD(pick.run_date.trim())
    : null
  const kickoffCol = kickoffReadableCol(pick.kickoff_display ?? null)

  return (
    <div className="mx-auto max-w-lg">
      <p className="mb-4 text-xs text-app-muted">
        <Link
          to={`/runs/${pick.daily_run_id}/picks`}
          className="font-medium text-violet-800 underline decoration-violet-200 underline-offset-2"
        >
          ← Run {pick.daily_run_id}
        </Link>
        <span className="mx-2 text-app-line">·</span>
        <Link
          to="/"
          className="text-app-muted underline decoration-app-line underline-offset-2"
        >
          Dashboard
        </Link>
      </p>

      <article className="overflow-hidden rounded-2xl border border-violet-200/80 bg-app-card shadow-lg shadow-violet-100/50">
        <header className="border-b border-violet-100 bg-gradient-to-br from-violet-50 via-white to-sky-50/50 px-4 py-4">
          <h1 className="text-lg font-semibold leading-snug text-violet-950">
            {title}
          </h1>
          {pick.league?.trim() ? (
            <p className="mt-1 text-xs text-app-muted">{pick.league.trim()}</p>
          ) : null}
          {kickoffCol ? (
            <p className="mt-2 text-sm leading-snug text-app-fg">
              <span className="text-app-muted">Inicio del partido: </span>
              <span className="font-mono font-semibold tabular-nums">
                {kickoffCol}
              </span>
            </p>
          ) : null}
          {runDateLabel ? (
            <p className="mt-1 text-xs text-app-muted">
              Día del análisis (run):{' '}
              <span className="font-mono text-app-fg">{runDateLabel}</span>
            </p>
          ) : null}
          <p className="mt-2 font-mono text-[10px] text-violet-700/90 tabular-nums">
            pick #{pick.pick_id} · event {pick.event_id}
          </p>
        </header>

        <OutcomeFeedbackBlock
          p={mergedFeedbackCard(pick, boardPick)}
          className="mx-4 mt-3"
        />

        <section className="space-y-0 px-4 py-4 text-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-800">
            Qué estás apostando (web)
          </p>
          <p className="mt-2">
            <span className="inline-block rounded-md border border-violet-200 bg-violet-50 px-2 py-0.5 text-xs font-semibold text-violet-950">
              {pick.market.trim()}
            </span>
          </p>
          <p className="mt-2 text-xs leading-relaxed text-app-fg">
            {describeMarketKind(pick.market)}
          </p>
          <p className="mt-3">
            <span className="text-app-muted">Código en el boletín:</span>{' '}
            <span className="font-mono font-medium">{selShow}</span>
          </p>
          <p className="mt-2 rounded-lg border border-sky-100 bg-sky-50/80 px-3 py-2 text-xs leading-relaxed text-sky-950">
            <span className="font-semibold text-sky-900">Resumen:</span>{' '}
            {describeSelectionPlain(
              pick.market,
              pick.selection,
              pick.event_label,
            )}
          </p>
          {pick.picked_value != null && (
            <p className="mt-3 font-mono tabular-nums">
              <span className="text-app-muted">Cuota (pago si aciertas):</span>{' '}
              <span className="font-semibold text-app-fg">{pick.picked_value}</span>
            </p>
          )}
          {(Boolean(conf?.trim()) || edge != null) && (
            <div className={`mt-4 flex flex-wrap gap-2 ${DIV} pt-4`}>
              {conf?.trim() ? (
                <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-950">
                  Confianza del modelo: {conf.trim()}
                </span>
              ) : null}
              {edge != null && (
                <span className="rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 font-mono text-xs font-medium text-teal-950 tabular-nums">
                  Ventaja que ve el modelo: {edge}%
                </span>
              )}
            </div>
          )}
          {razon && (
            <p className={`mt-4 text-sm leading-relaxed text-app-fg ${DIV} pt-4`}>
              <span className="font-medium text-app-muted">
                Por qué lo sugiere el modelo:
              </span>{' '}
              {razon}
            </p>
          )}
        </section>

        <section
          className={`${DIV} bg-gradient-to-b from-violet-50/90 to-sky-50/30 px-4 py-4`}
        >
          <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-900">
            Tu feedback (mismo tablero que en el run)
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-app-muted">
            Tomé / origen / monto en COP / cierre manual. El bankroll para
            sugerencias está en la barra lateral.
          </p>
          {userId == null && (
            <p className="mt-3 text-xs text-amber-800">
              Elige un usuario en la página del run o en el dashboard para
              guardar aquí.
            </p>
          )}
          {userId != null && boardQ.isLoading && (
            <p className="mt-3 text-xs text-app-muted">Cargando tu seguimiento…</p>
          )}
          {userId != null && boardQ.isError && (
            <p className="mt-3 text-xs text-app-danger">
              No se pudo cargar el tablero del run.
            </p>
          )}
          {userId != null && boardPick && (
            <div className="mt-3 rounded-xl border border-white/80 bg-white/90 p-3 shadow-sm">
              <PickTrackingControls
                pick={boardPick}
                userId={userId}
                bankrollCOP={bankrollCOP}
                disabled={savePickM.isPending}
                onSave={(payload) => savePickM.mutate(payload)}
              />
            </div>
          )}
          {userId != null && boardQ.isSuccess && !boardPick && (
            <p className="mt-3 text-xs text-app-muted">
              Este pick no aparece en el último tablero del run (poco usual).
            </p>
          )}
        </section>

        <footer className={`${DIV} bg-neutral-50/80 px-4 py-3 text-xs`}>
          <p className="font-mono text-[11px] text-app-muted">
            <span className="inline-block rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase text-neutral-600">
              {pick.status}
            </span>
            {' · '}
            idempotencia{' '}
            <span className="break-all text-[10px]">{pick.idempotency_key}</span>
          </p>
          {pick.status === 'pending' && (
            <button
              type="button"
              disabled={voidMutation.isPending}
              onClick={() => voidMutation.mutate()}
              className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-900 disabled:opacity-40"
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

      <details className="mt-8 rounded-xl border border-app-line bg-app-card p-3 text-xs shadow-sm">
        <summary className="cursor-pointer font-semibold text-app-muted">
          JSON técnico (resultado API / odds_reference)
        </summary>
        <pre className="mt-3 overflow-x-auto rounded-lg border border-app-line bg-app-bg p-3 font-mono text-[10px] leading-relaxed">
          {JSON.stringify(
            { result: pick.result, odds_reference: pick.odds_reference },
            null,
            2,
          )}
        </pre>
      </details>
    </div>
  )
}
