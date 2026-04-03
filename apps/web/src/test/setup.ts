import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { useUserStore } from '@/store/useUserStore'

afterEach(() => {
  useUserStore.getState().reset()
  useUserStore.persist.clearStorage()
  localStorage.clear()
})
