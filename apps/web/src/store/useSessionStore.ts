import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useUserStore } from '@/store/useUserStore'
import { bt2FetchJson } from '@/lib/api'
import type { Bt2SessionDayOut, Bt2TakenPickRecord } from '@/lib/bt2Types'
import {
  getOperatingDayKey,
  graceExpiresIso,
  isGraceExpired,
  type DayKey,
} from '@/lib/operatingDay'

export type ReconciliationStatus = 'PERFECT_MATCH' | 'DISCREPANCY'

export type DailyCloseSummary = {
  at: string
  exchangeCop: number
  projectedCop: number
  status: ReconciliationStatus
  disciplineScore: number
  dailyReflection: string
  discrepancyNote?: string
}

/** US-FE-012: ítem pendiente detectado al cambiar de día. */
export type PreviousDayItem = 'UNSETTLED_PICK' | 'STATION_UNCLOSED'

/**
 * US-FE-012 / US-FE-044: penalización conductual aplicada tras expirar la gracia.
 *
 * Tabla de consecuencias (DECISIONES.md 2026-04-04):
 * - STATION_UNCLOSED → -50 DP solo si hubo picks tomados ese día (servidor alinea).
 * - UNSETTLED_PICKS  → -50 DP por picks sin liquidar tras gracia.
 */
export type PenaltyRecord = {
  appliedAt: string
  dayKey: DayKey
  reason: 'grace_expired_station_unclosed' | 'grace_expired_unsettled_picks'
  dpPenalty: number
  description: string
}

/**
 * Matriz de bloqueo de estación (US-FE-014):
 *
 * | Condición                                      | ¿Estación bloqueada? |
 * |------------------------------------------------|----------------------|
 * | stationLockedUntilIso en el futuro + mismo día | Sí                   |
 * | stationLockedUntilIso en el pasado             | No                   |
 * | Nuevo día calendario (closedForDayKey ≠ hoy)   | No (nuevo día)       |
 * | Sin cierre registrado                          | No                   |
 */

const LOCK_MS = 24 * 60 * 60 * 1000

function discrepancyPercent(
  exchangeCop: number,
  projectedCop: number,
): number {
  const base = Math.max(projectedCop, 1)
  return (Math.abs(exchangeCop - projectedCop) / base) * 100
}

function hadBt2PicksOnOperatingDay(
  picks: Bt2TakenPickRecord[],
  dayKey: DayKey,
): boolean {
  return picks.some((p) => {
    if (p.operatingDayKey && p.operatingDayKey === dayKey) return true
    const head = (p.openedAt || '').slice(0, 10)
    return head === dayKey
  })
}

function computeDisciplineScore(
  status: ReconciliationStatus,
  settlementsToday: number,
  reflectionLen: number,
): number {
  let s = 52
  s += Math.min(38, settlementsToday * 9)
  if (status === 'PERFECT_MATCH') s += 6
  if (reflectionLen >= 24) s += 4
  return Math.min(100, Math.round(s))
}

export type CloseStationResult =
  | { ok: true; summary: DailyCloseSummary }
  | { ok: false; reason: 'note_required_for_discrepancy' | 'invalid_input' }

export type SessionStoreState = {
  stationLockedUntilIso: string | null
  lastCloseSummary: DailyCloseSummary | null
  /**
   * US-FE-012: día operativo actual en TZ del usuario (YYYY-MM-DD).
   * null hasta el primer `checkDayBoundary`.
   */
  operatingDayKey: DayKey | null
  /**
   * US-FE-014: día operativo en que se cerró la estación.
   * Permite distinguir si `stationLockedUntilIso` pertenece al día actual o al anterior.
   */
  closedForDayKey: DayKey | null
  /**
   * US-FE-012: ISO8601 hasta cuando aplica la gracia del día anterior.
   * null si no hay gracia activa o ya expiró.
   */
  graceActiveUntilIso: string | null
  /**
   * US-FE-012: ítems pendientes del día anterior detectados al cambiar de día.
   * Se vacían al aplicar penalizaciones o al completar los ítems.
   */
  previousDayPendingItems: PreviousDayItem[]
  /** US-FE-012 / T-044: registro auditado de penalizaciones aplicadas. */
  penaltiesApplied: PenaltyRecord[]
  /**
   * GET /bt2/session/day (T-184): liquidaciones pendientes del día anterior en servidor.
   */
  sessionPendingPrevDaySettlements: number | null
  /** GET /bt2/session/day: estación ya cerrada para el día operativo actual. */
  sessionStationClosedToday: boolean | null
}

