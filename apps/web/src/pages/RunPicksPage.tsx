import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ComboTrackingControls,
  type ComboSavePayload,
} from '@/components/ComboTrackingControls'
import { PickInboxRow } from '@/components/PickInboxRow'
import { fetchJson } from '@/lib/api'
import { useBankrollCOP } from '@/hooks/useBankrollCOP'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import { useUsersQuery } from '@/hooks/useUsersQuery'
import { selectionShortLabel } from '@/lib/marketCopy'
import type { TrackingBoardOut, UserOut } from '@/types/api'

type BoardPick = TrackingBoardOut['picks'][number]

function effectiveOutcome(p: BoardPick): 'win' | 'loss' | 'pending' | null {
  const u = p.user_outcome
  if (u === 'win' || u === 'loss' || u === 'pending') return u
  const ro = p.result?.outcome
  if (ro === 'win' || ro === 'loss' || ro === 'pending') return ro
  return null
}

export default function RunPicksPage() {
  const { dailyRunId } = useParams<{ dailyRunId: string }>()
  const runId = Number(dailyRunId)
  const invalid = Number.isNaN(runId)
  const { userId, setUserId } = useTrackingUser()
  const { bankrollCOP } = useBankrollCOP(userId)
  const qc = useQueryClient()

  const usersQ = useUsersQuery()
  const users = useMemo(() => usersQ.data ?? [], [usersQ.data])

  useEffect(() => {
    if (users.length === 0) return
    if (userId == null) {
      setUserId(users[0].user_id)
      return
    }
    const ok = users.some((u) => u.user_id === userId)
    if (!ok) setUserId(users[0].user_id)
  }, [users, userId, setUserId])

  const boardQ = useQuery({
    queryKey: ['board', runId, userId],
    enabled: !invalid && userId != null,
    queryFn: () =>
      fetchJson<TrackingBoardOut>(
        `/daily-runs/${runId}/board?user_id=${userId}`,
      ),
  })

  const bootstrapM = useMutation({
    mutationFn: () => fetchJson<UserOut[]>('/users/bootstrap', { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const saveComboM = useMutation({
    mutationFn: async (payload: ComboSavePayload) => {
      if (userId == null) throw new Error('user')
      const body: Record<string, unknown> = { taken: payload.taken }
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
      return fetchJson(
        `/users/${userId}/suggested-combos/${payload.comboId}/taken`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      )
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const baselinesM = useMutation({
    mutationFn: () =>
      fetchJson<{ baselines_inserted: number }>(
        `/daily-runs/${runId}/pick-baselines`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
    },
  })

  const regenCombosM = useMutation({
    mutationFn: () =>
      fetchJson(`/daily-runs/${runId}/suggested-combos/regenerate`, {
        method: 'POST',
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
    },
  })

  if (invalid) {
    return <p className="text-sm text-app-muted">Run inválido.</p>
  }

  const board = boardQ.data

  return (
    <div>
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-app-fg">
            Picks del run
          </h2>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-app-muted">
            Lista compacta: abre la ficha para ver la tarjeta completa, cuotas y
            tu seguimiento (tomé, monto, resultado).
          </p>
        </div>
      </div>

      {usersQ.isError && (
        <p className="mb-4 text-sm text-app-danger whitespace-pre-wrap">
          {(usersQ.error as Error).message}
        </p>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-violet-200/80 bg-gradient-to-r from-violet-50/90 to-white p-4 text-xs shadow-sm">
        <span className="font-medium text-violet-900">Usuario</span>
        <select
          className="min-w-[12rem] rounded-md border border-violet-200 bg-white px-2 py-2 text-app-fg shadow-sm"
          value={userId != null ? String(userId) : ''}
          onChange={(e) => {
            const v = e.target.value
            setUserId(v === '' ? null : Number(v))
          }}
          disabled={usersQ.isLoading || users.length === 0}
        >
          {users.length === 0 ? (
            <option value="">
              {usersQ.isLoading ? 'Cargando…' : 'Sin usuarios'}
            </option>
          ) : (
            users.map((u) => (
              <option key={u.user_id} value={String(u.user_id)}>
                {u.display_name} ({u.slug})
              </option>
            ))
          )}
        </select>
        <button
          type="button"
          className="rounded-md border border-app-line bg-white px-3 py-2 text-app-fg shadow-sm disabled:opacity-40"
          disabled={bootstrapM.isPending}
          onClick={() => bootstrapM.mutate()}
        >
          Crear usuarios prueba
        </button>
        <p className="w-full text-[10px] leading-relaxed text-app-muted sm:w-auto sm:flex-1">
          El bankroll en COP está en la barra lateral: ahí se basan las sugerencias
          de monto por pick.
        </p>
      </div>

      {userId == null && !usersQ.isLoading && users.length > 0 && (
        <p className="text-sm text-app-muted">Elige un usuario.</p>
      )}

      {userId != null && boardQ.isError && (
        <p className="text-sm text-app-danger">
          {(boardQ.error as Error).message}
        </p>
      )}

      {userId != null && boardQ.isLoading && (
        <p className="text-sm text-app-muted">Cargando tablero…</p>
      )}

      {userId != null && board && (
        <>
          <div className="mb-4 flex flex-wrap gap-2 text-xs">
            <button
              type="button"
              className="rounded-md border border-teal-200 bg-teal-50 px-3 py-2 font-medium text-teal-950 shadow-sm disabled:opacity-40"
              disabled={baselinesM.isPending}
              onClick={() => baselinesM.mutate()}
            >
              Congelar baseline
            </button>
            <button
              type="button"
              className="rounded-md border border-fuchsia-200 bg-fuchsia-50 px-3 py-2 font-medium text-fuchsia-950 shadow-sm disabled:opacity-40"
              disabled={regenCombosM.isPending}
              onClick={() => regenCombosM.mutate()}
            >
              Regenerar combinadas
            </button>
            {baselinesM.isSuccess && (
              <span className="self-center text-app-muted">
                +{baselinesM.data.baselines_inserted} baselines
              </span>
            )}
          </div>

          {board.picks.length === 0 ? (
            <p className="rounded-xl border border-dashed border-app-line bg-app-card p-8 text-center text-sm text-app-muted">
              Sin picks en este run (ejecuta persist_picks tras el análisis).
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
              {board.picks.map((p, i) => (
                <PickInboxRow
                  key={p.pick_id}
                  pickId={p.pick_id}
                  href={`/picks/${p.pick_id}`}
                  eventLabel={p.event_label}
                  league={p.league}
                  market={p.market}
                  selection={p.selection}
                  pickedValue={p.picked_value}
                  outcome={effectiveOutcome(p)}
                  userTaken={p.user_taken}
                  ordinal={i + 1}
                />
              ))}
            </div>
          )}

          <h3 className="mb-1 mt-14 text-lg font-semibold tracking-tight text-violet-950">
            Combinadas sugeridas
          </h3>
          <p className="mb-5 max-w-xl text-xs leading-relaxed text-app-muted">
            Parlays armados por el modelo. Cada pierna enlaza a su ficha; el tono
            violeta / ámbar las distingue de los singles.
          </p>
          {board.suggested_combos.length === 0 ? (
            <p className="text-xs text-app-muted">
              Pulsa «Regenerar combinadas».
            </p>
          ) : (
            <ul className="space-y-5">
              {board.suggested_combos.map((c) => (
                <li key={c.suggested_combo_id} className="group relative">
                  <div className="rounded-2xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-400 p-[2px] shadow-md">
                    <div className="rounded-[14px] bg-app-card p-4">
                      <div className="border-b border-violet-100 pb-3">
                        <span className="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-900">
                          Combo #{c.rank_order}
                        </span>
                        <p className="mt-2 text-sm font-semibold text-app-fg">
                          {c.legs.length} piernas · parlay sugerido
                        </p>
                        {c.strategy_note && (
                          <p className="mt-1 text-xs leading-relaxed text-app-muted">
                            {c.strategy_note}
                          </p>
                        )}
                      </div>
                      <ol className="mt-3 space-y-2">
                        {c.legs.map((leg, idx) => (
                          <li key={leg.pick_id}>
                            <Link
                              to={`/picks/${leg.pick_id}`}
                              className="flex items-start gap-3 rounded-xl border border-sky-100 bg-gradient-to-r from-sky-50/80 to-white px-3 py-2 text-xs transition-colors hover:border-sky-300 hover:from-sky-50"
                            >
                              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-600 text-[10px] font-bold text-white">
                                {idx + 1}
                              </span>
                              <div className="min-w-0 flex-1">
                                <p className="font-mono text-[10px] text-app-muted">
                                  pick {leg.pick_id} · event {leg.event_id}
                                </p>
                                <p className="mt-0.5 font-medium text-app-fg">
                                  <span className="mr-1 rounded bg-violet-100 px-1 py-0.5 text-[10px] text-violet-900">
                                    {leg.market}
                                  </span>{' '}
                                  {selectionShortLabel(
                                    leg.market,
                                    leg.selection,
                                  )}
                                </p>
                              </div>
                              <span className="shrink-0 text-[10px] font-semibold text-sky-700">
                                Ficha →
                              </span>
                            </Link>
                          </li>
                        ))}
                      </ol>
                      <ComboTrackingControls
                        key={`${c.suggested_combo_id}-${c.user_stake_amount ?? ''}`}
                        combo={c}
                        bankrollCOP={bankrollCOP}
                        disabled={saveComboM.isPending}
                        onSave={(payload) => saveComboM.mutate(payload)}
                      />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
