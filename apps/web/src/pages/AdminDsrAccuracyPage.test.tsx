import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/lib/api'
import AdminDsrAccuracyPage from '@/pages/AdminDsrAccuracyPage'

describe('AdminDsrAccuracyPage (T-166)', () => {
  let spy: ReturnType<typeof vi.spyOn>

  let spyDist: ReturnType<typeof vi.spyOn>

  let spyRange: ReturnType<typeof vi.spyOn>

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
    spyDist = vi
      .spyOn(api, 'fetchBt2AdminVaultPickDistribution')
      .mockResolvedValue({
        operatingDayKey: '2026-04-01',
        byDsrConfidenceLabel: [{ key: 'high', count: 1 }],
        byDsrSource: [{ key: 'dsr_api', count: 2 }],
        scoreBuckets: [{ scoreBucket: -1, count: 1 }],
        totalDailyPickRows: 2,
        summaryHumanEs: 'Distribución de prueba.',
      })
    spyRange = vi
      .spyOn(api, 'fetchBt2AdminDsrRange')
      .mockImplementation(async (from: string, to: string) => {
        const days: {
          operatingDayKey: string
          distinctEventsInVault: number
          picksSettledWithModel: number
          modelHits: number
          modelMisses: number
          modelVoids: number
          modelNa: number
          hitRatePct: number | null
          summaryHumanEs: string
        }[] = []
        const start = new Date(`${from}T12:00:00`)
        const end = new Date(`${to}T12:00:00`)
        for (
          let d = new Date(start);
          d <= end;
          d.setDate(d.getDate() + 1)
        ) {
          const y = d.getFullYear()
          const m = String(d.getMonth() + 1).padStart(2, '0')
          const day = String(d.getDate()).padStart(2, '0')
          days.push({
            operatingDayKey: `${y}-${m}-${day}`,
            distinctEventsInVault: 0,
            picksSettledWithModel: 0,
            modelHits: 0,
            modelMisses: 0,
            modelVoids: 0,
            modelNa: 0,
            hitRatePct: null,
            summaryHumanEs: '',
          })
        }
        return {
          fromOperatingDayKey: from,
          toOperatingDayKey: to,
          days,
          totals: {
            dayCount: days.length,
            daysWithSettledModel: 0,
            sumDistinctEventsDaily: 0,
            picksSettledWithModel: 0,
            modelHits: 0,
            modelMisses: 0,
            modelVoids: 0,
            modelNa: 0,
            hitRatePct: null,
            summaryHumanEs: 'Totales histórico de prueba.',
          },
        }
      })
  })

  afterEach(() => {
    spy.mockRestore()
    spyDist.mockRestore()
    spyRange.mockRestore()
  })

  it('muestra encabezado, KPI de liquidación y bloque de distribución', async () => {
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
    await waitFor(() => {
      expect(
        screen.getByRole('heading', {
          name: /Distribución del snapshot de bóveda/i,
        }),
      ).toBeInTheDocument()
    })
    expect(screen.getByText(/Distribución de prueba/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText(/Totales histórico de prueba/i)).toBeInTheDocument()
    })
  })
})
