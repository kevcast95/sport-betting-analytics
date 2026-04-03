import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useUserStore } from '@/store/useUserStore'

export function V2SessionGate({ children }: { children: ReactNode }) {
  const location = useLocation()
  const isAuthenticated = useUserStore((s) => s.isAuthenticated)
  const hasAcceptedContract = useUserStore((s) => s.hasAcceptedContract)

  if (!isAuthenticated) {
    console.warn(
      `[BT2] Observabilidad: acceso a ${location.pathname} sin sesión; redirigiendo a /v2/session.`,
    )
    return <Navigate to="/v2/session" replace />
  }
  if (!hasAcceptedContract) {
    console.warn(
      `[BT2] Observabilidad: bypass del contrato bloqueado (hasAcceptedContract=false en ${location.pathname}); redirigiendo a /v2/session.`,
    )
    return <Navigate to="/v2/session" replace />
  }
  return <>{children}</>
}
