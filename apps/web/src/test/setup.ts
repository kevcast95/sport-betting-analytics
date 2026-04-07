import { afterEach, vi } from 'vitest'

// Spy sobre bt2FetchJson para tests que necesiten mockear; por defecto delega al real.
vi.mock('@/lib/api', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...mod,
    bt2FetchJson: vi.fn(
      (...args: Parameters<typeof mod.bt2FetchJson>) => mod.bt2FetchJson(...args),
    ),
  }
})

import '@testing-library/jest-dom/vitest'

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  vi.stubGlobal('ResizeObserver', ResizeObserverStub)
}

afterEach(async () => {
  const { useUserStore } = await import('@/store/useUserStore')
  const { useBankrollStore } = await import('@/store/useBankrollStore')
  const { useVaultStore } = await import('@/store/useVaultStore')
  const { useTradeStore } = await import('@/store/useTradeStore')
  const { useSessionStore } = await import('@/store/useSessionStore')

  useUserStore.getState().reset()
  useUserStore.persist.clearStorage()
  useBankrollStore.getState().reset()
  useBankrollStore.persist.clearStorage()
  useVaultStore.getState().reset()
  useVaultStore.persist.clearStorage()
  useTradeStore.getState().reset()
  useTradeStore.persist.clearStorage()
  useSessionStore.getState().reset()
  useSessionStore.persist.clearStorage()
  localStorage.clear()
})
