import { Navigate, Outlet } from 'react-router-dom'
import { useUserStore } from '@/store/useUserStore'

/** Bloquea el búnker hasta completar el diagnóstico operativo (US-FE-005). */
export function DiagnosticAccessGuard() {
  const hasCompletedDiagnostic = useUserStore((s) => s.hasCompletedDiagnostic)
  if (!hasCompletedDiagnostic) {
    return <Navigate to="/v2/diagnostic" replace />
  }
  return <Outlet />
}
