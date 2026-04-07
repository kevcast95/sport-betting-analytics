/**
 * US-FE-006 / US-FE-028 (Sprint 04): ledger de liquidaciones.
 * - finalizeSettlement: flujo local (mock picks, modo trust local).
 * - settleApiPick: flujo real vía POST /bt2/picks/{id}/settle.
 * - earnedDp proviene del servidor (D-04-011: +10 won, +5 lost, 0 void).
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import { vaultMockPicks } from '@/data/vaultMockPicks'
import type { SettlementOutcome } from '@/lib/settlementPnL'
import { computeSettlementPnlCop } from '@/lib/settlementPnL'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'
import { bt2FetchJson } from '@/lib/api'
import type { Bt2SettleOut } from '@/lib/bt2Types'

/** D-04-011: recompensa local para flujo mock (sin API). */
const SETTLEMENT_DP_REWARD_WON = 10
const SETTLEMENT_DP_REWARD_LOST = 5

export type LedgerRow = {
  pickId: string
  /** US-FE-008: protocolo CDM (clase de mercado). */
  marketClass?: string
  titulo?: string
  /** Etiqueta de evento (US-FE-022). */
  eventLabel?: string
  /** Selección concreta de la apuesta en español (US-FE-024). */
  selectionSummaryEs?: string
  outcome: SettlementOutcome
  reflection: string
  pnlCop: number
  stakeCop: number
  /** Cuota usada para calcular el PnL (puede ser cuota casa si fue capturada). */
  decimalCuota: number
  /** Cuota sugerida por el sistema CDM (US-FE-022). */
  suggestedDecimalOdds?: number
  /** Cuota real capturada en la casa del operador (US-FE-022 T-057). */
  bookDecimalOdds?: number
  settledAt: string
  /** DP ganados por liquidación (D-04-011: +10 won, +5 lost, 0 void). */
  earnedDp?: number
  /** bt2_picks.id del servidor (US-FE-028; null para picks mock). */
  bt2PickId?: number
}

export type FinalizeSettlementResult =
  | { ok: true; earnedDp: number }
  | {
      ok: false
      reason:
        | 'already_settled'
        | 'pick_locked'
        | 'invalid_reflection'
        | 'invalid_amounts'
        | 'station_locked'
        | 'api_error'
    }

export type TradeStoreState = {
  settledPickIds: string[]
  ledger: LedgerRow[]
}

export type TradeStoreActions = {
  isSettled: (pickId: string) => boolean
  /** Flujo local (mock picks): finalización sin llamada API. */
  finalizeSettlement: (input: {
    pickId: string
    outcome: SettlementOutcome
    reflection: string
    stakeCop: number
    decimalCuota: number
    bookDecimalOdds?: number
  }) => FinalizeSettlementResult
  /**
   * US-FE-028: Flujo API. Llama POST /bt2/picks/{bt2PickId}/settle y persiste
   * el resultado desde la respuesta del servidor.
   * Debe llamarse solo cuando el pick tiene bt2PickId (fue tomado vía API).
   */
  settleApiPick: (input: {
    vaultPickId: string
    bt2PickId: number
    outcome: SettlementOutcome
    reflection: string
    stakeCop: number
    decimalCuota: number
    bookDecimalOdds?: number
    market: string
    selection: string
  }) => Promise<FinalizeSettlementResult>
  reset: () => void
}

export type TradeStore = TradeStoreState & TradeStoreActions

const initial: TradeStoreState = {
  settledPickIds: [],
  ledger: [],
}

/** D-04-011: mapea outcome local a delta DP (flujo mock sin API). */
function earnDpForOutcome(outcome: SettlementOutcome): number {
  if (outcome === 'PROFIT') return SETTLEMENT_DP_REWARD_WON
  if (outcome === 'LOSS') return SETTLEMENT_DP_REWARD_LOST
  return 0
}

/**
 * US-FE-028 (D-04-FE-001): mapa simplificado de outcome a scores para trust mode.
 * PUSH → scores neutros (el servidor puede computar como lost para algunos mercados;
 * limitación documentada en DECISIONES.md Sprint 04).
 */
