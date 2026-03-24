import { useEffect, useMemo, useState } from 'react'
import type { TrackingBoardOut } from '@/types/api'
import { formatCOP } from '@/lib/formatDateTime'
import { usePickTrackingLock } from '@/lib/pickTrackingLock'
import {
  confidenceTierFromLabel,
  stakeAssessmentCOP,
  suggestedStakeMidCOP,
  suggestedStakeRangeCOP,
  tierLabelEs,
} from '@/lib/stakeSuggestion'

type BoardPick = TrackingBoardOut['picks'][number]

type OddsRef = Record<string, unknown> | null | undefined

function refStr(ref: OddsRef, key: string): string | undefined {
  if (!ref || typeof ref !== 'object') return undefined
  const v = ref[key]
  if (v == null) return undefined
  return String(v)
}

const ORIGIN = ['', 'analizada', 'intuicion', 'impulso'] as const

export type PickSavePayload = {
  pickId: number
  taken: boolean
  decision_origin?: string | null
  stake_amount?: number | null
  userOutcome?: 'auto' | 'win' | 'loss' | 'pending'
}

function baseFromPick(p: BoardPick): PickSavePayload {
  return {
    pickId: p.pick_id,
    taken: p.user_taken ?? false,
    decision_origin: p.decision_origin ?? null,
    stake_amount: p.stake_amount ?? null,
  }
}

