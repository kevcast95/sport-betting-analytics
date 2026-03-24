import { useCallback, useEffect, useState } from 'react'

const KEY = 'scrapper-tracking-user-id'

export function useTrackingUser() {
  const [userId, setUserIdState] = useState<number | null>(() => {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  })

  useEffect(() => {
    if (userId != null) localStorage.setItem(KEY, String(userId))
    else localStorage.removeItem(KEY)
  }, [userId])

  const setUserId = useCallback((id: number | null) => {
    setUserIdState(id)
  }, [])

  return { userId, setUserId }
}
