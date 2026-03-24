import { useEffect, useMemo, useState } from 'react'

export function isPickTrackingLocked(
  matchState: string | null | undefined,
): boolean {
  return String(matchState ?? '').trim().toLowerCase() === 'finished'
}

/** Se actualiza cada 15s para desbloquear/bloquear sin recargar. */
export function usePickTrackingLock(
  matchState: string | null | undefined,
): boolean {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 15_000)
    return () => window.clearInterval(id)
  }, [])
  return useMemo(
    () => isPickTrackingLocked(matchState),
    [matchState, now],
  )
}
