import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PickTelegramCard, type PickCardData } from '@/components/PickTelegramCard'
import { fetchJson } from '@/lib/api'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import { useUsersQuery } from '@/hooks/useUsersQuery'
import type { TrackingBoardOut, UserOut } from '@/types/api'

const RISK = [
  '',
  'escalonada',
  'segura',
  'balanceada',
  'arriesgada',
  'justificada',
] as const
const ORIGIN = ['', 'analizada', 'intuicion', 'impulso'] as const

type BoardPick = TrackingBoardOut['picks'][number]

function boardPickSaveBase(p: BoardPick) {
  return {
    pickId: p.pick_id,
    taken: p.user_taken ?? false,
    risk_category: p.risk_category ?? null,
    decision_origin: p.decision_origin ?? null,
    stake_amount: p.stake_amount ?? null,
  }
}

function toCard(p: BoardPick): PickCardData {
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
    result: p.result,
    user_outcome: p.user_outcome ?? undefined,
    system_outcome:
      ro === 'win' || ro === 'loss' || ro === 'pending' ? ro : undefined,
    user_taken: p.user_taken,
    risk_category: p.risk_category,
    decision_origin: p.decision_origin,
    stake_amount: p.stake_amount,
  }
}

export default function RunPicksPage() {
  const { dailyRunId } = useParams<{ dailyRunId: string }>()
  const runId = Number(dailyRunId)
  const invalid = Number.isNaN(runId)
  const { userId, setUserId } = useTrackingUser()
  const qc = useQueryClient()

  const usersQ = useUsersQuery()
  const users = usersQ.data ?? []

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

  const savePickM = useMutation({
    mutationFn: async (payload: {
      pickId: number
      taken: boolean
      risk_category?: string | null
      decision_origin?: string | null
      stake_amount?: number | null
      /** Sin enviar: el API conserva user_outcome. */
      userOutcome?: 'auto' | 'win' | 'loss' | 'pending'
    }) => {
      if (userId == null) throw new Error('user')
      const body: Record<string, unknown> = { taken: payload.taken }
      if (payload.risk_category !== undefined)
        body.risk_category = payload.risk_category || null
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
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const toggleComboM = useMutation({
    mutationFn: async ({
      comboId,
      taken,
    }: {
      comboId: number
      taken: boolean
    }) => {
      if (userId == null) throw new Error('user')
      return fetchJson(`/users/${userId}/suggested-combos/${comboId}/taken`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taken }),
      })
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
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
      <p className="mb-4 text-xs text-app-muted">
        <Link
          to="/runs"
          className="font-medium text-app-fg underline decoration-app-line underline-offset-2"
        >
          ← Runs
        </Link>
        <span className="mx-2 text-app-line">/</span>
        <span className="font-mono">run {runId}</span>
      </p>
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">
            Picks y tracking
          </h2>
          {board && (
            <p className="mt-1 font-mono text-sm text-app-muted tabular-nums">
              Fecha run <span className="text-app-fg">{board.run.run_date}</span>
              {' · '}
              {board.run.sport}
            </p>
          )}
        </div>
      </div>

      {usersQ.isError && (
        <p className="mb-4 text-sm text-app-danger whitespace-pre-wrap">
          {(usersQ.error as Error).message}
        </p>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-app-line bg-app-card p-4 text-xs">
        <span className="text-app-muted">Usuario</span>
        <select
          className="min-w-[12rem] rounded-md border border-app-line bg-app-bg px-2 py-2 text-app-fg"
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
          className="rounded-md border border-app-line px-3 py-2 text-app-fg disabled:opacity-40"
          disabled={bootstrapM.isPending}
          onClick={() => bootstrapM.mutate()}
        >
          Crear usuarios prueba
        </button>
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
              className="rounded-md border border-app-line bg-app-card px-3 py-2 text-app-fg disabled:opacity-40"
              disabled={baselinesM.isPending}
              onClick={() => baselinesM.mutate()}
            >
              Congelar baseline
            </button>
            <button
              type="button"
              className="rounded-md border border-app-line bg-app-card px-3 py-2 text-app-fg disabled:opacity-40"
              disabled={regenCombosM.isPending}
              onClick={() => regenCombosM.mutate()}
            >
              Regenerar combinaciones
            </button>
            {baselinesM.isSuccess && (
              <span className="self-center text-app-muted">
                +{baselinesM.data.baselines_inserted} baselines
              </span>
            )}
          </div>

          <p className="mb-3 text-xs text-app-muted">
            Desliza horizontalmente · análisis y tu seguimiento van en la misma tarjeta.
          </p>

          {board.picks.length === 0 ? (
            <p className="rounded-xl border border-dashed border-app-line bg-app-card p-8 text-center text-sm text-app-muted">
              Sin picks en este run (ejecuta persist_picks tras el análisis).
            </p>
          ) : (
            <div className="-mx-1 flex gap-4 overflow-x-auto overflow-y-visible pb-4 pt-1 [scrollbar-gutter:stable] snap-x snap-mandatory">
              {board.picks.map((p) => (
                <div
                  key={p.pick_id}
                  className="w-[min(100vw-1.5rem,22rem)] shrink-0 snap-start"
                >
                  <PickTelegramCard
                    p={toCard(p)}
                    compact
                    trackingSlot={
                      <div className="grid gap-2 text-[11px]">
                        <label className="grid grid-cols-[4rem_1fr] items-center gap-2">
                          <span className="text-app-muted">Tomé</span>
                          <select
                            className="rounded border border-app-line bg-app-card px-2 py-1.5"
                            value={
                              p.user_taken === true
                                ? 'yes'
                                : p.user_taken === false
                                  ? 'no'
                                  : ''
                            }
                            onChange={(e) => {
                              const v = e.target.value
                              if (v === '') return
                              savePickM.mutate({
                                ...boardPickSaveBase(p),
                                taken: v === 'yes',
                              })
                            }}
                            disabled={savePickM.isPending}
                          >
                            <option value="">—</option>
                            <option value="yes">Sí</option>
                            <option value="no">No</option>
                          </select>
                        </label>
                        <label className="grid grid-cols-[4rem_1fr] items-center gap-2">
                          <span className="text-app-muted">Riesgo</span>
                          <select
                            className="rounded border border-app-line bg-app-card px-2 py-1.5"
                            value={p.risk_category ?? ''}
                            onChange={(e) => {
                              savePickM.mutate({
                                ...boardPickSaveBase(p),
                                risk_category: e.target.value || null,
                              })
                            }}
                            disabled={savePickM.isPending}
                          >
                            {RISK.map((x) => (
                              <option key={x || 'empty'} value={x}>
                                {x || '—'}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="grid grid-cols-[4rem_1fr] items-center gap-2">
                          <span className="text-app-muted">Origen</span>
                          <select
                            className="rounded border border-app-line bg-app-card px-2 py-1.5"
                            value={p.decision_origin ?? ''}
                            onChange={(e) => {
                              savePickM.mutate({
                                ...boardPickSaveBase(p),
                                decision_origin: e.target.value || null,
                              })
                            }}
                            disabled={savePickM.isPending}
                          >
                            {ORIGIN.map((x) => (
                              <option key={x || 'empty'} value={x}>
                                {x || '—'}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="grid grid-cols-[4rem_1fr] items-center gap-2">
                          <span className="text-app-muted">Stake</span>
                          <input
                            type="number"
                            min={0}
                            step={0.01}
                            className="rounded border border-app-line bg-app-card px-2 py-1.5 font-mono tabular-nums"
                            defaultValue={p.stake_amount ?? ''}
                            key={`${p.pick_id}-${p.stake_amount}`}
                            onBlur={(e) => {
                              const raw = e.target.value
                              const n =
                                raw === '' ? null : Number.parseFloat(raw)
                              if (
                                raw !== '' &&
                                (n === null || Number.isNaN(n))
                              )
                                return
                              savePickM.mutate({
                                ...boardPickSaveBase(p),
                                stake_amount: n,
                              })
                            }}
                            disabled={savePickM.isPending}
                          />
                        </label>
                        <label className="grid grid-cols-[4rem_1fr] items-center gap-2">
                          <span className="text-app-muted">Cierre</span>
                          <select
                            className="rounded border border-app-line bg-app-card px-2 py-1.5"
                            value={
                              p.user_outcome === 'win' ||
                              p.user_outcome === 'loss' ||
                              p.user_outcome === 'pending'
                                ? p.user_outcome
                                : 'auto'
                            }
                            onChange={(e) => {
                              const v = e.target.value
                              if (v === 'auto') {
                                savePickM.mutate({
                                  ...boardPickSaveBase(p),
                                  userOutcome: 'auto',
                                })
                                return
                              }
                              savePickM.mutate({
                                ...boardPickSaveBase(p),
                                userOutcome: v as 'win' | 'loss' | 'pending',
                              })
                            }}
                            disabled={savePickM.isPending}
                          >
                            <option value="auto">Solo auto (sin cierre manual)</option>
                            <option value="win">Gané (yo)</option>
                            <option value="loss">Perdí (yo)</option>
                            <option value="pending">Pendiente (yo)</option>
                          </select>
                        </label>
                      </div>
                    }
                  />
                </div>
              ))}
            </div>
          )}

          <h3 className="mb-2 mt-12 text-base font-semibold">
            Combinaciones sugeridas
          </h3>
          <p className="mb-4 text-xs text-app-muted">
            Hasta 2 parlays · confianza en{' '}
            <code className="rounded bg-neutral-100 px-1">odds_reference</code>
          </p>
          {board.suggested_combos.length === 0 ? (
            <p className="text-xs text-app-muted">
              Pulsa «Regenerar combinaciones».
            </p>
          ) : (
            <ul className="space-y-4 text-xs">
              {board.suggested_combos.map((c) => (
                <li
                  key={c.suggested_combo_id}
                  className="rounded-xl border border-app-line bg-app-card p-4"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <span className="text-app-muted">#{c.rank_order}</span>
                    <span className="text-app-muted">Tomé</span>
                    <select
                      className="rounded border border-app-line bg-app-bg px-2 py-1"
                      value={
                        c.user_taken === true
                          ? 'yes'
                          : c.user_taken === false
                            ? 'no'
                            : ''
                      }
                      onChange={(e) => {
                        const v = e.target.value
                        if (v === '') return
                        toggleComboM.mutate({
                          comboId: c.suggested_combo_id,
                          taken: v === 'yes',
                        })
                      }}
                      disabled={toggleComboM.isPending}
                    >
                      <option value="">—</option>
                      <option value="yes">Sí</option>
                      <option value="no">No</option>
                    </select>
                  </div>
                  <ul className="list-inside list-disc text-app-muted">
                    {c.legs.map((leg) => (
                      <li key={leg.pick_id}>
                        pick {leg.pick_id} · event {leg.event_id} ·{' '}
                        {leg.market} {leg.selection}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
