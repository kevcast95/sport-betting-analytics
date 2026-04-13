/**
 * US-FE-025 (Sprint 04): Bóveda desde API real.
 * - apiPicks: pool completo del día (hasta 20) tras session/open + GET /bt2/vault/picks.
 * - takenApiPicks: registro local de picks tomados (POST /bt2/picks).
 * - El tier "standard" equivale a "open" (libre sin DP).
 * - El tier "premium" requiere saldo DP ≥ unlockCostDp.
 * Se mantiene compatibilidad con picks mock (string IDs) para dev/tests.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { createBt2EncryptedLocalStorage } from '@/lib/bt2EncryptedStorage'
import {
  bt2FetchJson,
  bt2PostPickRegister,
  bt2PostVaultPremiumUnlock,
} from '@/lib/api'
import { useSessionStore } from '@/store/useSessionStore'
import { useUserStore } from '@/store/useUserStore'
import type {
  Bt2DpInsufficientPremiumDetail,
  Bt2VaultDaySnapshotMeta,
  Bt2VaultPickOut,
  Bt2VaultPicksPageOut,
  Bt2PickRegisterBody,
  Bt2TakenPickRecord,
} from '@/lib/bt2Types'
import {
  BT2_ERR_INSUFFICIENT_BANKROLL_STAKE,
  BT2_ERR_PICK_EVENT_KICKOFF_ELAPSED,
} from '@/lib/bt2VaultConstants'
import { isKickoffUtcInPast } from '@/lib/vaultKickoff'
import { computeVaultQuota } from '@/lib/vaultQuota'
import { computeUnitValue } from '@/lib/treasuryMath'
import { useBankrollStore } from '@/store/useBankrollStore'

export const VAULT_UNLOCK_COST_DP = 50

export type VaultUnlockResult =
  | { ok: true }
  | {
      ok: false
      reason:
        | 'insufficient_dp'
        | 'insufficient_dp_premium'
        | 'already_unlocked'
        | 'station_locked'
        | 'api_error'
        | 'pick_unavailable'
        | 'no_event_id'
        | 'not_premium'
        | 'pick_not_found'
        | 'premium_not_unlocked'
        | 'kickoff_elapsed'
        | 'quota_standard_exhausted'
        | 'quota_premium_exhausted'
        | 'insufficient_bankroll'
      /** D-05-005 — solo si reason === insufficient_dp_premium (402) */
      premiumDetail?: Bt2DpInsufficientPremiumDetail
      /** Mensaje servidor (422 kickoff, etc.) */
      apiMessage?: string
    }

export type VaultLoadStatus = 'idle' | 'loading' | 'loaded' | 'empty' | 'error'
export type SessionOpenStatus = 'idle' | 'opening' | 'open' | 'error'

export type VaultStoreState = {
  /** Mock unlock IDs (Sprint 01 compat — string pick IDs). */
  unlockedPickIds: string[]
  /** Picks del día desde API (US-FE-025). */
  apiPicks: Bt2VaultPickOut[]
  /** Picks tomados vía POST /bt2/picks (US-FE-025). */
  takenApiPicks: Bt2TakenPickRecord[]
  /** Estado de carga de picks. */
  picksLoadStatus: VaultLoadStatus
  /** Mensaje informativo del API (ej: "No hay eventos hoy"). */
  picksMessage: string | null
  /** Estado de apertura de sesión operativa. */
  sessionOpenStatus: SessionOpenStatus
  /**
   * T-169 / D-05-019: `operatingDayKey` del último snapshot GET /bt2/vault/picks
   * (primer pick o día de sesión si lista vacía). Anti-stale vs `useSessionStore.operatingDayKey`.
   */
  vaultSnapshotOperatingDayKey: string | null
  /** Sprint 05.2 — meta pool en última respuesta GET /bt2/vault/picks */
  vaultPoolMeta: {
    poolTargetCount: number
    poolHardCap: number
    /** D-06-032 — candidatos valor máx. antes del slate (típ. 20). */
    valuePoolUniverseMax?: number
    poolItemCount: number
    vaultUniversePersistedCount?: number
    slateBandCycle?: number
    poolBelowTarget: boolean
  } | null
  /** S6.1 — flags vacío operativo, degradación y conteos (US-BE-036 / T-184). */
  vaultDaySnapshotMeta: Bt2VaultDaySnapshotMeta | null
  /**
   * Ciclo 0–3 para priorizar franja horaria al **barajar en cliente** el pool ya cargado (GET único).
   * Se inicializa con `slateBandCycle` del API en `loadApiPicks`; «Regenerar cartelera» solo rota (+1 mod 4).
   */
  vaultLocalSlateCycle: number
}

