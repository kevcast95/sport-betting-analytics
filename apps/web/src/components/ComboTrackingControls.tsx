import { useEffect, useMemo, useState } from 'react'
import type { TrackingBoardOut } from '@/types/api'
import { formatCOP } from '@/lib/formatDateTime'
import {
  stakeAssessmentCOP,
  suggestedStakeMidCOP,
  suggestedStakeRangeCOP,
} from '@/lib/stakeSuggestion'

type ComboRow = TrackingBoardOut['suggested_combos'][number]

export type ComboSavePayload = {
  comboId: number
  taken: boolean
  stake_amount?: number | null
  userOutcome?: 'auto' | 'win' | 'loss' | 'pending'
}

function baseCombo(c: ComboRow): ComboSavePayload {
  return {
    comboId: c.suggested_combo_id,
    taken: c.user_taken ?? false,
    stake_amount: c.user_stake_amount ?? null,
  }
}

function outcomeLabel(o: string) {
  if (o === 'win') return 'Ganada'
  if (o === 'loss') return 'Perdida'
  return 'Pendiente'
}

function effectiveComboStake(
  copDraft: string,
  persisted: number | null | undefined,
): number | null {
  const raw = copDraft.trim()
  if (raw !== '') {
    const n = Number.parseInt(raw, 10)
    if (!Number.isNaN(n) && n > 0) return n
    return null
  }
  if (persisted != null && persisted > 0) return Math.round(persisted)
  return null
}

const COMBO_TIER = 'low' as const

