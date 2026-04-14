import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/lib/api'
import type { Bt2AdminFase1OperationalSummaryOut } from '@/lib/bt2Types'
import AdminFase1OperationalPage from '@/pages/AdminFase1OperationalPage'

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
}

describe('AdminFase1OperationalPage (US-FE-061)', () => {
  let spy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    spy = vi
      .spyOn(api, 'fetchBt2AdminFase1OperationalSummary')
      .mockResolvedValue(mockSummary as Bt2AdminFase1OperationalSummaryOut)
  })

  it('muestra tres bloques y KPIs del loop', async () => {
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
    expect(screen.getByText(/OUTSIDE_SUPPORTED_MARKET_V1/)).toBeInTheDocument()
    expect(screen.getByText(/Hit rate global/i)).toBeInTheDocument()
    expect(spy).toHaveBeenCalled()
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