export type VaultStoreActions = {
  /** Compatibilidad Sprint 01: verifica si un pick (string ID) está desbloqueado. */
  isUnlocked: (pickId: string) => boolean
  /** Compatibilidad Sprint 01: intenta desbloquear un pick mock. */
  tryUnlockPick: (pickId: string) => VaultUnlockResult
  /**
   * US-FE-025: abre sesión operativa (POST /bt2/session/open)
   * y luego carga picks del día (GET /bt2/vault/picks).
   */
  loadApiPicks: () => Promise<void>
  /**
   * Baraja el orden visible: rota ciclo 0–3 **solo en memoria** (sin segundo request; el pool viene del GET).
   */
  regenerateVaultSlate: () =>
    | { ok: true; cycle: number; poolSize: number }
    | { ok: false; message: string }
  /**
   * US-FE-025: "tomar" un pick de la API.
   * Para tier standard: registra el pick en bt2_picks (sin coste DP).
   * Para tier premium: requiere `premiumUnlocked` (POST /vault/premium-unlock); el servidor valida DP al tomar.
   */
  takeApiPick: (vaultPick: Bt2VaultPickOut) => Promise<VaultUnlockResult>
  /**
   * Sprint 05.1 / US-BE-029: cobra DP por desbloqueo premium sin crear bt2_picks.
   */
  unlockPremiumVaultPick: (vaultPickId: string) => Promise<VaultUnlockResult>
  /** Devuelve el bt2PickId tomado para un vault pick dado (o null si no existe). */
  getApiPickRecord: (vaultPickId: string) => Bt2TakenPickRecord | null
  /**
   * T-169: si el día operativo actual ≠ último snapshot persistido, fuerza `picksLoadStatus: 'idle'`
   * para que `VaultPage` vuelva a llamar `loadApiPicks()`.
   */
  invalidateVaultIfOperatingDayMismatch: (expectedDayKey: string | null) => void
  /** Solo tests / reset global */
  reset: () => void
}

export type VaultStore = VaultStoreState & VaultStoreActions

const initial: VaultStoreState = {
  unlockedPickIds: [],
  apiPicks: [],
  takenApiPicks: [],
  picksLoadStatus: 'idle',
  picksMessage: null,
  sessionOpenStatus: 'idle',
  vaultSnapshotOperatingDayKey: null,
  vaultPoolMeta: null,
  vaultDaySnapshotMeta: null,
  vaultLocalSlateCycle: 0,
}

