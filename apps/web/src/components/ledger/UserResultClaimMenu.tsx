import { useState } from 'react'
import { bt2PatchUserResultClaim, type Bt2UserResultClaim } from '@/lib/api'

/**
 * Mini menú tipo v1 (Auto / pendiente / ganado / perdido / void).
 * Persiste en `bt2_picks.user_result_claim`; no ejecuta liquidación formal.
 */
export function UserResultClaimMenu(props: {
  bt2PickId: number
  claim: string | null
  disabled?: boolean
  onDone: () => void | Promise<void>
}) {
  const [busy, setBusy] = useState(false)

  const fire = async (next: Bt2UserResultClaim | null) => {
    if (busy || props.disabled) return
    setBusy(true)
    try {
      await bt2PatchUserResultClaim(props.bt2PickId, next)
      await Promise.resolve(props.onDone())
    } catch (e) {
      console.error('[BT2] user-result-claim:', e)
    } finally {
      setBusy(false)
    }
  }

  const is = (v: Bt2UserResultClaim) => props.claim === v
  const base =
    'min-w-[2.25rem] rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-tight transition-colors'
  const active = 'border-[#8B5CF6] bg-[#8B5CF6]/10 text-[#4c1d95]'
  const idle = 'border-[#a4b4be]/30 bg-white text-[#52616a] hover:border-[#6d3bd7]/40'

  return (
    <div
      className="inline-flex flex-wrap items-center gap-0.5"
      title="Tu criterio (no reemplaza la liquidación en protocolo)"
    >
      <button
        type="button"
        disabled={busy}
        className={`${base} ${props.claim == null || props.claim === '' ? active : idle}`}
        onClick={() => void fire(null)}
      >
        Auto
      </button>
      <button
        type="button"
        disabled={busy}
        className={`${base} ${is('pending') ? active : idle}`}
        onClick={() => void fire('pending')}
      >
        …
      </button>
      <button
        type="button"
        disabled={busy}
        className={`${base} ${is('won') ? active : idle}`}
        onClick={() => void fire('won')}
      >
        G
      </button>
      <button
        type="button"
        disabled={busy}
        className={`${base} ${is('lost') ? active : idle}`}
        onClick={() => void fire('lost')}
      >
        L
      </button>
      <button
        type="button"
        disabled={busy}
        className={`${base} ${is('void') ? active : idle}`}
        onClick={() => void fire('void')}
        title="Empate técnico / anulación"
      >
        ∅
      </button>
    </div>
  )
}