function outcomeToScores(
  market: string,
  selection: string,
  outcome: SettlementOutcome,
): { result_home: number; result_away: number } {
  if (outcome === 'PUSH') return { result_home: 0, result_away: 0 }
  const m = market.toUpperCase()
  const s = selection.trim().toLowerCase()
  const won = outcome === 'PROFIT'

  if (m.includes('1X2') || m.includes('ML_SIDE') || m.includes('ML_HOME') || m.includes('ML_AWAY') || m.includes('MATCH WINNER') || m.includes('WINNER')) {
    if (['1', 'home', 'local'].some((k) => s.includes(k))) {
      return won ? { result_home: 2, result_away: 0 } : { result_home: 0, result_away: 2 }
    }
    if (['2', 'away', 'visitante'].some((k) => s.includes(k))) {
      return won ? { result_home: 0, result_away: 2 } : { result_home: 2, result_away: 0 }
    }
    if (['x', 'draw', 'empate'].some((k) => s.includes(k))) {
      return won ? { result_home: 1, result_away: 1 } : { result_home: 2, result_away: 0 }
    }
    return won ? { result_home: 2, result_away: 0 } : { result_home: 0, result_away: 2 }
  }

  if (m.includes('TOTAL') || m.includes('OVER') || m.includes('UNDER') || m.includes('ML_TOTAL') || m.includes('TOTAL_OVER') || m.includes('TOTAL_UNDER')) {
    const numMatch = s.match(/(\d+\.?\d*)/)
    const threshold = numMatch ? parseFloat(numMatch[1]) : 2.5
    if (s.includes('over') || s.includes('más') || m.includes('TOTAL_OVER')) {
      const total = Math.floor(threshold) + 1
      return won
        ? { result_home: Math.ceil(total / 2), result_away: Math.floor(total / 2) }
        : { result_home: 0, result_away: 0 }
    }
    if (s.includes('under') || s.includes('menos') || m.includes('TOTAL_UNDER')) {
      return won
        ? { result_home: 0, result_away: Math.max(0, Math.floor(threshold) - 1) }
        : { result_home: Math.ceil(threshold / 2) + 1, result_away: Math.ceil(threshold / 2) + 1 }
    }
    return won ? { result_home: 2, result_away: 0 } : { result_home: 0, result_away: 3 }
  }

  // Fallback genérico
  return won ? { result_home: 2, result_away: 0 } : { result_home: 0, result_away: 2 }
}

