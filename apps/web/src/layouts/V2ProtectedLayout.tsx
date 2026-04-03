import { V2SessionGate } from '@/components/V2SessionGate'
import BunkerLayout from '@/layouts/BunkerLayout'

/** Contenedor V2 tras sesión + contrato; el contenido va en `<Outlet />` dentro de BunkerLayout. */
export default function V2ProtectedLayout() {
  return (
    <V2SessionGate>
      <BunkerLayout />
    </V2SessionGate>
  )
}
