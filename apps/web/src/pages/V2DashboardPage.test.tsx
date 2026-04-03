import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import V2ProtectedLayout from '@/layouts/V2ProtectedLayout'
import SanctuaryPage from '@/pages/SanctuaryPage'
import VaultPage from '@/pages/VaultPage'
import V2SettingsOutlet from '@/pages/V2SettingsOutlet'
import { useUserStore } from '@/store/useUserStore'

function v2Harness(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/v2/session" element={<div>v2-session-marker</div>} />
        <Route path="/v2" element={<V2ProtectedLayout />}>
          <Route path="sanctuary" element={<SanctuaryPage />} />
          <Route path="vault" element={<VaultPage />} />
          <Route path="settings" element={<V2SettingsOutlet />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('V2 rutas protegidas (US-FE-004)', () => {
  it('redirige a /v2/session si no hay sesión y registra observabilidad', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    useUserStore.setState({
      isAuthenticated: false,
      hasAcceptedContract: false,
    })
    v2Harness('/v2/sanctuary')
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
    v2Harness('/v2/sanctuary')
    expect(screen.getByText('v2-session-marker')).toBeInTheDocument()
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining('bypass del contrato'),
    )
    warn.mockRestore()
  })

  it('muestra el Santuario cuando sesión y contrato están OK', () => {
    useUserStore.setState({
      isAuthenticated: true,
      hasAcceptedContract: true,
    })
    v2Harness('/v2/sanctuary')
    expect(
      screen.getByRole('heading', {
        name: /Calma en el ruido del cambio/i,
      }),
    ).toBeInTheDocument()
    expect(screen.getByText(/Santuario Zurich/i)).toBeInTheDocument()
  })

  it('muestra La Bóveda en /v2/vault', () => {
    useUserStore.setState({
      isAuthenticated: true,
      hasAcceptedContract: true,
    })
    v2Harness('/v2/vault')
    expect(
      screen.getByRole('heading', { name: /La Bóveda/i }),
    ).toBeInTheDocument()
  })

  it('US-FE-004: el primer enlace del sidebar lateral es Santuario', () => {
    useUserStore.setState({
      isAuthenticated: true,
      hasAcceptedContract: true,
    })
    v2Harness('/v2/vault')
    const lateral = screen.getByRole('navigation', {
      name: /Navegación lateral V2/i,
      hidden: true,
    })
    const firstLink = lateral.querySelector('a[href]')
    expect(firstLink).toBeTruthy()
    expect(firstLink).toHaveAttribute('href', '/v2/sanctuary')
  })
})
