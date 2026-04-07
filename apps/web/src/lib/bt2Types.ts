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
  externalSearchUrl: string
}

export interface Bt2VaultPicksPageOut {
  picks: Bt2VaultPickOut[]
  generatedAtUtc: string
  message?: string
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
  earned_dp: number | null
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
  settlementVerificationMode: 'trust' | 'verified'
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
}
