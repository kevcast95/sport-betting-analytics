import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { ListPagination } from '@/components/ListPagination'
import { Link, useParams } from 'react-router-dom'
import {
  ComboTrackingControls,
  type ComboSavePayload,
} from '@/components/ComboTrackingControls'
import { CardExplain, HelpCueIcon } from '@/components/CardExplain'
import { PickInboxRow } from '@/components/PickInboxRow'
import { SportHiddenInUiMessage } from '@/components/SportHiddenInUiMessage'
import { ViewContextBar } from '@/components/ViewContextBar'
import { useUiSportsVisibility } from '@/contexts/UiSportsVisibilityContext'
import { fetchJson } from '@/lib/api'
import { usePickOutcomeQuickMutation } from '@/hooks/usePickOutcomeQuickMutation'
import { usePickOutcomeAutoQuickMutation } from '@/hooks/usePickOutcomeAutoQuickMutation'
import { useBankrollCOP } from '@/hooks/useBankrollCOP'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import { useListPageSize } from '@/hooks/useListPageSize'
import { selectionShortLabel } from '@/lib/marketCopy'
import { confidenceTierFromLabel } from '@/lib/stakeSuggestion'
import type { TrackingBoardOut, ValidatePicksRunResponse } from '@/types/api'

type BoardPick = TrackingBoardOut['picks'][number]
type RunPicksStats = {
  total_generated: number
  tradable_visible: number
  hidden_non_tradable: number
  min_tradable_odds: number
}

type OddsRef = Record<string, unknown> | null | undefined

function refStr(ref: OddsRef, key: string): string | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = (ref as Record<string, unknown>)[key]
  if (v == null) return undefined
  return String(v)
}

type PickSortMode = 'confidence' | 'kickoff'

function kickoffMs(p: BoardPick): number {
  const k = p.kickoff_at_utc
  if (k) {
    const t = Date.parse(k)
    if (!Number.isNaN(t)) return t
  }
  return Number.MAX_SAFE_INTEGER
}

function effectiveOutcome(p: BoardPick): 'win' | 'loss' | 'pending' | null {
  const u = p.user_outcome
  if (u === 'win' || u === 'loss' || u === 'pending') return u
  const ro = p.result?.outcome
  if (ro === 'win' || ro === 'loss' || ro === 'pending') return ro
  return null
}

const COMBOS_SECTION_STORAGE = 'altea.runPicks.showCombos'

function loadShowCombosPreference(): boolean {
  try {
    return localStorage.getItem(COMBOS_SECTION_STORAGE) !== '0'
  } catch {
    return true
  }
}

function validateSofaTag(phase: string | undefined): string | null {
  if (phase === 'morning') return 'Mañana'
  if (phase === 'evening') return 'Tarde'
  if (phase === 'full') return 'Histórico'
  return null
}

function legOutcomeShort(
  o: 'win' | 'loss' | 'pending' | null | undefined,
): { label: string; className: string } {
  if (o === 'win')
    return { label: 'Pierna: ganada', className: 'border-emerald-200 bg-emerald-50 text-emerald-900' }
  if (o === 'loss')
    return { label: 'Pierna: perdida', className: 'border-red-200 bg-red-50 text-red-900' }
  return { label: 'Pierna: pendiente', className: 'border-amber-200 bg-amber-50 text-amber-900' }
}

