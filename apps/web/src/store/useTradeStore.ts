/**
 * US-FE-006 / US-FE-028 (Sprint 04): ledger de liquidaciones.
 * - finalizeSettlement: flujo local (mock picks, modo trust local).
 * - settleApiPick: flujo real vía POST /bt2/picks/{id}/settle.
 * - earnedDp desde API / mock alineado a US-BE-020: +10 DP por liquidación (won/lost/void).
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
import { parseBt2SettleOut } from '@/lib/bt2SettleParse'
import type { Bt2PicksListOut, Bt2PickOut } from '@/lib/bt2Types'

/** US-BE-020: misma recompensa DP en mock local que en servidor (+10 cualquier resultado). */
const SETTLEMENT_DP_REWARD = 10

export type LedgerRow = {
  pickId: string
  /** US-FE-008: protocolo CDM (clase de mercado). */
  marketClass?: string
  /** US-FE-054: etiqueta humana mercado canónico (API). */
  marketCanonicalLabelEs?: string
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
  /** DP ganados por liquidación (US-BE-020: +10 won/lost/void). */
  earnedDp?: number
  /** bt2_picks.id del servidor (US-FE-028; null para picks mock). */
  bt2PickId?: number
  /** Sprint 06 — resultado modelo tras liquidar (GET /bt2/picks). */
  modelPredictionResult?: string | null
  /**
   * Marca declarativa enviada al servidor (`PATCH .../user-result-claim`);
   * no confundir con `outcome` (liquidación / PnL).
   */
  userResultClaim?: string | null
  /** Estado en bt2_picks (`open`/`won`/…) para reabrir liquidación. */
  protocolPickStatus?: string
}

export type OpenPickSelfRow = {
  bt2PickId: number
  vaultPickId?: string
  eventLabel: string
  marketClass: string
  marketCanonicalLabelEs?: string
  selectionSummaryEs: string
  openedAt: string
  userResultClaim: string | null
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
  /** Picks aún abiertos: validación manual del operador (p. ej. sin CDM). */
  openPickSelfRows: OpenPickSelfRow[]
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
  /**
   * US-FE-032: hidrata ledger y settledPickIds desde GET /bt2/picks (servidor).
   * Conserva filas mock locales sin bt2PickId; sustituye por API si hay mismo bt2PickId.
   */
  hydrateLedgerFromApi: () => Promise<void>
  reset: () => void
}

export type TradeStore = TradeStoreState & TradeStoreActions

const initial: TradeStoreState = {
  settledPickIds: [],
  ledger: [],
  openPickSelfRows: [],
}

