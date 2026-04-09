/**
 * Tipos canónicos para la integración API Sprint 04 — US-FE-025 … US-FE-029.
 * Alineados con bt2_schemas.py (camelCase vía serialization_alias).
 */

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface Bt2AuthTokenResponse {
  access_token: string
  user_id: string
  display_name?: string
}

export interface Bt2MeResponse {
  user_id: string
  email: string
  display_name: string
  created_at: string
}

// ─── Vault ────────────────────────────────────────────────────────────────────

/** Franja local del kickoff (Sprint 05.2 / D-05.2-002). */
export type Bt2VaultTimeBand = 'morning' | 'afternoon' | 'evening' | 'overnight'

/** Schema real de GET /bt2/vault/picks (bt2_schemas.py Bt2VaultPickOut). */
export interface Bt2VaultPickOut {
  id: string
  eventId: number
  marketClass: string
  marketLabelEs: string
  eventLabel: string
  titulo: string
  suggestedDecimalOdds: number
  edgeBps: number
  selectionSummaryEs: string
  traduccionHumana: string
  curvaEquidad: number[]
  accessTier: 'standard' | 'premium'
  unlockCostDp: number
  operatingDayKey: string
  isAvailable: boolean
  /** ISO 8601 UTC (…Z). Vacío si el CDM no tiene kickoff (D-05-011). */
  kickoffUtc: string
  /** Valor crudo `bt2_events.status` (scheduled, inplay, finished, …). */
  eventStatus: string
  externalSearchUrl: string
  /** US-BE-029: desbloqueo premium ya pagado (o legado: pick abierto en el evento). */
  premiumUnlocked: boolean
  /** US-BE-030: franja horaria local del kickoff (TZ usuario). */
  timeBand: Bt2VaultTimeBand
  /** Sprint 06 — DSR / pipeline (US-BE-025, US-DX-002). */
  pipelineVersion?: string
  dsrNarrativeEs?: string
  dsrConfidenceLabel?: string
  dsrSource?: string
  marketCanonical?: string
  marketCanonicalLabelEs?: string
  modelMarketCanonical?: string
  modelSelectionCanonical?: string
}

/** POST /bt2/vault/premium-unlock (US-BE-029). */
export interface Bt2VaultPremiumUnlockBody {
  vaultPickId: string
}

export interface Bt2VaultPremiumUnlockOut {
  vaultPickId: string
  premiumUnlocked: boolean
  dpBalanceAfter: number
}

export interface Bt2VaultPicksPageOut {
  picks: Bt2VaultPickOut[]
  generatedAtUtc: string
  message?: string
  /** Objetivo de ítems en pool (típ. 15) — US-BE-030. */
  poolTargetCount: number
  poolHardCap: number
  poolItemCount: number
  poolBelowTarget: boolean
}

// ─── Picks (bt2_picks) ────────────────────────────────────────────────────────

export interface Bt2PickRegisterBody {
  event_id: number
  market: string
  selection: string
  odds_accepted: number
  stake_units: number
}

export interface Bt2PickOut {
  pick_id: number
  status: 'open' | 'won' | 'lost' | 'void' | 'cancelled'
  opened_at: string
  stake_units: number
  odds_accepted: number
  event_label: string
  event_id: number
  market: string
  selection: string
  settled_at: string | null
  pnl_units: number | null
  /** Suma ledger `pick_settle` para este pick; null si sigue abierto. */
  earned_dp: number | null
  /** camelCase desde API (`response_model_by_alias`). */
  resultHome?: number | null
  resultAway?: number | null
  kickoffUtc?: string | null
  eventStatus?: string | null
  settlementSource?: string
  marketCanonical?: string | null
  marketCanonicalLabelEs?: string | null
  modelMarketCanonical?: string | null
  modelSelectionCanonical?: string | null
  modelPredictionResult?: string | null
}

export interface Bt2PicksListOut {
  picks: Bt2PickOut[]
}

export interface Bt2SettleOut {
  pick_id: number
  status: string
  pnl_units: number
  bankroll_after_units: number | null
  earned_dp: number
  dp_balance_after: number
}

// ─── Session ──────────────────────────────────────────────────────────────────

export interface Bt2SessionDayOut {
  operatingDayKey: string
  userTimeZone: string
  graceUntilIso: string | null
  pendingSettlementsPreviousDay: number
  stationClosedForOperatingDay: boolean
}

