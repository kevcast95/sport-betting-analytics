import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  vi.stubGlobal('ResizeObserver', ResizeObserverStub)
}
import { useBankrollStore } from '@/store/useBankrollStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'
import { useVaultStore } from '@/store/useVaultStore'

afterEach(() => {
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
