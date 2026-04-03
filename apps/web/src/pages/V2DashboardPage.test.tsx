import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { useUserStore } from '@/store/useUserStore'
import V2DashboardPage from './V2DashboardPage'

function harness(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/v2/session" element={<div>v2-session-marker</div>} />
        <Route path="/v2/dashboard" element={<V2DashboardPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('V2DashboardPage', () => {
  it('redirige a /v2/session si no hay sesión y registra observabilidad', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    useUserStore.setState({
      isAuthenticated: false,
      hasAcceptedContract: false,
    })
    harness('/v2/dashboard')
    expect(screen.getByText('v2-session-marker')).toBeInTheDocument()
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining('sin sesión'),
    )
    warn.mockRestore()
  })

  it('redirige a /v2/session si falta contrato aceptado', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    useUserStore.setState({
      isAuthenticated: true,
      hasAcceptedContract: false,
    })
    harness('/v2/dashboard')
    expect(screen.getByText('v2-session-marker')).toBeInTheDocument()
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining('bypass del contrato'),
    )
    warn.mockRestore()
  })

  it('muestra el Búnker cuando sesión y contrato están OK', () => {
    useUserStore.setState({
      isAuthenticated: true,
      hasAcceptedContract: true,
    })
    harness('/v2/dashboard')
    expect(
      screen.getByRole('heading', { name: /El Búnker/i }),
    ).toBeInTheDocument()
  })
})