/** POST /bt2/session/close — campos nuevos con alias camelCase. */
export interface Bt2SessionCloseOut {
  session_id: number
  status: string
  grace_until_iso: string
  pending_settlements: number
  earnedDpSessionClose: number
  dpBalanceAfter: number
}

// ─── User ─────────────────────────────────────────────────────────────────────

export interface Bt2UserProfileOut {
  userId: string
  email: string
  displayName: string
  bankrollAmount: number
  bankrollCurrency: string
  createdAt: string
}

export interface Bt2UserSettingsOut {
  riskPerPickPct: number
  dpUnlockPremiumThreshold: number
  timezone: string
  displayCurrency: string
}

/** GET /bt2/user/dp-balance — FastAPI serializa snake_case por defecto. */
export interface Bt2DpBalanceOut {
  dp_balance: number
  pending_settlements: number
  behavioral_block_count: number
}

/** POST /bt2/user/onboarding-phase-a-complete */
export interface Bt2OnboardingPhaseACompleteOut {
  dp_balance: number
  granted_dp: number
}

// ─── Meta ─────────────────────────────────────────────────────────────────────

export interface Bt2MetaOut {
  contractVersion?: string
  settlementVerificationMode: 'trust' | 'verified'
}

// ─── Admin analytics (US-BE-028 / T-163) — header X-BT2-Admin-Key ─────────────

export interface Bt2AdminDsrDaySummaryOut {
  operatingDayKey: string
  distinctEventsInVault: number
  picksSettledWithModel: number
  modelHits: number
  modelMisses: number
  modelVoids: number
  modelNa: number
  hitRatePct: number | null
  summaryHumanEs: string
}

export interface Bt2AdminDsrAuditRowOut {
  pickId: number
  userId: string
  eventId: number
  operatingDayKey: string
  status: string
  modelPredictionResult?: string | null
  modelMarketCanonical?: string | null
  modelSelectionCanonical?: string | null
}

export interface Bt2AdminDsrDayOut {
  summary: Bt2AdminDsrDaySummaryOut
  auditRows: Bt2AdminDsrAuditRowOut[]
}

// ─── US-DX-001 — Razones canónicas bt2_dp_ledger.reason (Sprint 05) ─────────

export type Bt2DpLedgerReason =
  | 'pick_settle'
  | 'pick_premium_unlock'
  | 'session_close_discipline'
  | 'onboarding_welcome'
  | 'onboarding_phase_a'
  | 'penalty_station_unclosed'
  | 'penalty_unsettled_picks'
  /** Reservado Sprint 07 */
  | 'parlay_activation_2l'
  /** Reservado Sprint 07 */
  | 'parlay_activation_3l'

/** 402 POST /bt2/picks — saldo insuficiente para pick_premium_unlock (D-05-005). */
export interface Bt2DpInsufficientPremiumDetail {
  code: 'dp_insufficient_for_premium_unlock'
  message: string
  requiredDp: number
  currentDp: number
}

// ─── Operating day summary (US-BE-018) ────────────────────────────────────────

export interface Bt2OperatingDaySummaryOut {
  operatingDayKey: string
  userTimeZone: string
  picksOpenedCount: number
  picksSettledCount: number
  wonCount: number
  lostCount: number
  voidCount: number
  totalStakeUnitsSettled: number
  netPnlUnits: number
  dpEarnedFromSettlements: number
  dpEarnedFromSessionClose: number
}

// ─── DP ledger (GET /bt2/user/dp-ledger) — snake_case como devuelve FastAPI ────

export interface Bt2DpLedgerEntry {
  id: number
  delta_dp: number
  reason: string
  reference_id: number | null
  created_at: string
  balance_after_dp: number
}

export interface Bt2DpLedgerOut {
  entries: Bt2DpLedgerEntry[]
}

// ─── Taken picks (local tracking de picks API tomados) ────────────────────────

/**
 * Registro local de un pick "tomado" (POST /bt2/picks exitoso).
 * Mapea el vault pick → bt2_picks row para el flujo de settlement.
 */
export interface Bt2TakenPickRecord {
  /** ID del vault pick ("dp-7") */
  vaultPickId: string
  /** bt2_picks.id retornado por POST /bt2/picks */
  bt2PickId: number
  eventId: number
  market: string
  selection: string
  oddsAccepted: number
  stakeUnits: number
  openedAt: string
  eventLabel: string
  /** Sprint 05.2 — cupo diario; copiado del ítem de bóveda al tomar. */
  operatingDayKey?: string
  accessTier?: 'standard' | 'premium'
}
