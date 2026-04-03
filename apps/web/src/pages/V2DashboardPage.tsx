import { Navigate } from 'react-router-dom'
import BunkerLayout from '@/layouts/BunkerLayout'
import { useUserStore } from '@/store/useUserStore'

/**
 * US-FE-001: el “dashboard” V2 solo tras sesión mock + contrato firmado.
 */
export default function V2DashboardPage() {
  const isAuthenticated = useUserStore((s) => s.isAuthenticated)
  const hasAcceptedContract = useUserStore((s) => s.hasAcceptedContract)

  if (!isAuthenticated) {
    console.warn(
      '[BT2] Observabilidad: acceso a /v2/dashboard sin sesión; redirigiendo a /v2/session.',
    )
    return <Navigate to="/v2/session" replace />
  }
  if (!hasAcceptedContract) {
    console.warn(
      '[BT2] Observabilidad: bypass del contrato bloqueado (hasAcceptedContract=false en /v2/dashboard); redirigiendo a /v2/session.',
    )
    return <Navigate to="/v2/session" replace />
  }
  return <BunkerLayout />
}
