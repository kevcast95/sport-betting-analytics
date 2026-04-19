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
  /** Orden en snapshot del día (1 = cabeza tras compose/regenerar). */
  slateRank?: number
  /** Sprint 06 — DSR / pipeline (US-BE-025, US-DX-002). */
  pipelineVersion?: string
  dsrNarrativeEs?: string
  dsrConfidenceLabel?: string
  dsrSource?: string
  marketCanonical?: string
  marketCanonicalLabelEs?: string
  modelMarketCanonical?: string
  modelSelectionCanonical?: string
  /**
   * S6.1 — heurística servidor 0–100 de completitud de mercados en CDM.
   * Mostrar en UI solo si viene definido; no es probabilidad de acierto (D-06-024 / US-DX-003).
   */
  dataCompletenessScore?: number | null
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

/** Meta del día en GET /bt2/vault/picks — US-BE-036 / T-179–T-180 (lineage a nivel página + vacío operativo). */
export interface Bt2VaultDaySnapshotMeta {
  dsrSignalDegraded: boolean
  limitedCoverage: boolean
  operationalEmptyHard: boolean
  /** Causa operativa cuando no hay picks o vacío duro; priorizar en copy sobre `message` genérico. */
  vaultOperationalMessageEs: string | null
  /** Disclaimer si hay picks por fallback (D-06-025 §4). */
  fallbackDisclaimerEs: string | null
  futureEventsInWindowCount: number
  fallbackEligiblePoolCount: number
}