export type SessionStoreActions = {
  /**
   * US-FE-014: selectStationLocked encapsulado como acción (para usos fuera de React).
   * En React, preferir `useSessionStore(selectStationLocked)`.
   */
  isStationLocked: () => boolean
  closeStationAndFinalizeDay: (input: {
    exchangeCop: number
    projectedCop: number
    dailyReflection: string
    discrepancyNote?: string
    settlementsTodayCount: number
  }) => CloseStationResult
  /**
   * US-FE-012: evalúa el cambio de día operativo.
   * Llámalo al montar la app y en heartbeat razonable (~1 min).
   *
   * @param nowIso ISO8601 del momento actual (inyectable para tests).
   * @param hasUnsettledPicks  true si hay picks activos sin liquidar del día anterior.
   * @param takenApiPicks  picks tomados vía API; sin picks ese día no hay pendiente STATION_UNCLOSED.
   */
  checkDayBoundary: (
    nowIso: string,
    hasUnsettledPicks: boolean,
    takenApiPicks?: Bt2TakenPickRecord[],
  ) => void
  /**
   * US-FE-027: hidrata el store desde GET /bt2/session/day.
   * Sincroniza operatingDayKey, graceActiveUntilIso y stationLockedForOperatingDay.
   */
  hydrateFromApi: () => Promise<void>
  /** Solo tests / soporte */
  reset: () => void
}

export type SessionStore = SessionStoreState & SessionStoreActions

const initial: SessionStoreState = {
  stationLockedUntilIso: null,
  lastCloseSummary: null,
  operatingDayKey: null,
  closedForDayKey: null,
  graceActiveUntilIso: null,
  previousDayPendingItems: [],
  penaltiesApplied: [],
  sessionPendingPrevDaySettlements: null,
  sessionStationClosedToday: null,
}

/**
 * US-FE-007 / US-FE-014: selector de estación bloqueada.
 *
 * Coherencia con día calendario (US-FE-014):
 * - Si el `closedForDayKey` no coincide con el `operatingDayKey` actual,
 *   el bloqueo del día anterior NO bloquea el nuevo día.
 */
export function selectStationLocked(s: SessionStoreState): boolean {
  const until = s.stationLockedUntilIso
  if (!until) return false
  const isTimeValid = new Date(until).getTime() > Date.now()
  if (!isTimeValid) return false
  // US-FE-014: bloqueo de día anterior no aplica al nuevo día calendario
  if (
    s.operatingDayKey &&
    s.closedForDayKey &&
    s.closedForDayKey !== s.operatingDayKey
  ) {
    return false
  }
  return true
}

