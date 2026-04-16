import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/lib/api'
import type { Bt2AdminFase1OperationalSummaryOut } from '@/lib/bt2Types'
import AdminFase1OperationalPage from '@/pages/AdminFase1OperationalPage'

const mockF2 = {
  leagueBt2IdsResolved: [1, 2],
  windowFrom: '2026-04-09',
  windowTo: '2026-04-09',
  operatingDayKeyFilter: '2026-04-09',
  metricsGlobal: {
    candidate_events_count: 10,
    eligible_official_count: 6,
    eligible_relaxed_count: 8,
    pool_eligibility_rate_official_pct: 60,
    pool_eligibility_rate_relaxed_pct: 80,
    primary_discard_breakdown_official: { INSUFFICIENT_MARKET_FAMILIES: 2 },
    core_family_coverage_counts: { ft_1x2_complete: 5 },
  },
  metricsByLeague: [
    {
      league_id: 1,
      league_name: 'Test League',
      candidate_events_count: 4,
      pool_eligibility_rate_official_pct: 50,
      pass_league_40: true,
    },
  ],
  thresholds: {
    target_global_official_pct: 60,
    target_per_league_official_pct: 40,
    pass_global_60: true,
    pass_all_leagues_40: true,
  },
  insufficientMarketFamiliesDominant: false,
  noteEs: 'Nota F2 de prueba.',
}

const mockSummary = {
  operatingDayKey: '2026-04-09',
  poolCoverage: {
    candidateEventsCount: 4,
    eligibleEventsCount: 2,
    eventsWithLatestAudit: 3,
    poolEligibilityRatePct: 50,
    poolDiscardReasonBreakdown: { MISSING_VALID_ODDS: 1, '(sin auditoría reciente)': 1 },
  },
  officialEvaluationLoop: {
    suggestedPicksCount: 5,
    officialEvaluationEnrolled: 5,
    pendingResult: 1,
    evaluatedHit: 2,
    evaluatedMiss: 1,
    voidCount: 0,
    noEvaluable: 1,
    hitRateOnScoredPct: 66.67,
    noEvaluableByReason: { OUTSIDE_SUPPORTED_MARKET_V1: 1 },
    summaryHumanEs: 'Resumen humano de prueba.',
    operatingDayKeyFilter: '2026-04-09',
  },
  precisionByMarket: [
    {
      bucketKey: 'FT_1X2',
      evaluatedHit: 2,
      evaluatedMiss: 1,
      pendingResult: 0,
      noEvaluable: 0,
      voidCount: 0,
      hitRateOnScoredPct: 66.67,
    },
  ],
  precisionByConfidence: [
    {
      bucketKey: 'high',
      evaluatedHit: 1,
      evaluatedMiss: 0,
      pendingResult: 0,
      noEvaluable: 0,
      voidCount: 0,
      hitRateOnScoredPct: 100,
    },
  ],
  summaryHumanEs: 'Texto agregado día.',
  poolEligibilityMinFamiliesRequired: 2,
  poolEligibilityOfficialReferenceS63: 2,
  poolEligibilityObservabilityRelaxed: false,
  poolEligibilityConfigNoteEs: '',
}

describe('AdminFase1OperationalPage (US-FE-061)', () => {
  let spy: ReturnType<typeof vi.spyOn>
  let spyF2: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    spy = vi
      .spyOn(api, 'fetchBt2AdminFase1OperationalSummary')
      .mockResolvedValue(mockSummary as Bt2AdminFase1OperationalSummaryOut)
    spyF2 = vi
      .spyOn(api, 'fetchBt2AdminF2PoolEligibilityMetrics')
      .mockResolvedValue(mockF2)
  })

  it('muestra bloques Fase 1 + F2 y KPIs del loop', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<AdminFase1OperationalPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/Cobertura del pool/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Cierre de loop/i)).toBeInTheDocument()
    expect(screen.getByText(/Desempeño por mercado/i)).toBeInTheDocument()
    expect(screen.getByTestId('fase1-f2-block')).toBeInTheDocument()
    expect(screen.getByText(/Pool elegibilidad F2/i)).toBeInTheDocument()
    expect(screen.getByText(/Nota F2 de prueba/)).toBeInTheDocument()
    expect(screen.getByText(/OUTSIDE_SUPPORTED_MARKET_V1/)).toBeInTheDocument()
    expect(screen.getByText(/Hit rate \(scored, este día\)/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Checklist cierre operativo US-FE-062/i)).toBeInTheDocument()
    expect(screen.getByTestId('fase1-operating-day-api')).toHaveTextContent(
      'operatingDayKey (respuesta API):',
    )
    expect(screen.getByTestId('fase1-operating-day-api')).toHaveTextContent('2026-04-09')
    expect(spy).toHaveBeenCalled()
    expect(spyF2).toHaveBeenCalledWith({ operatingDayKey: expect.any(String) })
  })

  it('botón Actualizar vuelve a pedir datos', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<AdminFase1OperationalPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Actualizar/i })).toBeInTheDocument()
    })
    const n = spy.mock.calls.length
    await user.click(screen.getByRole('button', { name: /Actualizar/i }))
    await waitFor(() => {
      expect(spy.mock.calls.length).toBeGreaterThan(n)
    })
  })
})
