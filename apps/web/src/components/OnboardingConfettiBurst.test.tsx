/**
 * US-FE-015: tests unitarios del componente OnboardingConfettiBurst.
 *
 * Verifica el comportamiento con prefers-reduced-motion: reduce.
 * La ráfaga visual se valida manualmente (abrir fase A en perfil limpio).
 */
import { describe, expect, it, vi, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { OnboardingConfettiBurst } from '@/components/OnboardingConfettiBurst'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('OnboardingConfettiBurst (US-FE-015)', () => {
  it('no monta partículas cuando prefers-reduced-motion está activo', () => {
    // Mock matchMedia para simular reduced motion
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('prefers-reduced-motion'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    // Necesita un padre posicionado ya que el componente usa `absolute`
    const wrapper = document.createElement('div')
    wrapper.style.position = 'fixed'
    document.body.appendChild(wrapper)
    const { container } = render(<OnboardingConfettiBurst active={true} />, { container: wrapper })
    // Con reduced motion activo, el componente retorna null → sin nodos de partículas
    expect(container.querySelector('[aria-hidden="true"]')).toBeNull()
    document.body.removeChild(wrapper)
  })

  it('no monta nada cuando active es false', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    const { container } = render(<OnboardingConfettiBurst active={false} />)
    expect(container.firstChild).toBeNull()
  })
})