export const useSessionStore = create<SessionStore>()(
  persist(
    (set, get) => ({
      ...initial,
      isStationLocked: () => selectStationLocked(get()),
      closeStationAndFinalizeDay: (input) => {
        const reflection = input.dailyReflection.trim()
        if (!Number.isFinite(input.exchangeCop) || input.exchangeCop < 0) {
          return { ok: false, reason: 'invalid_input' }
        }
        if (!Number.isFinite(input.projectedCop) || input.projectedCop < 0) {
          return { ok: false, reason: 'invalid_input' }
        }
        if (reflection.length < 8) {
          return { ok: false, reason: 'invalid_input' }
        }
        const diffPct = discrepancyPercent(input.exchangeCop, input.projectedCop)
        const status: ReconciliationStatus =
          diffPct > 1 ? 'DISCREPANCY' : 'PERFECT_MATCH'
        if (diffPct > 1) {
          const note = (input.discrepancyNote ?? '').trim()
          if (note.length < 6) {
            return { ok: false, reason: 'note_required_for_discrepancy' }
          }
        }
        const disciplineScore = computeDisciplineScore(
          status,
          Math.max(0, Math.floor(input.settlementsTodayCount)),
          reflection.length,
        )
        const summary: DailyCloseSummary = {
          at: new Date().toISOString(),
          exchangeCop: input.exchangeCop,
          projectedCop: input.projectedCop,
          status,
          disciplineScore,
          dailyReflection: reflection,
          discrepancyNote:
            diffPct > 1 ? (input.discrepancyNote ?? '').trim() : undefined,
        }
        useBankrollStore
          .getState()
          .reconcileToExchangeBalance(input.exchangeCop)
        const untilIso = new Date(Date.now() + LOCK_MS).toISOString()
        // US-FE-014: registrar el día en que se cerró la estación
        const dayKey = get().operatingDayKey ?? getOperatingDayKey()
        set({
          stationLockedUntilIso: untilIso,
          lastCloseSummary: summary,
          closedForDayKey: dayKey,
          // Al cerrar correctamente, limpiar ítems pendientes del día anterior
          previousDayPendingItems: get().previousDayPendingItems.filter(
            (i) => i !== 'STATION_UNCLOSED',
          ),
        })
        console.info(
          `[BT2] Estación cerrada hasta ${untilIso} · ${status} · disciplina ${disciplineScore} · día ${dayKey}`,
        )
        return { ok: true, summary }
      },
      checkDayBoundary: (nowIso, hasUnsettledPicks, takenApiPicks = []) => {
        const currentDayKey = getOperatingDayKey(nowIso)
        const state = get()
        const prevDayKey = state.operatingDayKey

        // Primer uso: inicializar el día operativo sin aplicar lógica de cambio
        if (!prevDayKey) {
          set({ operatingDayKey: currentDayKey })
          console.info(`[BT2] Día operativo inicializado: ${currentDayKey}`)
          return
        }

        // Sin cambio de día: revisar si la gracia vigente expiró
        if (prevDayKey === currentDayKey) {
          if (
            state.graceActiveUntilIso &&
            isGraceExpired(prevDayKey, nowIso) &&
            state.previousDayPendingItems.length > 0
          ) {
            // Aplicar penalizaciones por incumplimiento tras la gracia
            applyPenalties(set, get, prevDayKey, nowIso)
          }
          return
        }

        // CAMBIO DE DÍA detectado
        console.info(
          `[BT2] Cambio de día operativo: ${prevDayKey} → ${currentDayKey}`,
        )

        const pendingItems: PreviousDayItem[] = []
        const wasStationClosed = !!state.lastCloseSummary &&
          state.closedForDayKey === prevDayKey

        const hadPicksPrevDay = hadBt2PicksOnOperatingDay(takenApiPicks, prevDayKey)
        if (!wasStationClosed && hadPicksPrevDay) {
          pendingItems.push('STATION_UNCLOSED')
        }
        if (hasUnsettledPicks) {
          pendingItems.push('UNSETTLED_PICK')
        }

        if (pendingItems.length > 0) {
          // Iniciar ventana de gracia 24h (si no estaba ya activa)
          const grace = graceExpiresIso(prevDayKey)
          set({
            operatingDayKey: currentDayKey,
            previousDayPendingItems: pendingItems,
            graceActiveUntilIso: grace,
          })
          console.info(
            `[BT2] Día anterior con pendientes: [${pendingItems.join(', ')}] · gracia hasta ${grace}`,
          )

          // Si ya expiró la gracia (cambio de más de un día), aplicar penalizaciones
          if (isGraceExpired(prevDayKey, nowIso)) {
            applyPenalties(set, get, prevDayKey, nowIso)
          }
        } else {
          // Día anterior cerrado sin pendientes
          set({
            operatingDayKey: currentDayKey,
            previousDayPendingItems: [],
            graceActiveUntilIso: null,
          })
        }
      },
      hydrateFromApi: async () => {
        try {
          const data = await bt2FetchJson<Bt2SessionDayOut>('/bt2/session/day')
          const dayKey = data.operatingDayKey as DayKey
          set((s) => ({
            operatingDayKey: dayKey,
            graceActiveUntilIso: data.graceUntilIso ?? null,
            sessionPendingPrevDaySettlements:
              data.pendingSettlementsPreviousDay ?? null,
            sessionStationClosedToday: data.stationClosedForOperatingDay ?? null,
            // stationClosedForOperatingDay → si cerrada, stationLockedUntilIso se mantiene
            // No sobreescribir stationLockedUntilIso con data de API (se gestiona localmente)
            closedForDayKey: data.stationClosedForOperatingDay ? dayKey : s.closedForDayKey,
          }))
          console.info(`[BT2] Sesión del día sincronizada: ${dayKey}`)
        } catch (e) {
          console.warn('[BT2] hydrateFromApi session error:', e instanceof Error ? e.message : e)
        }
      },
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_session',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)

/**
 * US-FE-012 / Sprint 05: tras expirar la gracia, registra pendientes en `penaltiesApplied`.
 * Los cargos −50 DP (estación / picks sin liquidar, según caso) los aplica el servidor en `POST /bt2/session/open`
 * (penalty_station_unclosed, penalty_unsettled_picks); el cliente no llama a
 * `incrementDisciplinePoints` aquí.
 */
function applyPenalties(
  set: (partial: Partial<SessionStoreState>) => void,
  get: () => SessionStore,
  dayKey: DayKey,
  nowIso: string,
) {
  const state = get()
  if (!isGraceExpired(dayKey, nowIso)) return
  if (state.previousDayPendingItems.length === 0) return

  const newPenalties: PenaltyRecord[] = []

  if (state.previousDayPendingItems.includes('STATION_UNCLOSED')) {
    const record: PenaltyRecord = {
      appliedAt: nowIso,
      dayKey,
      reason: 'grace_expired_station_unclosed',
      dpPenalty: 50,
      description:
        'Estación del día anterior sin cerrar (hubo picks tomados ese día) tras la gracia. ' +
        'El servidor solo descuenta −50 DP en esa situación. Completa el After-Action Review.',
    }
    newPenalties.push(record)
    console.warn(
      `[BT2] Pendiente conductual registrado — estación sin cerrar · día ${dayKey} · la penalización DP la aplica el servidor en session/open (Sprint 05).`,
    )
  }

  if (state.previousDayPendingItems.includes('UNSETTLED_PICK')) {
    const record: PenaltyRecord = {
      appliedAt: nowIso,
      dayKey,
      reason: 'grace_expired_unsettled_picks',
      dpPenalty: 50,
      description:
        'Picks sin liquidar del día anterior tras la ventana de gracia (24 h). ' +
        'Penalización: -50 DP. Liquida los picks pendientes para mantener la integridad.',
    }
    newPenalties.push(record)
    console.warn(
      `[BT2] Pendiente conductual registrado — picks sin liquidar · día ${dayKey} · la penalización DP la aplica el servidor en session/open (Sprint 05).`,
    )
  }

  set({
    penaltiesApplied: [...state.penaltiesApplied, ...newPenalties],
    previousDayPendingItems: [],
    graceActiveUntilIso: null,
  })

  void useUserStore.getState().syncDpBalance()
}

/**
 * US-FE-012: tiempo restante de la gracia en milisegundos.
 * Retorna 0 si no hay gracia activa o ya expiró.
 */
export function selectGraceRemainingMs(
  s: SessionStoreState,
  nowMs?: number,
): number {
  if (!s.graceActiveUntilIso) return 0
  const remaining = new Date(s.graceActiveUntilIso).getTime() - (nowMs ?? Date.now())
  return Math.max(0, remaining)
}

/**
 * US-FE-012: true si hay ítems pendientes del día anterior Y la gracia sigue activa.
 */
export function selectHasPendingWithGrace(s: SessionStoreState): boolean {
  return (
    s.previousDayPendingItems.length > 0 &&
    s.graceActiveUntilIso !== null &&
    selectGraceRemainingMs(s) > 0
  )
}