/** Monto antes de «tomé»; misma regla que singles. */
export function ComboTrackingControls({
  combo: c,
  bankrollCOP,
  disabled,
  onSave,
}: {
  combo: ComboRow
  bankrollCOP: number | null
  disabled?: boolean
  onSave: (payload: ComboSavePayload) => void
}) {
  const range = useMemo(() => {
    if (bankrollCOP == null || bankrollCOP <= 0) return null
    return suggestedStakeRangeCOP(bankrollCOP, COMBO_TIER)
  }, [bankrollCOP])

  const midSuggestion = useMemo(() => {
    if (bankrollCOP == null || bankrollCOP <= 0) return null
    return suggestedStakeMidCOP(bankrollCOP, COMBO_TIER)
  }, [bankrollCOP])

  const [copDraft, setCopDraft] = useState(() =>
    c.user_stake_amount != null ? String(Math.round(c.user_stake_amount)) : '',
  )
  useEffect(() => {
    setCopDraft(
      c.user_stake_amount != null ? String(Math.round(c.user_stake_amount)) : '',
    )
  }, [c.suggested_combo_id, c.user_stake_amount])

  const [copHint, setCopHint] = useState<{
    tone: 'ok' | 'warn' | 'risk'
    message: string
  } | null>(null)

  const stakeNow = useMemo(
    () => effectiveComboStake(copDraft, c.user_stake_amount),
    [copDraft, c.user_stake_amount],
  )
  const bankrollOk =
    bankrollCOP != null &&
    bankrollCOP > 0 &&
    stakeNow != null &&
    stakeNow <= bankrollCOP
  const canMarkTaken =
    stakeNow != null && stakeNow > 0 && bankrollOk

  return (
    <div className="mt-3 space-y-2 border-t border-violet-100 pt-3 text-[11px]">
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[10px] font-medium text-sky-950">
          Por piernas: {outcomeLabel(c.outcome_from_legs)}
        </span>
        <span className="rounded-full border border-violet-300 bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-950">
          Efectivo: {outcomeLabel(c.outcome_effective)}
        </span>
      </div>
      <p className="text-[10px] leading-relaxed text-app-muted">
        Si no tocas el cierre, cuenta el resultado lógico de las piernas. El
        monto de la combinada sigue tu bankroll (menú lateral); sugerencia
        conservadora abajo.
      </p>
      {range && (
        <p className="text-[10px] text-violet-900/90">
          Rango sugerido (combinada):{' '}
          <span className="font-mono tabular-nums">
            {formatCOP(range.min)} – {formatCOP(range.max)}
          </span>
        </p>
      )}
      {midSuggestion != null && (
        <button
          type="button"
          disabled={disabled}
          className="rounded-md border border-violet-400 bg-violet-50 px-2 py-1 text-[10px] font-semibold text-violet-900 disabled:opacity-40"
          onClick={() => {
            const v = midSuggestion
            setCopDraft(String(v))
            setCopHint({
              tone: 'ok',
              message: 'Sugerencia aplicada; luego puedes marcar «Sí, la tomé».',
            })
            onSave({ ...baseCombo(c), stake_amount: v })
          }}
        >
          Usar sugerencia (media): {formatCOP(midSuggestion)}
        </button>
      )}

      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[5rem_1fr] sm:items-start sm:gap-2">
        <span className="text-app-muted sm:pt-1.5">
          Monto COP <span className="text-red-600">*</span>
        </span>
        <div className="min-w-0">
          <input
            type="text"
            inputMode="numeric"
            className="w-full rounded-md border border-app-line bg-white px-2 py-1.5 font-mono text-[11px] tabular-nums shadow-sm"
            placeholder="Antes de marcar tomada"
            value={copDraft}
            onChange={(e) => {
              setCopDraft(e.target.value.replace(/[^\d]/g, ''))
              setCopHint(null)
            }}
            onBlur={() => {
              const raw = copDraft.trim()
              const n = raw === '' ? null : Number.parseInt(raw, 10)
              if (raw !== '' && (n === null || Number.isNaN(n))) return
              if (
                n != null &&
                n > 0 &&
                bankrollCOP != null &&
                bankrollCOP > 0 &&
                n > bankrollCOP
              ) {
                setCopHint({
                  tone: 'risk',
                  message: 'El monto no puede superar tu bankroll.',
                })
                return
              }
              if ((n == null || n <= 0) && c.user_taken === true) {
                setCopHint({
                  tone: 'warn',
                  message:
                    'Sin monto válido no puede quedar tomada. Se guardó como no tomada.',
                })
                onSave({ ...baseCombo(c), stake_amount: n, taken: false })
                return
              }
              const assess =
                n != null && n > 0 && bankrollCOP != null && bankrollCOP > 0
                  ? stakeAssessmentCOP(n, bankrollCOP, COMBO_TIER)
                  : n != null && n > 0
                    ? stakeAssessmentCOP(n, 0, COMBO_TIER)
                    : null
              setCopHint(
                assess?.message
                  ? { tone: assess.tone, message: assess.message }
                  : null,
              )
              onSave({ ...baseCombo(c), stake_amount: n })
            }}
            disabled={disabled}
          />
          {copHint && (
            <p
              className={`mt-1 text-[10px] ${
                copHint.tone === 'risk'
                  ? 'text-red-700'
                  : copHint.tone === 'warn'
                    ? 'text-amber-800'
                    : 'text-emerald-800'
              }`}
            >
              {copHint.message}
            </p>
          )}
        </div>
      </label>

      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[5rem_1fr] sm:items-center sm:gap-2">
        <span className="text-app-muted">¿La tomé?</span>
        <select
          className="rounded-md border border-app-line bg-white px-2 py-1.5 shadow-sm"
          value={
            c.user_taken === true ? 'yes' : c.user_taken === false ? 'no' : ''
          }
          onChange={(e) => {
            const v = e.target.value
            if (v === '') return
            if (v === 'yes' && !canMarkTaken) {
              setCopHint({
                tone: 'warn',
                message:
                  'Primero un monto COP mayor a 0 o pulsa la sugerencia.',
              })
              return
            }
            setCopHint(null)
            onSave({ ...baseCombo(c), taken: v === 'yes' })
          }}
          disabled={disabled}
        >
          <option value="">—</option>
          <option value="no">No</option>
          <option value="yes" disabled={!canMarkTaken}>
            Sí
            {!canMarkTaken
              ? stakeNow != null &&
                  stakeNow > 0 &&
                  bankrollCOP != null &&
                  bankrollCOP > 0 &&
                  stakeNow > bankrollCOP
                ? ' (monto > bankroll)'
                : ' (monto y bankroll)'
              : ''}
          </option>
        </select>
      </label>

      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[5rem_1fr] sm:items-center sm:gap-2">
        <span className="text-app-muted">Cierre</span>
        <select
          className="rounded-md border border-app-line bg-white px-2 py-1.5 shadow-sm"
          value={
            c.user_outcome === 'win' ||
            c.user_outcome === 'loss' ||
            c.user_outcome === 'pending'
              ? c.user_outcome
              : 'auto'
          }
          onChange={(e) => {
            const v = e.target.value
            if (v === 'auto') {
              onSave({ ...baseCombo(c), userOutcome: 'auto' })
              return
            }
            onSave({
              ...baseCombo(c),
              userOutcome: v as 'win' | 'loss' | 'pending',
            })
          }}
          disabled={disabled}
        >
          <option value="auto">Auto (desde piernas)</option>
          <option value="win">Gané (yo)</option>
          <option value="loss">Perdí (yo)</option>
          <option value="pending">Pendiente (yo)</option>
        </select>
      </label>
    </div>
  )
}
