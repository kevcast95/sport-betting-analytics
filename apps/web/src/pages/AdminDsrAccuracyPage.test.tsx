import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/lib/api'
import AdminDsrAccuracyPage from '@/pages/AdminDsrAccuracyPage'

describe('AdminDsrAccuracyPage (T-166)', () => {
  let spy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    spy = vi.spyOn(api, 'fetchBt2AdminDsrDay').mockResolvedValue({
      summary: {
        operatingDayKey: '2026-04-01',
        distinctEventsInVault: 3,
        picksSettledWithModel: 2,
        modelHits: 1,
        modelMisses: 1,
        modelVoids: 0,
        modelNa: 0,
        hitRatePct: 50,
        summaryHumanEs: 'Resumen de prueba para operador.',
      },
      auditRows: [],
    })
  })

  afterEach(() => {
    spy.mockRestore()
  })

  it('muestra encabezado y KPI de tasa de acierto', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<AdminDsrAccuracyPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /Precisión del modelo \(DSR\)/i }),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('50.0%')).toBeInTheDocument()
    })
    expect(screen.getByText(/Resumen de prueba para operador/i)).toBeInTheDocument()
  })
})