export default function RunPicksPage() {
  const { dailyRunId } = useParams<{ dailyRunId: string }>()
  const runId = Number(dailyRunId)
  const invalid = Number.isNaN(runId)
  const { userId } = useTrackingUser()
  const { bankrollCOP } = useBankrollCOP(userId)
  const qc = useQueryClient()
  const [pickQuery, setPickQuery] = useState('')
  /** '' = todas; valor exacto del modelo; '__sin__' = sin campo confianza */
  const [confidenceFilter, setConfidenceFilter] = useState('')
  const [outcomeFilter, setOutcomeFilter] = useState<
    'all' | 'win' | 'loss' | 'pending'
  >('all')
  const [pickListPage, setPickListPage] = useState(0)
  const [pickSortMode, setPickSortMode] = useState<PickSortMode>('confidence')
  const [validateFlash, setValidateFlash] = useState<string | null>(null)
  const { pageSize: pickPageSize, setPageSize: setPickPageSize } =
    useListPageSize()
  const quickOutcomeM = usePickOutcomeQuickMutation(userId)
  const quickAutoOutcomeM = usePickOutcomeAutoQuickMutation(userId)
  const [showCombosSection, setShowCombosSection] = useState(
    loadShowCombosPreference,
  )

  useEffect(() => {
    try {
      localStorage.setItem(
        COMBOS_SECTION_STORAGE,
        showCombosSection ? '1' : '0',
      )
    } catch {
      /* ignore */
    }
  }, [showCombosSection])

  useEffect(() => {
    setPickListPage(0)
  }, [pickQuery, confidenceFilter, outcomeFilter, pickPageSize, pickSortMode])

  const { isRunSportVisible } = useUiSportsVisibility()

  const boardQ = useQuery({
    queryKey: ['board', runId, userId],
    enabled: !invalid && userId != null,
    queryFn: () =>
      fetchJson<TrackingBoardOut>(
        `/daily-runs/${runId}/board?user_id=${userId}`,
      ),
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

  const regenCombosM = useMutation({
    mutationFn: () =>
      fetchJson(`/daily-runs/${runId}/suggested-combos/regenerate`, {
        method: 'POST',
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
    },
  })

  const validatePicksM = useMutation({
    mutationFn: () =>
      fetchJson<ValidatePicksRunResponse>(
        `/daily-runs/${runId}/validate-picks`,
        { method: 'POST' },
      ),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['board', runId, userId] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
      void qc.invalidateQueries({ queryKey: ['pick'] })
      void qc.invalidateQueries({ queryKey: ['picks'] })
      if (data.ok) {
        setValidateFlash(
          `Listo: ${data.validated} liquidados (win/loss), ${data.pending_outcomes} siguen pendientes · procesados ${data.total_processed}.\nCohorte: ${data.execution_slot_label_es}`,
        )
      } else {
        setValidateFlash(
          data.message ??
            `Falló la validación (código ${data.subprocess_exit_code}). Revisa el API / logs.`,
        )
      }
    },
    onError: (e) => {
      setValidateFlash((e as Error).message)
    },
  })

  const board = boardQ.data
  const picksStats = (board as (TrackingBoardOut & { picks_stats?: RunPicksStats }) | undefined)?.picks_stats
  const picksStatsTotal = picksStats?.total_generated ?? 0
  const picksStatsTradablePct =
    picksStatsTotal > 0 && picksStats
      ? Math.round((picksStats.tradable_visible / picksStatsTotal) * 100)
      : 0
  const picksStatsAnalysisPct =
    picksStatsTotal > 0 && picksStats
      ? Math.round((picksStats.hidden_non_tradable / picksStatsTotal) * 100)
      : 0

  const picksOrdered = useMemo(() => {
    if (!board) return []
    const score: Record<'high' | 'medium' | 'low' | 'unknown', number> = {
      high: 3,
      medium: 2,
      low: 1,
      unknown: 0,
    }
    const tierOf = (p: BoardPick) => {
      const conf = refStr(p.odds_reference as OddsRef, 'confianza')
      return confidenceTierFromLabel(conf)
    }
    const list = [...board.picks]
    if (pickSortMode === 'kickoff') {
      list.sort((a, b) => {
        const d = kickoffMs(a) - kickoffMs(b)
        if (d !== 0) return d
        return b.pick_id - a.pick_id
      })
      return list
    }
    return list.sort((a, b) => {
      const tA = tierOf(a)
      const tB = tierOf(b)
      const d = score[tB] - score[tA]
      if (d !== 0) return d
      return b.pick_id - a.pick_id
    })
  }, [board, pickSortMode])

  const picksFiltered = useMemo(() => {
    const q = pickQuery.trim().toLowerCase()
    return picksOrdered.filter((p) => {
      const confRaw = refStr(p.odds_reference as OddsRef, 'confianza')
      const confTrim = confRaw?.trim() ?? ''

      if (confidenceFilter === '__sin__') {
        if (confTrim.length > 0) return false
      } else if (confidenceFilter !== '') {
        if (confTrim !== confidenceFilter) return false
      }

      const eff = effectiveOutcome(p)
      if (outcomeFilter === 'win') {
        if (eff !== 'win') return false
      } else if (outcomeFilter === 'loss') {
        if (eff !== 'loss') return false
      } else if (outcomeFilter === 'pending') {
        // `effectiveOutcome()` devuelve `null` si aún no hay información => en la UI ya se pinta como pendiente.
        if (eff !== 'pending' && eff !== null) return false
      }

      if (!q) return true
      const haystack = [
        String(p.pick_id),
        String(p.event_id),
        p.event_label ?? '',
        p.league ?? '',
        p.market ?? '',
        p.selection ?? '',
        confTrim,
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(q)
    })
  }, [picksOrdered, pickQuery, confidenceFilter, outcomeFilter])

  const pickTotal = picksFiltered.length

  useEffect(() => {
    const maxP =
      pickTotal <= 0 ? 0 : Math.max(0, Math.ceil(pickTotal / pickPageSize) - 1)
    if (pickListPage > maxP) setPickListPage(maxP)
  }, [pickTotal, pickPageSize, pickListPage])

  const pickPageSafe =
    pickTotal <= 0
      ? 0
      : Math.min(
          pickListPage,
          Math.max(0, Math.ceil(pickTotal / pickPageSize) - 1),
        )
  const picksPageSlice = useMemo(() => {
    const start = pickPageSafe * pickPageSize
    return picksFiltered.slice(start, start + pickPageSize)
  }, [picksFiltered, pickPageSafe, pickPageSize])

  const boardListStats = useMemo(() => {
    if (!board) return null
    let pending = 0
    let win = 0
    let loss = 0
    for (const p of board.picks) {
      const e = effectiveOutcome(p)
      if (e === 'win') win += 1
      else if (e === 'loss') loss += 1
      else pending += 1
    }
    return {
      total: board.picks.length,
      pending,
      win,
      loss,
    }
  }, [board])

  if (invalid) {
    return <p className="text-sm text-app-muted">Run inválido.</p>
  }

  const run = boardQ.data?.run

  if (
    boardQ.isSuccess &&
    boardQ.data?.run != null &&
    !isRunSportVisible(boardQ.data.run.sport)
  ) {
    const r = boardQ.data.run
    return (
      <div>
        <ViewContextBar
          crumbs={[
            { label: 'Inicio', to: '/' },
            {
              label: `Ejecución ${r.run_date} · ${r.sport}`,
              to: `/runs/${runId}/events`,
            },
            { label: 'Picks' },
          ]}
        />
        <div className="mt-4">
          <SportHiddenInUiMessage sportLabel={r.sport} />
        </div>
      </div>
    )
  }

  return (
    <div>
      <ViewContextBar
        crumbs={[
          { label: 'Inicio', to: '/' },
          run
            ? {
                label: `Ejecución ${run.run_date} · ${run.sport}`,
                to: `/runs/${runId}/events`,
              }
            : { label: `Run ${runId}`, to: `/runs/${runId}/events` },
          { label: 'Picks' },
        ]}
      />
      <div className="mb-4">
        <h2 className="font-serif text-xl font-normal tracking-tight text-violet-950">
          Picks del run
        </h2>
        {userId != null && board && boardListStats ? (
          <>
            <p className="mt-1 text-xs text-app-muted">
              <span className="font-mono tabular-nums text-app-fg">{boardListStats.total}</span> en tablero
              {boardListStats.total > 0 ? (
                <>
                  {' · '}
                  <span className="font-mono tabular-nums text-app-fg">{boardListStats.pending}</span> pendientes
                  de resultado
                  {' · '}
                  <span className="font-mono tabular-nums text-emerald-800">{boardListStats.win}</span>
                  {' gan. · '}
                  <span className="font-mono tabular-nums text-red-800">{boardListStats.loss}</span> perd.
                </>
              ) : null}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Link
                to={`/runs/${runId}/events`}
                className="inline-flex rounded-md border border-violet-200/80 bg-violet-50/70 px-2.5 py-1.5 text-[11px] font-medium text-violet-950 shadow-sm hover:bg-violet-100/80"
              >
                Ver eventos del run
              </Link>
              <Link
                to={
                  board.run.sport === 'tennis'
                    ? `/?run_date=${encodeURIComponent(board.run.run_date)}&sport=tennis`
                    : `/?run_date=${encodeURIComponent(board.run.run_date)}`
                }
                className="inline-flex rounded-md border border-app-line bg-white px-2.5 py-1.5 text-[11px] font-medium text-app-fg shadow-sm hover:bg-neutral-50"
              >
                Resumen del día
              </Link>
              {boardListStats.total > 0 && boardListStats.pending > 0 ? (
                <button
                  type="button"
                  onClick={() => setOutcomeFilter('pending')}
                  className={`inline-flex rounded-md border px-2.5 py-1.5 text-[11px] font-medium shadow-sm ${
                    outcomeFilter === 'pending'
                      ? 'border-violet-400 bg-violet-100 text-violet-950'
                      : 'border-app-line bg-white text-app-muted hover:bg-violet-50/60 hover:text-violet-950'
                  }`}
                >
                  Solo pendientes ({boardListStats.pending})
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => setOutcomeFilter('all')}
                className={`inline-flex rounded-md border px-2.5 py-1.5 text-[11px] font-medium shadow-sm ${
                  outcomeFilter === 'all'
                    ? 'border-violet-400 bg-violet-100 text-violet-950'
                    : 'border-app-line bg-white text-app-muted hover:bg-violet-50/60 hover:text-violet-950'
                }`}
              >
                Todos los estados
              </button>
            </div>
          </>
        ) : null}
      </div>

      {userId == null && (
        <p className="mb-4 text-sm text-app-muted">
          Elige o crea un usuario en el menú lateral (arriba).
        </p>
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
          <details className="mb-4 rounded-xl border border-violet-200/50 bg-violet-50/25 shadow-sm">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-xs font-medium text-violet-950 [list-style:none] [&::-webkit-details-marker]:hidden">
              <HelpCueIcon />
              <span>Mantenimiento del run (avanzado)</span>
              <span className="hidden font-normal text-app-muted sm:inline">
                · combinadas, validación SofaScore (cohorte según hora)
              </span>
            </summary>
            <div className="space-y-3 border-t border-violet-100/80 px-3 py-3">
              <div className="flex flex-wrap gap-2 text-xs">
                <button
                  type="button"
                  className="rounded-md border border-violet-200/80 bg-white px-3 py-2 font-medium text-violet-950 shadow-sm hover:bg-violet-50 disabled:opacity-40"
                  disabled={regenCombosM.isPending}
                  onClick={() => regenCombosM.mutate()}
                >
                  Regenerar combinadas
                </button>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-md border border-violet-200/80 bg-white px-3 py-2 font-medium text-violet-950 shadow-sm hover:bg-violet-50 disabled:opacity-40"
                  disabled={validatePicksM.isPending}
                  title={
                    board.validate_window?.label_es ??
                    'Ejecuta validate_picks para picks pendientes de este run (SofaScore).'
                  }
                  onClick={() => {
                    setValidateFlash(null)
                    validatePicksM.mutate()
                  }}
                >
                  {validatePicksM.isPending ? (
                    'Validando…'
                  ) : (
                    (() => {
                      const tag = validateSofaTag(board.validate_window?.phase)
                      return (
                        <>
                          <span>Validar vs SofaScore</span>
                          {tag ? (
                            <span className="rounded-full border border-violet-300/80 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-900">
                              {tag}
                            </span>
                          ) : null}
                        </>
                      )
                    })()
                  )}
                </button>
              </div>
              {validateFlash ? (
                <div className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-app-line bg-white px-3 py-2 text-[11px] text-app-fg">
                  <span className="min-w-0 flex-1 whitespace-pre-wrap">{validateFlash}</span>
                  <button
                    type="button"
                    className="shrink-0 text-app-muted hover:text-app-fg"
                    onClick={() => setValidateFlash(null)}
                  >
                    Cerrar
                  </button>
                </div>
              ) : null}
            </div>
          </details>

          {board.picks.length === 0 ? (
            <p className="rounded-xl border border-dashed border-app-line bg-app-card p-8 text-center text-sm text-app-muted">
              Sin picks en este run (ejecuta persist_picks tras el análisis).
            </p>
          ) : (
            <>
              <div className="mb-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:items-end">
                <label className="block text-xs text-app-muted">
                  Buscar pick
                  <input
                    type="text"
                    value={pickQuery}
                    onChange={(e) => setPickQuery(e.target.value)}
                    placeholder="pick_id, event_id, jugador, mercado, confianza..."
                    className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-1.5 text-xs text-app-fg shadow-sm"
                  />
                </label>
                <label className="block text-xs text-app-muted">
                  Confianza del modelo
                  <select
                    value={confidenceFilter}
                    onChange={(e) => setConfidenceFilter(e.target.value)}
                    className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-1.5 text-xs text-app-fg shadow-sm"
                  >
                    <option value="">Todas</option>
                    <option value="Alta">Alta</option>
                    <option value="Media-Alta">Media-Alta</option>
                    <option value="Media">Media</option>
                    <option value="Baja">Baja</option>
                    <option value="__sin__">Sin etiqueta</option>
                  </select>
                </label>
                <label className="block text-xs text-app-muted">
                  Estado del pick
                  <select
                    value={outcomeFilter}
                    onChange={(e) =>
                      setOutcomeFilter(e.target.value as typeof outcomeFilter)
                    }
                    className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-1.5 text-xs text-app-fg shadow-sm"
                  >
                    <option value="all">Todos</option>
                    <option value="win">Ganada</option>
                    <option value="loss">Perdida</option>
                    <option value="pending">Pendiente</option>
                  </select>
                </label>
                <div className="text-xs text-app-muted">
                  <span className="block">Orden de la lista</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <button
                      type="button"
                      className={`rounded-md border px-2.5 py-1.5 text-[11px] font-medium shadow-sm ${
                        pickSortMode === 'confidence'
                          ? 'border-violet-300 bg-violet-100 text-violet-950'
                          : 'border-app-line bg-white text-app-muted hover:bg-violet-50/50'
                      }`}
                      onClick={() => setPickSortMode('confidence')}
                    >
                      Confianza
                    </button>
                    <button
                      type="button"
                      className={`rounded-md border px-2.5 py-1.5 text-[11px] font-medium shadow-sm ${
                        pickSortMode === 'kickoff'
                          ? 'border-violet-300 bg-violet-100 text-violet-950'
                          : 'border-app-line bg-white text-app-muted hover:bg-violet-50/50'
                      }`}
                      onClick={() => setPickSortMode('kickoff')}
                    >
                      Hora del partido
                    </button>
                  </div>
                </div>
              </div>
              <p className="mb-2 text-[11px] text-app-muted">
                Filtrados:{' '}
                <span className="font-mono text-app-fg">{picksFiltered.length}</span>
                {' · total run: '}
                <span className="font-mono text-app-fg">{picksOrdered.length}</span>
              </p>
              <ListPagination
                className="mb-2"
                idPrefix="run-picks"
                page={pickPageSafe}
                pageSize={pickPageSize}
                total={pickTotal}
                onPageChange={setPickListPage}
                onPageSizeChange={setPickPageSize}
              />
              <CardExplain summary="Atajos en cada fila (sin abrir la ficha)" className="mb-2">
                <p>
                  En la columna derecha puedes marcar{' '}
                  <strong className="text-app-fg">Gané / Perdí / Pend.</strong> al vuelo. La ficha del pick sigue
                  siendo el lugar para tomar apuesta, monto y origen de la decisión.
                </p>
              </CardExplain>
              <div className="overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
                {picksPageSlice.map((p, i) => (
                <PickInboxRow
                  key={p.pick_id}
                  pickId={p.pick_id}
                  eventId={p.event_id}
                  href={`/picks/${p.pick_id}`}
                  eventLabel={p.event_label}
                  league={p.league}
                  market={p.market}
                  selection={p.selection}
                  pickedValue={p.picked_value}
                  kickoffDisplay={p.kickoff_display ?? null}
                  executionSlotLabelEs={p.execution_slot_label_es ?? null}
                  confidence={refStr(p.odds_reference as OddsRef, 'confianza') ?? null}
                  outcome={effectiveOutcome(p)}
                  userTaken={p.user_taken}
                  ordinal={pickPageSafe * pickPageSize + i + 1}
                  onQuickOutcome={
                    userId != null
                      ? (o) =>
                          quickOutcomeM.mutate({
                            pickId: p.pick_id,
                            dailyRunId: runId,
                            taken: p.user_taken ?? false,
                            outcome: o,
                          })
                      : undefined
                  }
                  quickOutcomePending={
                    quickOutcomeM.isPending &&
                    quickOutcomeM.variables?.pickId === p.pick_id
                  }
                  onQuickAutoOutcome={
                    userId != null
                      ? () =>
                          quickAutoOutcomeM.mutate({
                            pickId: p.pick_id,
                            dailyRunId: runId,
                            taken: p.user_taken ?? false,
                          })
                      : undefined
                  }
                  quickAutoOutcomePending={
                    quickAutoOutcomeM.isPending &&
                    quickAutoOutcomeM.variables?.pickId === p.pick_id
                  }
                />
                ))}
              </div>
            </>
          )}

          {picksStats && picksStatsTotal > 0 ? (
            <div className="mt-8 rounded-xl border border-violet-200/40 bg-app-card px-3 py-3 shadow-sm">
              <p className="font-serif text-sm font-medium tracking-tight text-app-fg">
                Modelo vs lista en este run
              </p>
              <CardExplain summary="Qué contrasta este bloque con la lista de arriba" className="mt-1">
                <p>
                  El modelo puede generar más picks de los que ves en esta pantalla. Aquí se reparte el total emitido
                  entre lo que cumple la <strong className="text-app-fg">cuota mínima</strong> del día (lista operativa,
                  la misma que estás recorriendo) y el resto en <strong className="text-app-fg">solo análisis</strong>,
                  que no aparece como fila operativa pero sigue contando para el modelo.
                </p>
                <p className="mt-2">
                  Misma lógica que el resumen del día en el dashboard; aquí acotado a este run.
                </p>
              </CardExplain>
              <details className="mt-2 rounded-lg border border-violet-200/50 bg-violet-50/40 px-3 py-2 text-[11px] leading-relaxed text-app-muted">
                <summary className="flex cursor-pointer list-none items-center gap-1.5 font-medium text-violet-950 [list-style:none] [&::-webkit-details-marker]:hidden">
                  <HelpCueIcon />
                  <span>
                    Detalle: umbral {picksStats.min_tradable_odds} y lista ejecutable
                  </span>
                </summary>
                <p className="mt-2 border-t border-violet-100 pt-2">
                  Pick con cuota de referencia ≥ <span className="font-mono text-app-fg">{picksStats.min_tradable_odds}</span> entra en la lista de arriba; por debajo cuenta como generado pero no como fila operativa en este tablero.
                </p>
              </details>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div className="rounded border border-app-line bg-white px-2 py-1.5">
                  <p className="text-[10px] uppercase tracking-wide text-app-muted">Generados (modelo)</p>
                  <p className="font-mono text-sm text-app-fg">{picksStats.total_generated}</p>
                  <p className="mt-0.5 text-[9px] text-app-muted">Operativos + solo análisis</p>
                </div>
                <div className="rounded border border-emerald-200 bg-emerald-50/60 px-2 py-1.5">
                  <p className="text-[10px] uppercase tracking-wide text-app-muted">Listos para operar</p>
                  <p className="font-mono text-sm text-emerald-800">
                    {picksStats.tradable_visible}{' '}
                    <span className="text-[11px]">({picksStatsTradablePct}%)</span>
                  </p>
                  <p className="mt-0.5 text-[9px] text-app-muted">En este tablero</p>
                </div>
                <div className="rounded border border-amber-200 bg-amber-50/60 px-2 py-1.5">
                  <p className="text-[10px] uppercase tracking-wide text-app-muted">Solo análisis</p>
                  <p className="font-mono text-sm text-amber-800">
                    {picksStats.hidden_non_tradable}{' '}
                    <span className="text-[11px]">({picksStatsAnalysisPct}%)</span>
                  </p>
                  <p className="mt-0.5 text-[9px] text-app-muted">
                    Contados, no en lista operativa
                  </p>
                </div>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full border border-app-line bg-app-card">
                <div
                  className="h-full bg-emerald-500/80"
                  style={{ width: `${picksStatsTradablePct}%` }}
                />
              </div>
              <CardExplain summary="Leyenda de la barra" className="mt-2">
                <p>
                  Parte verde: proporción del total generado que cumple el mínimo de cuota y coincide con las filas
                  operativas del tablero; el gris es solo análisis.
                </p>
              </CardExplain>
            </div>
          ) : null}

          <div className="mb-1 mt-10 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-lg font-semibold tracking-tight text-violet-950">
              Combinadas sugeridas
            </h3>
            <button
              type="button"
              className="self-start rounded-md border border-violet-200 bg-violet-50 px-3 py-1.5 text-[11px] font-medium text-violet-950 shadow-sm hover:bg-violet-100"
              onClick={() => setShowCombosSection((v) => !v)}
            >
              {showCombosSection ? 'Ocultar combinadas' : 'Mostrar combinadas'}
            </button>
          </div>
          {showCombosSection ? (
            <>
              <p className="mb-5 max-w-xl text-xs leading-relaxed text-app-muted">
                Parlays armados con reglas automáticas (ver nota en cada combo).
                Cada pierna enlaza a su ficha. Si una pierna pierde, la combinada
                pierde: el estado por pierna y el resumen «por piernas» abajo lo
                reflejan.
              </p>
              {board.suggested_combos.length === 0 ? (
                <p className="text-xs text-app-muted">
                  Pulsa «Regenerar combinadas».
                </p>
              ) : (
                <ul className="space-y-5">
                  {board.suggested_combos.map((c) => (
                    <li key={c.suggested_combo_id} className="group relative">
                      <div className="rounded-2xl border border-violet-200/70 bg-app-card p-4 shadow-sm">
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
                            {c.legs.map((leg, idx) => {
                              const lo = legOutcomeShort(leg.leg_outcome)
                              const showAnalysis =
                                leg.operativo_visible === false
                              return (
                                <li key={leg.pick_id}>
                                  <Link
                                    to={`/picks/${leg.pick_id}`}
                                    className="flex items-start gap-3 rounded-xl border border-sky-100 bg-gradient-to-r from-sky-50/80 to-white px-3 py-2 text-xs transition-colors hover:border-sky-300 hover:from-sky-50"
                                  >
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-600 text-[10px] font-bold text-white">
                                      {idx + 1}
                                    </span>
                                    <div className="min-w-0 flex-1">
                                      <div className="flex flex-wrap items-center gap-1.5">
                                        <p className="font-mono text-[10px] text-app-muted">
                                          pick {leg.pick_id} · event{' '}
                                          {leg.event_id}
                                          {leg.picked_value != null && leg.picked_value > 0
                                            ? ` · @${Number(leg.picked_value).toFixed(2)}`
                                            : ''}
                                        </p>
                                        <span
                                          className={`inline-flex rounded-full border px-1.5 py-0.5 text-[9px] font-semibold ${lo.className}`}
                                        >
                                          {lo.label}
                                        </span>
                                        {showAnalysis ? (
                                          <span className="inline-flex rounded-full border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[9px] font-medium text-amber-950">
                                            Solo análisis (no en lista)
                                          </span>
                                        ) : null}
                                      </div>
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
                              )
                            })}
                          </ol>
                          <ComboTrackingControls
                            key={`${c.suggested_combo_id}-${c.user_stake_amount ?? ''}`}
                            combo={c}
                            bankrollCOP={bankrollCOP}
                            disabled={saveComboM.isPending}
                            onSave={(payload) => saveComboM.mutate(payload)}
                          />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="mb-5 text-[11px] text-app-muted">
              Sección oculta para reducir ruido. Pulsa «Mostrar combinadas» cuando
              quieras verlas de nuevo (se recuerda en este navegador).
            </p>
          )}
        </>
      )}
    </div>
  )
}