export const useTradeStore = create<TradeStore>()(
  persist(
    (set, get) => ({
      ...initial,
      isSettled: (pickId) => get().settledPickIds.includes(pickId),

      finalizeSettlement: (input) => {
        if (useSessionStore.getState().isStationLocked()) {
          return { ok: false, reason: 'station_locked' }
        }
        const reflection = input.reflection.trim()
        if (reflection.length < 10) {
          return { ok: false, reason: 'invalid_reflection' }
        }
        if (get().settledPickIds.includes(input.pickId)) {
          return { ok: false, reason: 'already_settled' }
        }
        if (!useVaultStore.getState().isUnlocked(input.pickId)) {
          return { ok: false, reason: 'pick_locked' }
        }
        const pnl = computeSettlementPnlCop(
          input.stakeCop,
          input.decimalCuota,
          input.outcome,
        )
        if (!Number.isFinite(pnl)) {
          return { ok: false, reason: 'invalid_amounts' }
        }
        const meta = vaultMockPicks.find((p) => p.id === input.pickId)
        const dpEarned = earnDpForOutcome(input.outcome)
        const row: LedgerRow = {
          pickId: input.pickId,
          marketClass: meta?.marketClass ?? 'CDM',
          titulo: meta?.titulo ?? input.pickId,
          eventLabel: meta?.eventLabel,
          selectionSummaryEs: meta?.selectionSummaryEs,
          outcome: input.outcome,
          reflection,
          pnlCop: pnl,
          stakeCop: input.stakeCop,
          decimalCuota: input.decimalCuota,
          suggestedDecimalOdds: meta?.suggestedDecimalOdds,
          bookDecimalOdds: input.bookDecimalOdds,
          settledAt: new Date().toISOString(),
          earnedDp: dpEarned,
        }
        useBankrollStore.getState().applyBankrollDelta(pnl)
        useUserStore.getState().incrementDisciplinePoints(dpEarned)
        set((s) => ({
          settledPickIds: [...s.settledPickIds, input.pickId],
          ledger: [...s.ledger, row],
        }))
        console.info(
          `[BT2] Liquidación (local): ${input.pickId} · PnL ${pnl} COP · +${dpEarned} DP`,
        )
        return { ok: true, earnedDp: dpEarned }
      },

      settleApiPick: async (input) => {
        if (get().settledPickIds.includes(input.vaultPickId)) {
          return { ok: false, reason: 'already_settled' }
        }
        const reflection = input.reflection.trim()
        if (reflection.length < 10) {
          return { ok: false, reason: 'invalid_reflection' }
        }

        const scores = outcomeToScores(input.market, input.selection, input.outcome)

        try {
          const res = await bt2FetchJson<Bt2SettleOut>(
            `/bt2/picks/${input.bt2PickId}/settle`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(scores),
            },
          )

          // Actualizar bankroll desde respuesta servidor
          if (res.bankroll_after_units != null) {
            useBankrollStore.getState().reconcileToExchangeBalance(res.bankroll_after_units)
          } else {
            // Fallback: aplicar delta local
            const pnlCop = computeSettlementPnlCop(input.stakeCop, input.decimalCuota, input.outcome)
            useBankrollStore.getState().applyBankrollDelta(pnlCop)
          }

          // Actualizar DP desde respuesta servidor
          const earnedDp = res.earned_dp ?? 0
          useUserStore.getState().setDisciplinePoints(res.dp_balance_after ?? useUserStore.getState().disciplinePoints + earnedDp)

          const pnlCop = res.pnl_units != null
            ? res.pnl_units
            : computeSettlementPnlCop(input.stakeCop, input.decimalCuota, input.outcome)

          // Buscar metadata del vault pick en la store
          const vaultPick = useVaultStore.getState().apiPicks.find((p) => p.id === input.vaultPickId)

          const row: LedgerRow = {
            pickId: input.vaultPickId,
            marketClass: vaultPick?.marketClass ?? input.market,
            titulo: vaultPick?.titulo ?? input.selection,
            eventLabel: vaultPick?.eventLabel,
            selectionSummaryEs: vaultPick?.selectionSummaryEs ?? input.selection,
            outcome: input.outcome,
            reflection,
            pnlCop: typeof pnlCop === 'number' ? pnlCop : 0,
            stakeCop: input.stakeCop,
            decimalCuota: input.decimalCuota,
            suggestedDecimalOdds: vaultPick?.suggestedDecimalOdds,
            bookDecimalOdds: input.bookDecimalOdds,
            settledAt: new Date().toISOString(),
            earnedDp,
            bt2PickId: input.bt2PickId,
          }

          set((s) => ({
            settledPickIds: [...s.settledPickIds, input.vaultPickId],
            ledger: [...s.ledger, row],
          }))

          console.info(
            `[BT2] Liquidación (API): ${input.vaultPickId} → bt2PickId=${input.bt2PickId} · status=${res.status} · +${earnedDp} DP`,
          )
          return { ok: true, earnedDp }
        } catch (e) {
          const msg = e instanceof Error ? e.message : ''
          if (msg.includes('409')) {
            // Pick ya liquidado en servidor → marcar localmente y evitar duplicado
            set((s) => ({
              settledPickIds: s.settledPickIds.includes(input.vaultPickId)
                ? s.settledPickIds
                : [...s.settledPickIds, input.vaultPickId],
            }))
            return { ok: false, reason: 'already_settled' }
          }
          console.error('[BT2] settleApiPick error:', e)
          return { ok: false, reason: 'api_error' }
        }
      },

      reset: () => set(initial),
    }),
    {
      name: 'bt2_v2_trades',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
