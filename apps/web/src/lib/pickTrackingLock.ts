import { useEffect, useMemo, useState } from 'react'

/** Minutos tras el inicio del partido en los que se bloquea tomé + monto. */
export const PICK_TRACKING_LOCK_MINUTES_AFTER_KICKOFF = 100

export function isPickTrackingLocked(
  kickoffAtUtc: string | null | undefined,
  nowMs: number = Date.now(),
): boolean {
  if (!kickoffAtUtc?.trim()) return false
  const t = Date.parse(kickoffAtUtc.trim())
  if (Number.isNaN(t)) return false
  const deadline =
    t + PICK_TRACKING_LOCK_MINUTES_AFTER_KICKOFF * 60 * 1000
  return nowMs >= deadline
}

/** Se actualiza cada 15s para desbloquear/bloquear sin recargar. */
export function usePickTrackingLock(
  kickoffAtUtc: string | null | undefined,
): boolean {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 15_000)
    return () => window.clearInterval(id)
  }, [])
  return useMemo(
    () => isPickTrackingLocked(kickoffAtUtc, now),
    [kickoffAtUtc, now],
  )
}