export interface Bt2VaultPicksPageOut {
  picks: Bt2VaultPickOut[]
  generatedAtUtc: string
  message?: string
  /** Slate objetivo por día (D-06-032: 5). */
  poolTargetCount: number
  poolHardCap: number
  /** Candidatos valor máx. antes del slate (D-06-032: 20). */
  valuePoolUniverseMax?: number
  poolItemCount: number
  /** Filas en bt2_daily_picks (hasta 20); cartelera visible = primeros 5. */
  vaultUniversePersistedCount?: number
  /** Ciclo 0–3 al componer/regenerar (prioridad de franja). */
  slateBandCycle?: number
  poolBelowTarget: boolean
  /** US-BE-036 / T-179 — fallback SQL por ausencia de señal DSR válida. */
  dsrSignalDegraded?: boolean
  limitedCoverage?: boolean
  operationalEmptyHard?: boolean
  vaultOperationalMessageEs?: string | null
  fallbackDisclaimerEs?: string | null
  futureEventsInWindowCount?: number
  fallbackEligiblePoolCount?: number
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
  /** POST /bt2/picks: bankroll tras descontar el stake. */
  bankrollAfterUnits?: number | null
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

/** `GET /bt2/meta` — hito actual: `bt2-dx-001-s6.2r2` (vault 20/5/5 + franjas D-06-032). */
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

/** GET /bt2/admin/analytics/dsr-range — serie diaria + totales (histórico admin). */
export interface Bt2AdminDsrRangeTotalsOut {
  dayCount: number
  daysWithSettledModel: number
  sumDistinctEventsDaily: number
  picksSettledWithModel: number
  modelHits: number
  modelMisses: number
  modelVoids: number
  modelNa: number
  hitRatePct: number | null
  summaryHumanEs: string
}

export interface Bt2AdminDsrRangeOut {
  fromOperatingDayKey: string
  toOperatingDayKey: string
  days: Bt2AdminDsrDaySummaryOut[]
  totals: Bt2AdminDsrRangeTotalsOut
}

/** GET /bt2/admin/analytics/vault-pick-distribution — US-BE-035 / T-183 */
export interface Bt2AdminCountRowOut {
  key: string
  count: number
}

export interface Bt2AdminScoreBucketOut {
  scoreBucket: number
  count: number
}

export interface Bt2AdminVaultPickDistributionOut {
  operatingDayKey: string
  byDsrConfidenceLabel: Bt2AdminCountRowOut[]
  byDsrSource: Bt2AdminCountRowOut[]
  scoreBuckets: Bt2AdminScoreBucketOut[]
  totalDailyPickRows: number
  summaryHumanEs: string
}

/** POST /bt2/admin/vault/regenerate-daily-snapshot — US-BE-047 / T-215 (operación). */
export interface Bt2AdminVaultRegenerateSnapshotOut {
  userId: string
  operatingDayKey: string
  picksInsertedThisRun: number
  picksTotalAfter: number
  messageEs: string
}

/** GET /bt2/admin/analytics/official-evaluation-loop — US-BE-050 / T-233 */
export interface Bt2AdminOfficialEvaluationLoopOut {
  suggestedPicksCount: number
  officialEvaluationEnrolled: number
  pendingResult: number
  evaluatedHit: number
  evaluatedMiss: number
  voidCount: number
  noEvaluable: number
  hitRateOnScoredPct: number | null
  noEvaluableByReason: Record<string, number>
  summaryHumanEs: string
  operatingDayKeyFilter: string | null
}

/** GET /bt2/admin/analytics/fase1-operational-summary — US-BE-052 / T-238 */
export interface Bt2AdminPoolCoverageOut {
  candidateEventsCount: number
  eligibleEventsCount: number
  eventsWithLatestAudit: number
  poolEligibilityRatePct: number | null
  poolDiscardReasonBreakdown: Record<string, number>
}

export interface Bt2AdminOfficialPrecisionBucketOut {
  bucketKey: string
  evaluatedHit: number
  evaluatedMiss: number
  pendingResult: number
  noEvaluable: number
  voidCount: number
  hitRateOnScoredPct: number | null
}

export interface Bt2AdminFase1OperationalSummaryOut {
  operatingDayKey: string
  poolCoverage: Bt2AdminPoolCoverageOut
  officialEvaluationLoop: Bt2AdminOfficialEvaluationLoopOut
  precisionByMarket: Bt2AdminOfficialPrecisionBucketOut[]
  precisionByConfidence: Bt2AdminOfficialPrecisionBucketOut[]
  summaryHumanEs: string
  /** Umbral activo (env `BT2_POOL_ELIGIBILITY_MIN_FAMILIES`, default 2 = canónico S6.3). */
  poolEligibilityMinFamiliesRequired: number
  /** Referencia fija de producto (2); no depende del env. */
  poolEligibilityOfficialReferenceS63: number
  /** True si el umbral activo &lt; referencia oficial (observabilidad interna). */
  poolEligibilityObservabilityRelaxed: boolean
  poolEligibilityConfigNoteEs: string
}

/** GET /bt2/admin/analytics/monitor-resultados — evaluación oficial vs bóveda */
export type Bt2MonitorOutcome = 'si' | 'no' | 'pendiente' | 'void' | 'ne'

/** Stake fijo 1 u por pick; cuota = consenso CDM (mediana entre casas). */
export interface Bt2AdminMonitorRoiFlatStakeOut {
  netUnits: number
  roiPct: number | null
  picksCounted: number
  picksMissingOdds: number
}

export interface Bt2AdminMonitorSummaryOut {
  totalPicks: number
  hits: number
  misses: number
  pending: number
  voidCount: number
  noEvaluable: number
  evaluatedScored: number
  hitRatePct: number | null
  roiFlatStake: Bt2AdminMonitorRoiFlatStakeOut
}

export interface Bt2AdminMonitorTodayOut {
  operatingDayKey: string
  totalPicks: number
  resolved: number
  pending: number
}

export interface Bt2AdminMonitorRowOut {
  dailyPickId: number
  operatingDayKey: string
  eventId: number
  userId: string
  eventLabel: string
  marketLabelEs: string
  selectionSummaryEs: string
  scoreText: string
  outcome: Bt2MonitorOutcome
  iOperated: boolean
  decimalOdds?: number | null
  flatStakeReturnUnits?: number | null
}

export interface Bt2AdminMonitorSmSyncOut {
  attempted: boolean
  ok: boolean
  messageEs: string
  fixturesTargeted: number
  uniqueFixturesProcessed: number
  closedPendingToFinal: number | null
}

export interface Bt2AdminMonitorResultadosOut {
  operatingDayKeyFrom: string
  operatingDayKeyTo: string
  timezoneLabel: string
  todayOperatingDayKey: string
  /** Día del resumen lateral «Hoy» (alineado al rango si consultás un solo día). */
  focusOperatingDayKey: string
  system: Bt2AdminMonitorSummaryOut
  yours: Bt2AdminMonitorSummaryOut | null
  today: Bt2AdminMonitorTodayOut
  rows: Bt2AdminMonitorRowOut[]
  summaryHumanEs: string
  smSync: Bt2AdminMonitorSmSyncOut
}

/**
 * GET /bt2/admin/analytics/f2-pool-eligibility-metrics (T-263).
 * `metricsGlobal` y filas de liga vienen en snake_case desde el API (dict anidado).
 */
export interface Bt2AdminF2MetricsGlobal {
  candidate_events_count?: number
  eligible_official_count?: number
  eligible_relaxed_count?: number
  pool_eligibility_rate_official_pct?: number | null
  pool_eligibility_rate_relaxed_pct?: number | null
  primary_discard_breakdown_official?: Record<string, number>
  core_family_coverage_counts?: Record<string, number>
}

export interface Bt2AdminF2MetricsByLeagueRow {
  league_id?: number
  league_name?: string
  candidate_events_count?: number
  pool_eligibility_rate_official_pct?: number | null
  pass_league_40?: boolean | null
}

export interface Bt2AdminF2PoolMetricsOut {
  leagueBt2IdsResolved: number[]
  windowFrom: string | null
  windowTo: string | null
  operatingDayKeyFilter: string | null
  metricsGlobal: Bt2AdminF2MetricsGlobal
  metricsByLeague: Bt2AdminF2MetricsByLeagueRow[]
  thresholds: Record<string, unknown>
  insufficientMarketFamiliesDominant: boolean | null
  noteEs: string
}

/** POST /bt2/admin/operations/refresh-cdm-from-sm-for-operating-day */
export interface Bt2AdminRefreshCdmFromSmOut {
  ok: boolean
  operatingDayKey: string
  messageEs: string
  fixturesTargeted: number
  uniqueSportmonksFixturesProcessed: number
  smFetchOk: number
  rawUpsertOk: number
  cdmNormalizedOk: number
  cdmSkipped: number
  cdmErrors: number
  officialEvaluation: Record<string, unknown> | null
  notes: string[]
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
  | 'penalty_unsettled_not_applicable'
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
