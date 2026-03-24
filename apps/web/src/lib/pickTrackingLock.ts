import { useMemo } from 'react'

export function isPickTrackingLocked(
  matchState: string | null | undefined,
): boolean {
  return String(matchState ?? '').trim().toLowerCase() === 'finished'
}

/** Bloqueo según `match_state` del API (p. ej. finished). */
export function usePickTrackingLock(
  matchState: string | null | undefined,
): boolean {
  return useMemo(
    () => isPickTrackingLocked(matchState),
    [matchState],
  )
}
