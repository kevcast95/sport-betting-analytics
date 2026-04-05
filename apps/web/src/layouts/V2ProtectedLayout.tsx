import { Outlet } from 'react-router-dom'
import { V2SessionGate } from '@/components/V2SessionGate'

/** Sesión + contrato; las rutas hijas definen diagnóstico, búnker, etc. */
export default function V2ProtectedLayout() {
  return (
    <V2SessionGate>
      <Outlet />
    </V2SessionGate>
  )
}
