import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { useBankrollStore } from '@/store/useBankrollStore'

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
}

export type SessionStoreActions = {
  isStationLocked: () => boolean
  closeStationAndFinalizeDay: (input: {
    exchangeCop: number
    projectedCop: number
    dailyReflection: string
    discrepancyNote?: string
    settlementsTodayCount: number
  }) => CloseStationResult
  /** Solo tests / soporte */
  reset: () => void
}

export type SessionStore = SessionStoreState & SessionStoreActions

const initial: SessionStoreState = {
  stationLockedUntilIso: null,
  lastCloseSummary: null,
}

export function selectStationLocked(s: SessionStoreState): boolean {
  const until = s.stationLockedUntilIso
  if (!until) return false
  return new Date(until).getTime() > Date.now()
}

export const useSessionStore = create<SessionStore>()(
  persist(
    (set, get) => ({
      ...initial,
      isStationLocked: () => {
        const until = get().stationLockedUntilIso
        if (!until) return false
        return new Date(until).getTime() > Date.now()
      },
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
        set({
          stationLockedUntilIso: untilIso,
          lastCloseSummary: summary,
        })
        console.info(
          `[BT2] Estación cerrada hasta ${untilIso} · ${status} · disciplina ${disciplineScore}`,
        )
        return { ok: true, summary }
      },
      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_session',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