/** US-BE-020: +10 DP por liquidación en flujo mock (sin API). */
function earnDpForOutcome(_outcome: SettlementOutcome): number {
  return SETTLEMENT_DP_REWARD
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

function bt2PickStatusToOutcome(st: string): SettlementOutcome {
  if (st === 'won') return 'PROFIT'
  if (st === 'lost') return 'LOSS'
  return 'PUSH'
}

function bt2NumericPickId(p: Bt2PickOut): number {
  const ext = p as Bt2PickOut & { pickId?: number }
  if (typeof ext.pickId === 'number' && Number.isFinite(ext.pickId)) {
    return ext.pickId
  }
  return p.pick_id
}

function pickUserClaimFromBt2Pick(p: Bt2PickOut): string | null {
  const ext = p as Bt2PickOut & { user_result_claim?: string | null }
  const v = p.userResultClaim ?? ext.user_result_claim
  return v != null && String(v).trim() !== '' ? String(v) : null
}

function bt2PickToLedgerRow(
  p: Bt2PickOut,
  vaultPickId: string | undefined,
): LedgerRow {
  const numericId = bt2NumericPickId(p)
  const pickId = vaultPickId ?? `bt2-pick-${numericId}`
  const stakeCop = Number.isFinite(p.stake_units) ? p.stake_units : 0
  const pnlCop =
    p.pnl_units != null && Number.isFinite(p.pnl_units) ? p.pnl_units : 0
  return {
    pickId,
    marketClass: p.market,
    marketCanonicalLabelEs: p.marketCanonicalLabelEs ?? undefined,
    titulo: p.event_label,
    eventLabel: p.event_label,
    selectionSummaryEs: p.selection,
    outcome: bt2PickStatusToOutcome(p.status),
    reflection: 'Sincronizado desde el servidor',
    pnlCop,
    stakeCop,
    decimalCuota: p.odds_accepted,
    settledAt: p.settled_at ?? p.opened_at,
    earnedDp: p.earned_dp ?? 0,
    bt2PickId: numericId,
    modelPredictionResult: p.modelPredictionResult ?? null,
    userResultClaim: pickUserClaimFromBt2Pick(p),
    protocolPickStatus: p.status,
  }
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
        // Tras `reopen-settlement` el servidor deja el pick `open`, pero la lista local
        // puede seguir marcando liquidado hasta hidratar — sin esto bloqueamos POST /settle y no suman DP.
        try {
          await get().hydrateLedgerFromApi()
        } catch {
          /* best-effort */
        }
        if (get().settledPickIds.includes(input.vaultPickId)) {
          return { ok: false, reason: 'already_settled' }
        }
        const reflection = input.reflection.trim()
        if (reflection.length < 10) {
          return { ok: false, reason: 'invalid_reflection' }
        }

        const scores = outcomeToScores(input.market, input.selection, input.outcome)

        try {
          const raw = await bt2FetchJson<unknown>(
            `/bt2/picks/${input.bt2PickId}/settle`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(scores),
            },
          )
          const res = parseBt2SettleOut(raw)
          if (!res) {
            console.error('[BT2] settle: respuesta JSON inválida', raw)
            return { ok: false, reason: 'api_error' }
          }

          // Bankroll: prioridad servidor; 0 es válido (no usar truthiness).
          if (res.bankroll_after_units != null && Number.isFinite(res.bankroll_after_units)) {
            useBankrollStore.getState().reconcileToExchangeBalance(res.bankroll_after_units)
          } else {
            const pnlCop = computeSettlementPnlCop(input.stakeCop, input.decimalCuota, input.outcome)
            useBankrollStore.getState().applyBankrollDelta(pnlCop)
          }

          const earnedDp = res.earned_dp ?? 0
          // Solo fijar saldo si el servidor envió explícitamente dp_balance_after.
          // Antes: faltar el campo → parse devolvía 0 → setDisciplinePoints(0) borraba todo el saldo DP.
          if (
            res.dp_balance_after != null &&
            Number.isFinite(res.dp_balance_after)
          ) {
            useUserStore.getState().setDisciplinePoints(res.dp_balance_after)
          } else if (earnedDp !== 0) {
            useUserStore.getState().incrementDisciplinePoints(earnedDp)
          }

          const pnlCop = Number.isFinite(res.pnl_units)
            ? res.pnl_units
            : computeSettlementPnlCop(input.stakeCop, input.decimalCuota, input.outcome)

          // Buscar metadata del vault pick en la store
          const vaultPick = useVaultStore.getState().apiPicks.find((p) => p.id === input.vaultPickId)

          const row: LedgerRow = {
            pickId: input.vaultPickId,
            marketClass: vaultPick?.marketClass ?? input.market,
            marketCanonicalLabelEs: vaultPick?.marketCanonicalLabelEs,
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
          void get().hydrateLedgerFromApi()
          // Fuente de verdad servidor (evita drift si el shape del JSON varió).
          void useUserStore.getState().syncDpBalance()
          void useBankrollStore.getState().syncFromApi()
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

      hydrateLedgerFromApi: async () => {
        try {
          const data = await bt2FetchJson<Bt2PicksListOut>('/bt2/picks')
          const taken = useVaultStore.getState().takenApiPicks
          const byBt2 = new Map(
            taken.map((r) => [r.bt2PickId, r.vaultPickId] as const),
          )
          const settled = data.picks.filter((p) => p.status !== 'open')
          const apiLedger = settled.map((p) =>
            bt2PickToLedgerRow(p, byBt2.get(bt2NumericPickId(p))),
          )
          const openPickSelfRows: OpenPickSelfRow[] = data.picks
            .filter((p) => p.status === 'open')
            .map((p) => {
              const bid = bt2NumericPickId(p)
              return {
                bt2PickId: bid,
                vaultPickId: byBt2.get(bid),
                eventLabel: p.event_label,
                marketClass: p.market,
                marketCanonicalLabelEs:
                  p.marketCanonicalLabelEs ?? undefined,
                selectionSummaryEs: p.selection,
                openedAt: p.opened_at,
                userResultClaim: pickUserClaimFromBt2Pick(p),
              }
            })
          const apiBt2Ids = new Set(
            apiLedger.map((r) => r.bt2PickId).filter((x): x is number => x != null),
          )
          /** Tras `reopen-settlement` el pick vuelve a `open`: no conservar filas ledger persistidas con ese bt2 id. */
          const openBt2Ids = new Set(
            data.picks
              .filter((p) => p.status === 'open')
              .map((p) => bt2NumericPickId(p)),
          )
          const mockOnly = get().ledger.filter((r) => {
            if (r.bt2PickId != null && openBt2Ids.has(r.bt2PickId)) {
              return false
            }
            return r.bt2PickId == null || !apiBt2Ids.has(r.bt2PickId)
          })
          const merged = [...apiLedger, ...mockOnly]
          set({
            ledger: merged,
            settledPickIds: [...new Set(merged.map((r) => r.pickId))],
            openPickSelfRows,
          })
          console.info(`[BT2] Ledger hidratado desde API: ${apiLedger.length} filas`)
        } catch (e) {
          console.warn(
            '[BT2] hydrateLedgerFromApi:',
            e instanceof Error ? e.message : e,
          )
        }
      },

      reset: () =>
        set({
          settledPickIds: [],
          ledger: [],
          openPickSelfRows: [],
        }),
    }),
    {
      name: 'bt2_v2_trades',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
    },
  ),
)
