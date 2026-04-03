import BunkerLayout from '@/layouts/BunkerLayout'
import { V2SessionGate } from '@/components/V2SessionGate'

export default function V2SettingsPage() {
  return (
    <V2SessionGate>
      <BunkerLayout />
    </V2SessionGate>
  )
}
