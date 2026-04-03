import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { useBankrollStore } from '@/store/useBankrollStore'
import { useUserStore } from '@/store/useUserStore'

afterEach(() => {
  useUserStore.getState().reset()
  useUserStore.persist.clearStorage()
  useBankrollStore.getState().reset()
  useBankrollStore.persist.clearStorage()
  localStorage.clear()
})