function effectiveStakeCOP(
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

/**
 * Orden: contexto bankroll → confianza + sugerencia → monto (+ retorno estimado) → tomé → origen → cierre.
 * «Tomé: Sí» solo si hay monto &gt; 0 (también valida el API).
 */
export function PickTrackingControls({
  pick: p,
  userId,
  bankrollCOP,
  disabled,
  onSave,
}: {
  pick: BoardPick
  userId: number | null
  bankrollCOP: number | null
  disabled?: boolean
  onSave: (payload: PickSavePayload) => void
}) {
  const ref = p.odds_reference as OddsRef
  const conf = refStr(ref, 'confianza')
  const tier = useMemo(() => confidenceTierFromLabel(conf), [conf])
  const range = useMemo(() => {
    if (bankrollCOP == null || bankrollCOP <= 0) return null
    return suggestedStakeRangeCOP(bankrollCOP, tier)
  }, [bankrollCOP, tier])

  const midSuggestion = useMemo(() => {
    if (bankrollCOP == null || bankrollCOP <= 0) return null
    return suggestedStakeMidCOP(bankrollCOP, tier)
  }, [bankrollCOP, tier])

  const [copDraft, setCopDraft] = useState<string>(() =>
    p.stake_amount != null ? String(Math.round(p.stake_amount)) : '',
  )
  useEffect(() => {
    setCopDraft(
      p.stake_amount != null ? String(Math.round(p.stake_amount)) : '',
    )
  }, [p.pick_id, p.stake_amount])

  const [copHint, setCopHint] = useState<{
    tone: 'ok' | 'warn' | 'risk'
    message: string
  } | null>(null)

  const trackingLocked = usePickTrackingLock(p.match_state)

  const stakeNow = useMemo(
    () => effectiveStakeCOP(copDraft, p.stake_amount),
    [copDraft, p.stake_amount],
  )
  const bankrollOk =
    bankrollCOP != null &&
    bankrollCOP > 0 &&
    stakeNow != null &&
    stakeNow <= bankrollCOP
  const canMarkTaken =
    stakeNow != null && stakeNow > 0 && bankrollOk

  const odds = p.picked_value
  const retornoSiGana =
    odds != null &&
    stakeNow != null &&
    stakeNow > 0 &&
    typeof odds === 'number' &&
    !Number.isNaN(odds)
      ? stakeNow * (odds - 1)
      : null

  return (
    <div className="grid gap-2 text-[11px]">
      {userId != null && trackingLocked && (
        <p className="rounded-md border border-neutral-300 bg-neutral-100/90 px-2 py-1.5 text-[10px] leading-relaxed text-neutral-900">
          <strong>Partido finalizado</strong>: no puedes cambiar si tomaste el
          pick ni el monto. Puedes
          seguir ajustando <strong>origen</strong> y <strong>cierre</strong> (resultado).
        </p>
      )}
      {userId == null ? (
        <p className="rounded-md border border-amber-200 bg-amber-50/90 px-2 py-1.5 text-[10px] text-amber-950">
          Elige un <strong>usuario</strong> arriba para guardar seguimiento.
        </p>
      ) : bankrollCOP == null || bankrollCOP <= 0 ? (
        <p className="rounded-md border border-amber-200 bg-amber-50/90 px-2 py-1.5 text-[10px] leading-relaxed text-amber-950">
          Define tu <strong>bankroll</strong> en el menú lateral: así la
          sugerencia de monto se calcula con tu confianza y un % prudente del
          bankroll (solo orientación).
        </p>
      ) : (
        <p className="rounded-md border border-emerald-200/80 bg-emerald-50/70 px-2 py-1.5 text-[10px] leading-relaxed text-emerald-950">
          Tu bankroll de referencia:{' '}
          <span className="font-mono font-semibold tabular-nums">
            {formatCOP(bankrollCOP)}
          </span>
          . El monto del pick debería encajar con la sugerencia; tú decides el
          valor final.
        </p>
      )}

      <div className="rounded-md border border-violet-200/80 bg-violet-50/80 px-2 py-1.5 text-[10px] leading-relaxed text-violet-950">
        <span className="font-medium">{tierLabelEs(tier)}</span>
        {conf ? ` · modelo «${conf}»` : ''}
        {range ? (
          <>
            <br />
            <span className="mt-0.5 inline-block">
              Rango sugerido para este pick:{' '}
              <span className="font-mono font-semibold tabular-nums">
                {formatCOP(range.min)} – {formatCOP(range.max)}
              </span>
            </span>
          </>
        ) : (
          <span className="text-violet-800/90">
            {' '}
            (sin rango numérico sin bankroll.)
          </span>
        )}
        {midSuggestion != null && !trackingLocked && (
          <div className="mt-2">
            <button
              type="button"
              disabled={disabled}
              className="rounded-md border border-violet-400 bg-white px-2 py-1 text-[10px] font-semibold text-violet-900 shadow-sm disabled:opacity-40"
              onClick={() => {
                const v = midSuggestion
                setCopDraft(String(v))
                setCopHint({
                  tone: 'ok',
                  message:
                    'Monto sugerido aplicado; ajústalo si quieres y luego podrás marcar «Tomé: Sí».',
                })
                onSave({ ...baseFromPick(p), stake_amount: v })
              }}
            >
              Usar sugerencia (punto medio): {formatCOP(midSuggestion)}
            </button>
          </div>
        )}
      </div>

      {trackingLocked && p.stake_amount != null && p.stake_amount > 0 && (
        <p className="rounded-md border border-app-line bg-neutral-50 px-2 py-1.5 text-[10px] text-app-muted">
          Monto registrado (solo lectura):{' '}
          <span className="font-mono font-semibold text-app-fg tabular-nums">
            {formatCOP(p.stake_amount)}
          </span>
        </p>
      )}
      {trackingLocked && (
        <p className="text-[10px] text-app-muted">
          ¿Tomaste el pick?{' '}
          <span className="font-medium text-app-fg">
            {p.user_taken === true ? 'Sí' : p.user_taken === false ? 'No' : 'Sin indicar'}
          </span>
        </p>
      )}

      {!trackingLocked && (
      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[4.5rem_1fr] sm:items-start sm:gap-2">
        <span className="text-app-muted sm:pt-1.5">
          Monto COP <span className="text-red-600">*</span>
        </span>
        <div className="min-w-0">
          <input
            type="text"
            inputMode="numeric"
            className="w-full rounded-md border border-app-line bg-white px-2 py-1.5 font-mono text-[11px] tabular-nums shadow-sm"
            placeholder="Antes de «Tomé: Sí»"
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
              if (
                (n == null || n <= 0) &&
                p.user_taken === true
              ) {
                setCopHint({
                  tone: 'warn',
                  message:
                    'Sin monto válido no puede quedar «tomado». Se guardó como no tomado.',
                })
                onSave({ ...baseFromPick(p), stake_amount: n, taken: false })
                return
              }
              const assess =
                n != null && n > 0 && bankrollCOP != null && bankrollCOP > 0
                  ? stakeAssessmentCOP(n, bankrollCOP, tier)
                  : n != null && n > 0
                    ? stakeAssessmentCOP(n, 0, tier)
                    : null
              setCopHint(
                assess?.message
                  ? { tone: assess.tone, message: assess.message }
                  : null,
              )
              onSave({ ...baseFromPick(p), stake_amount: n })
            }}
            disabled={disabled}
          />
          {p.realized_return_cop != null &&
            p.realized_return_cop > 0 &&
            Number.isFinite(p.realized_return_cop) && (
              <p className="mt-1 text-[10px] font-mono font-semibold text-emerald-900 tabular-nums">
                Retorno guardado (ganancia bruta al ganar): +
                {formatCOP(p.realized_return_cop)}
              </p>
            )}
          {retornoSiGana != null && retornoSiGana >= 0 && (
            <p className="mt-1 text-[10px] font-mono text-violet-900 tabular-nums">
              Estimado si aciertas (no se guarda hasta que el pick sea{' '}
              <strong>ganador</strong> efectivo):{' '}
              <span className="font-semibold">
                +{formatCOP(retornoSiGana)}
              </span>
            </p>
          )}
          {copHint && (
            <p
              className={`mt-1 text-[10px] leading-relaxed ${
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
      )}

      {!trackingLocked && (
      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[4.5rem_1fr] sm:items-center sm:gap-2">
        <span className="text-app-muted">Tomé</span>
        <select
          className="rounded-md border border-app-line bg-white px-2 py-1.5 shadow-sm"
          value={
            p.user_taken === true
              ? 'yes'
              : p.user_taken === false
                ? 'no'
                : ''
          }
          onChange={(e) => {
            const v = e.target.value
            if (v === '') return
            if (v === 'yes' && !canMarkTaken) {
              setCopHint({
                tone: 'warn',
                message:
                  'Primero indica un monto en COP mayor a 0 (o usa la sugerencia).',
              })
              return
            }
            setCopHint(null)
            onSave({ ...baseFromPick(p), taken: v === 'yes' })
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
      )}

      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[4.5rem_1fr] sm:items-center sm:gap-2">
        <span className="text-app-muted">Origen</span>
        <select
          className="rounded-md border border-app-line bg-white px-2 py-1.5 shadow-sm"
          value={p.decision_origin ?? ''}
          onChange={(e) => {
            onSave({
              ...baseFromPick(p),
              decision_origin: e.target.value || null,
            })
          }}
          disabled={disabled}
        >
          {ORIGIN.map((x) => (
            <option key={x || 'empty'} value={x}>
              {x || '—'}
            </option>
          ))}
        </select>
      </label>

      <label className="grid grid-cols-1 gap-1 sm:grid-cols-[4.5rem_1fr] sm:items-center sm:gap-2">
        <span className="text-app-muted">Cierre</span>
        <select
          className="rounded-md border border-app-line bg-white px-2 py-1.5 shadow-sm"
          value={
            p.user_outcome === 'win' ||
            p.user_outcome === 'loss' ||
            p.user_outcome === 'pending'
              ? p.user_outcome
              : 'auto'
          }
          onChange={(e) => {
            const v = e.target.value
            if (v === 'auto') {
              onSave({ ...baseFromPick(p), userOutcome: 'auto' })
              return
            }
            onSave({
              ...baseFromPick(p),
              userOutcome: v as 'win' | 'loss' | 'pending',
            })
          }}
          disabled={disabled}
        >
          <option value="auto">Solo auto (sin cierre manual)</option>
          <option value="win">Ganada</option>
          <option value="loss">Perdida</option>
          <option value="pending">Pendiente</option>
        </select>
      </label>
    </div>
  )
}