export const useVaultStore = create<VaultStore>()(
  persist(
    (set, get) => {
      const applyVaultPicksPageData = (data: Bt2VaultPicksPageOut) => {
        const sessionDayKey = useSessionStore.getState().operatingDayKey
        const snapshotPicks = data.picks
        const poolMeta = {
          poolTargetCount: data.poolTargetCount ?? 5,
          poolHardCap: Math.max(1, data.poolHardCap ?? 5),
          valuePoolUniverseMax: data.valuePoolUniverseMax ?? 20,
          poolItemCount: snapshotPicks.length,
          vaultUniversePersistedCount:
            data.vaultUniversePersistedCount ?? snapshotPicks.length,
          slateBandCycle: data.slateBandCycle ?? 0,
          poolBelowTarget: Boolean(data.poolBelowTarget),
        }
        const dayMeta: Bt2VaultDaySnapshotMeta = {
          dsrSignalDegraded: Boolean(data.dsrSignalDegraded),
          limitedCoverage: Boolean(data.limitedCoverage),
          operationalEmptyHard: Boolean(data.operationalEmptyHard),
          vaultOperationalMessageEs: data.vaultOperationalMessageEs ?? null,
          fallbackDisclaimerEs: data.fallbackDisclaimerEs ?? null,
          futureEventsInWindowCount: data.futureEventsInWindowCount ?? 0,
          fallbackEligiblePoolCount: data.fallbackEligiblePoolCount ?? 0,
        }
        const cycle = data.slateBandCycle ?? 0
        if (!snapshotPicks.length) {
          set({
            apiPicks: [],
            picksLoadStatus: 'empty',
            picksMessage: data.message ?? 'No hay picks disponibles hoy.',
            vaultSnapshotOperatingDayKey: sessionDayKey ?? null,
            vaultPoolMeta: poolMeta,
            vaultDaySnapshotMeta: dayMeta,
            vaultLocalSlateCycle: cycle,
          })
        } else {
          set({
            apiPicks: snapshotPicks,
            picksLoadStatus: 'loaded',
            picksMessage: data.message ?? null,
            vaultSnapshotOperatingDayKey: snapshotPicks[0].operatingDayKey,
            vaultPoolMeta: poolMeta,
            vaultDaySnapshotMeta: dayMeta,
            vaultLocalSlateCycle: cycle,
          })
        }
      }

      return {
      ...initial,

      // ── Sprint 01 compat ──────────────────────────────────────────────────
      isUnlocked: (pickId) => {
        // API picks (string like "dp-7"): check takenApiPicks
        const takenRecord = get().takenApiPicks.find((r) => r.vaultPickId === pickId)
        if (takenRecord) return true
        // API picks with standard tier: always unlocked
        const apiPick = get().apiPicks.find((p) => p.id === pickId)
        if (apiPick?.accessTier === 'standard') return true
        // Legacy string IDs in unlockedPickIds
        return get().unlockedPickIds.includes(pickId)
      },

      tryUnlockPick: (pickId) => {
        // Check API picks first
        const apiPick = get().apiPicks.find((p) => p.id === pickId)
        if (apiPick) {
          // Delegate to async takeApiPick (not called here for backwards compat)
          return { ok: false, reason: 'api_error' }
        }
        // Legacy mock flow
        if (useSessionStore.getState().isStationLocked()) {
          return { ok: false, reason: 'station_locked' }
        }
        if (get().unlockedPickIds.includes(pickId)) {
          return { ok: false, reason: 'already_unlocked' }
        }
        const dp = useUserStore.getState().disciplinePoints
        if (dp < VAULT_UNLOCK_COST_DP) {
          return { ok: false, reason: 'insufficient_dp' }
        }
        useUserStore.getState().incrementDisciplinePoints(-VAULT_UNLOCK_COST_DP)
        set((s) => ({
          unlockedPickIds: s.unlockedPickIds.includes(pickId)
            ? s.unlockedPickIds
            : [...s.unlockedPickIds, pickId],
        }))
        console.info(`[BT2] Pick desbloqueado (mock): ${pickId}`)
        return { ok: true }
      },

      // ── API flow (US-FE-025) ──────────────────────────────────────────────
      loadApiPicks: async () => {
        set({ picksLoadStatus: 'loading' })
        // 1. Abrir sesión si no está abierta
        set({ sessionOpenStatus: 'opening' })
        try {
          await bt2FetchJson('/bt2/session/open', { method: 'POST' })
          set({ sessionOpenStatus: 'open' })
        } catch (e) {
          const msg = e instanceof Error ? e.message : ''
          if (msg.includes('409')) {
            // Sesión ya abierta: OK
            set({ sessionOpenStatus: 'open' })
          } else {
            console.warn('[BT2] session/open error:', msg)
            set({ sessionOpenStatus: 'error' })
          }
        }
        // 2. Cargar picks (servidor devuelve hasta 20; la UI recorta a poolHardCap).
        try {
          const data = await bt2FetchJson<Bt2VaultPicksPageOut>('/bt2/vault/picks')
          applyVaultPicksPageData(data)
        } catch (e) {
          console.error('[BT2] vault/picks error:', e)
          set({
            picksLoadStatus: 'error',
            picksMessage: null,
            vaultPoolMeta: null,
            vaultDaySnapshotMeta: null,
          })
        }
        void useUserStore.getState().syncDpBalance()
      },

      regenerateVaultSlate: () => {
        const { apiPicks, vaultPoolMeta } = get()
        if (!apiPicks.length) {
          return {
            ok: false as const,
            message:
              'No hay pool cargado. Abre la estación y espera el GET de la bóveda (un solo request con hasta 20 picks).',
          }
        }
        const nextCycle = (get().vaultLocalSlateCycle + 1) % 4
        const poolSize = apiPicks.length
        set({
          vaultLocalSlateCycle: nextCycle,
          vaultPoolMeta: vaultPoolMeta
            ? { ...vaultPoolMeta, slateBandCycle: nextCycle }
            : {
                poolTargetCount: 5,
                poolHardCap: 5,
                valuePoolUniverseMax: 20,
                poolItemCount: poolSize,
                vaultUniversePersistedCount: poolSize,
                slateBandCycle: nextCycle,
                poolBelowTarget: poolSize < 5,
              },
        })
        return { ok: true as const, cycle: nextCycle, poolSize }
      },

      takeApiPick: async (vaultPick) => {
        // Ya tomado previamente
        const existing = get().takenApiPicks.find((r) => r.vaultPickId === vaultPick.id)
        if (existing) return { ok: false, reason: 'already_unlocked' }

        // Verificar estación
        if (useSessionStore.getState().isStationLocked()) {
          return { ok: false, reason: 'station_locked' }
        }

        if (
          vaultPick.accessTier === 'premium' &&
          !vaultPick.premiumUnlocked
        ) {
          return { ok: false, reason: 'premium_not_unlocked' }
        }

        if (vaultPick.isAvailable === false) {
          return { ok: false, reason: 'pick_unavailable' }
        }

        if (isKickoffUtcInPast(vaultPick.kickoffUtc)) {
          return {
            ok: false,
            reason: 'kickoff_elapsed',
            apiMessage:
              'El partido ya inició según el horario del evento; no puedes registrar el pick.',
          }
        }

        if (!vaultPick.eventId) {
          return { ok: false, reason: 'no_event_id' }
        }

        const sessionDay = useSessionStore.getState().operatingDayKey
        const quota = computeVaultQuota(
          get().takenApiPicks,
          sessionDay,
          get().apiPicks,
        )
        if (
          vaultPick.accessTier === 'standard' &&
          quota.standardRemaining <= 0
        ) {
          return { ok: false, reason: 'quota_standard_exhausted' }
        }
        if (vaultPick.accessTier === 'premium' && quota.premiumRemaining <= 0) {
          return { ok: false, reason: 'quota_premium_exhausted' }
        }

        // Construir stake
        const bankroll = useBankrollStore.getState().confirmedBankrollCop
        const stakePct = useBankrollStore.getState().selectedStakePct
        const stakeUnits = computeUnitValue(bankroll, stakePct)

        const body: Bt2PickRegisterBody = {
          event_id: vaultPick.eventId,
          market: vaultPick.marketClass,
          selection: vaultPick.selectionSummaryEs,
          odds_accepted: vaultPick.suggestedDecimalOdds,
          stake_units: stakeUnits > 0 ? stakeUnits : 1,
        }

        const post = await bt2PostPickRegister(body)
        if (!post.ok) {
          if (
            post.status === 422 &&
            post.errorCode === BT2_ERR_INSUFFICIENT_BANKROLL_STAKE
          ) {
            void useBankrollStore.getState().syncFromApi()
            return {
              ok: false,
              reason: 'insufficient_bankroll',
              apiMessage: post.message,
            }
          }
          if (post.status === 402 && post.premiumInsufficient) {
            console.warn(
              `[BT2] Desbloqueo premium rechazado (402): ${post.premiumInsufficient.message}`,
            )
            void useUserStore.getState().syncDpBalance()
            return {
              ok: false,
              reason: 'insufficient_dp_premium',
              premiumDetail: post.premiumInsufficient,
            }
          }
          if (
            post.status === 422 &&
            post.errorCode === BT2_ERR_PICK_EVENT_KICKOFF_ELAPSED
          ) {
            return {
              ok: false,
              reason: 'kickoff_elapsed',
              apiMessage: post.message,
            }
          }
          console.error('[BT2] takeApiPick error:', post.status, post.message)
          return { ok: false, reason: 'api_error', apiMessage: post.message }
        }

        const res = post.data
        // Sprint 05 (US-BE-017): el −50 DP va en bt2_dp_ledger en el mismo POST; no ajustar local.
        void useUserStore.getState().syncDpBalance()
        if (
          res.bankrollAfterUnits != null &&
          Number.isFinite(res.bankrollAfterUnits)
        ) {
          useBankrollStore
            .getState()
            .reconcileToExchangeBalance(res.bankrollAfterUnits)
        } else {
          void useBankrollStore.getState().syncFromApi()
        }

        const record: Bt2TakenPickRecord = {
          vaultPickId: vaultPick.id,
          bt2PickId: res.pick_id,
          eventId: vaultPick.eventId,
          market: res.market,
          selection: res.selection,
          oddsAccepted: res.odds_accepted,
          stakeUnits: res.stake_units,
          openedAt: res.opened_at,
          eventLabel: vaultPick.eventLabel,
          operatingDayKey: vaultPick.operatingDayKey,
          accessTier: vaultPick.accessTier,
        }

        set((s) => ({ takenApiPicks: [...s.takenApiPicks, record] }))
        console.info(
          `[BT2] Pick API registrado: ${vaultPick.id} → bt2PickId=${res.pick_id}`,
        )
        return { ok: true }
      },

      unlockPremiumVaultPick: async (vaultPickId) => {
        const vaultPick = get().apiPicks.find((p) => p.id === vaultPickId)
        if (!vaultPick) {
          return { ok: false, reason: 'pick_not_found' }
        }
        if (vaultPick.accessTier !== 'premium') {
          return { ok: false, reason: 'not_premium' }
        }
        if (vaultPick.premiumUnlocked) {
          return { ok: false, reason: 'already_unlocked' }
        }
        if (useSessionStore.getState().isStationLocked()) {
          return { ok: false, reason: 'station_locked' }
        }
        if (isKickoffUtcInPast(vaultPick.kickoffUtc)) {
          return {
            ok: false,
            reason: 'kickoff_elapsed',
            apiMessage:
              'El partido ya inició según el horario del evento; no puedes desbloquear esta señal.',
          }
        }

        const post = await bt2PostVaultPremiumUnlock({ vaultPickId })
        if (!post.ok) {
          if (post.status === 402 && post.premiumInsufficient) {
            void useUserStore.getState().syncDpBalance()
            return {
              ok: false,
              reason: 'insufficient_dp_premium',
              premiumDetail: post.premiumInsufficient,
            }
          }
          console.warn(
            '[BT2] unlockPremiumVaultPick:',
            post.status,
            post.message,
          )
          void useUserStore.getState().syncDpBalance()
          return { ok: false, reason: 'api_error' }
        }

        void useUserStore.getState().syncDpBalance()
        set((s) => ({
          apiPicks: s.apiPicks.map((p) =>
            p.id === vaultPickId ? { ...p, premiumUnlocked: true } : p,
          ),
        }))
        console.info(`[BT2] Premium desbloqueado (vault): ${vaultPickId}`)
        return { ok: true }
      },

      getApiPickRecord: (vaultPickId) => {
        return get().takenApiPicks.find((r) => r.vaultPickId === vaultPickId) ?? null
      },

      invalidateVaultIfOperatingDayMismatch: (expectedDayKey) => {
        if (!expectedDayKey) return
        const { picksLoadStatus, vaultSnapshotOperatingDayKey, apiPicks } = get()
        if (picksLoadStatus !== 'loaded' && picksLoadStatus !== 'empty') return
        if (vaultSnapshotOperatingDayKey == null) {
          // Migración T-169: estado persistido sin snapshot → un GET fija `vaultSnapshotOperatingDayKey`.
          if (picksLoadStatus === 'loaded' && apiPicks.length > 0) {
            set({ picksLoadStatus: 'idle' })
          }
          return
        }
        if (vaultSnapshotOperatingDayKey === expectedDayKey) return
        set({ picksLoadStatus: 'idle' })
      },

      reset: () => set(initial),
    }
    },
    {
      /**
       * Clave nueva (2026-04): el blob anterior persistía `apiPicks` + `picksLoadStatus`.
       * Eso dejaba 20 filas “pegadas” para siempre: con `loaded` la bóveda no volvía a
       * llamar GET /bt2/vault/picks aunque el servidor ya devolviera 5 (reiniciar API no limpia el navegador).
       */
      name: 'bt2_v2_vault_v2',
      storage: createJSONStorage(() => createBt2EncryptedLocalStorage()),
      /** Solo estado local; el listado del día siempre viene del servidor al montar (idle → fetch). */
      partialize: (s) => ({
        unlockedPickIds: s.unlockedPickIds,
        takenApiPicks: s.takenApiPicks,
      }),
    },
  ),
)
