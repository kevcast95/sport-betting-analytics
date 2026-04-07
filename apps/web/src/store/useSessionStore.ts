import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useUserStore } from '@/store/useUserStore'
import {
  getOperatingDayKey,
  graceExpiresIso,
  isGraceExpired,
  isWithinGrace,
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
 * - STATION_UNCLOSED → -50 DP (pérdida del bono de cierre + penalización)
 * - UNSETTLED_PICKS  → -25 DP por día con picks sin liquidar
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
   */
  checkDayBoundary: (nowIso: string, hasUnsettledPicks: boolean) => void
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
      checkDayBoundary: (nowIso, hasUnsettledPicks) => {
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

        if (!wasStationClosed) {
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
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_session',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)

/**
 * US-FE-012 / T-044: aplica las penalizaciones conductuales tras expirar la gracia.
 *
 * Tabla (DECISIONES.md 2026-04-04):
 * - Estación sin cerrar   → -50 DP (pérdida del bono de cierre + penalización conductual)
 * - Picks sin liquidar    → -25 DP (por cada día con picks rezagados)
 *
 * Cada penalización queda auditada en `penaltiesApplied`.
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
        'Estación del día anterior sin cerrar tras la ventana de gracia (24 h). ' +
        'Penalización: -50 DP. Completa el After-Action Review para reanudar operativa.',
    }
    newPenalties.push(record)
    useUserStore.getState().incrementDisciplinePoints(-50)
    console.warn(
      `[BT2] Penalización aplicada — estación sin cerrar · día ${dayKey} · -50 DP`,
    )
  }

  if (state.previousDayPendingItems.includes('UNSETTLED_PICK')) {
    const record: PenaltyRecord = {
      appliedAt: nowIso,
      dayKey,
      reason: 'grace_expired_unsettled_picks',
      dpPenalty: 25,
      description:
        'Picks sin liquidar del día anterior tras la ventana de gracia (24 h). ' +
        'Penalización: -25 DP. Liquida los picks pendientes para mantener la integridad.',
    }
    newPenalties.push(record)
    useUserStore.getState().incrementDisciplinePoints(-25)
    console.warn(
      `[BT2] Penalización aplicada — picks sin liquidar · día ${dayKey} · -25 DP`,
    )
  }

  set({
    penaltiesApplied: [...state.penaltiesApplied, ...newPenalties],
    previousDayPendingItems: [],
    graceActiveUntilIso: null,
  })
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
