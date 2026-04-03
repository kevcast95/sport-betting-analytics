import { Navigate } from 'react-router-dom'

/** Compat: enlaces antiguos a `/v2/dashboard` → Santuario (US-FE-004). */
export default function V2DashboardPage() {
  return <Navigate to="/v2/sanctuary" replace />
}
