import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { Bt2LockIcon } from '@/components/icons/bt2Icons'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import {
  STAKE_PCT_MAX,
  STAKE_PCT_MIN,
  STAKE_PCT_STEP,
  computeUnitValue,
  parseCopIntegerInput,
} from '@/lib/treasuryMath'
import { useBankrollStore } from '@/store/useBankrollStore'

export type TreasuryModalProps = {
  open: boolean
  onClose: () => void
  /** Si true, no se puede cerrar sin confirmar un capital válido (US-FE-002 Regla 5). */
  blocking: boolean
  /**
   * US-FE-011: callback llamado SOLO tras una confirmación exitosa del capital
   * (no en descartar ni en cierre por backdrop). Permite orquestar el flujo
   * de onboarding en el padre sin acoplar la lógica aquí.
   */
  onConfirm?: () => void
}

export function TreasuryModal({ open, onClose, blocking, onConfirm }: TreasuryModalProps) {
  const confirmedBankrollCop = useBankrollStore((s) => s.confirmedBankrollCop)
  const selectedStakePct = useBankrollStore((s) => s.selectedStakePct)
  const confirmTreasury = useBankrollStore((s) => s.confirmTreasury)

  const [draftBankroll, setDraftBankroll] = useState('')
  const [draftStake, setDraftStake] = useState(selectedStakePct)

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  useEffect(() => {
    if (!open) return
    setDraftStake(selectedStakePct)
    setDraftBankroll(
      confirmedBankrollCop > 0 ? String(Math.round(confirmedBankrollCop)) : '',
    )
  }, [open, confirmedBankrollCop, selectedStakePct])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const bankrollNum = parseCopIntegerInput(draftBankroll)
  const canConfirm = Number.isFinite(bankrollNum) && bankrollNum > 0
  const previewUnit = computeUnitValue(
    Number.isFinite(bankrollNum) ? bankrollNum : 0,
    draftStake,
  )

  const formatCop = (n: number) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(n)

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!canConfirm) return
    confirmTreasury(bankrollNum, draftStake)
    onConfirm?.()
    onClose()
  }

  const onBackdropPointerDown = () => {
    if (!blocking) onClose()
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-[#0a0f12]/40 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="treasury-modal-title"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) onBackdropPointerDown()
          }}
        >
          <motion.div
            className="relative w-full max-w-2xl overflow-hidden rounded-[2rem] border border-white/20 bg-[#f6fafe] shadow-2xl"
            initial={{ scale: 0.98, y: 8 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.98, y: 8 }}
            transition={{ duration: 0.2 }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <form onSubmit={onSubmit}>
              <div className="flex items-start justify-between border-b border-[#ddeaf3] p-8 pb-6">
                <div>
                  <h2
                    id="treasury-modal-title"
                    className="text-2xl font-extrabold tracking-tight text-[#26343d]"
                  >
                    Protocolo de gestión de capital
                  </h2>
                  <p className="mt-1 text-sm text-[#52616a]">
                    Indica tu capital de trabajo en pesos colombianos y el porcentaje que
                    destinas por unidad de riesgo. Cada vez que abras este cuadro debes
                    volver a validar el monto.
                  </p>
                </div>
                <div className="rounded-xl bg-[#eef4fa] p-2 text-[#8B5CF6]">
                  <Bt2LockIcon className="h-6 w-6" />
                </div>
              </div>

              <div className="space-y-8 p-8">
                <section>
                  <label
                    htmlFor="treasury-bankroll"
                    className="mb-3 block text-xs font-bold uppercase tracking-widest text-[#52616a]"
                  >
                    Confirmar capital (COP)
                  </label>
                  <input
                    id="treasury-bankroll"
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="Ej. 5000000"
                    value={draftBankroll}
                    onChange={(e) => setDraftBankroll(e.target.value)}
                    className="w-full rounded-2xl border border-transparent bg-[#ddeaf3]/80 px-5 py-4 text-xl font-bold text-[#26343d] outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa]"
                    style={monoStyle}
                  />
                  {confirmedBankrollCop > 0 && (
                    <p className="mt-2 text-[11px] text-[#52616a]">
                      Último confirmado:{' '}
                      <span className="font-semibold text-[#059669]" style={monoStyle}>
                        {formatCop(confirmedBankrollCop)}
                      </span>
                    </p>
                  )}
                </section>

                <section className="rounded-3xl border border-[#ddeaf3] bg-white/90 p-6">
                  <div className="mb-4 flex items-center justify-between gap-4">
                    <div>
                      <h3 className="text-sm font-bold text-[#26343d]">
                        Unidad de apuesta (riesgo por operación)
                      </h3>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                        Calibración · {STAKE_PCT_MIN}% – {STAKE_PCT_MAX}%
                      </p>
                    </div>
                    <span
                      className="text-2xl font-bold tabular-nums text-[#059669]"
                      style={monoStyle}
                    >
                      {draftStake.toFixed(2)}%
                    </span>
                  </div>
                  <p className="mb-3 text-xs text-[#52616a]">
                    Valor de una unidad (vista previa)
                  </p>
                  <p
                    className="mb-6 text-lg font-bold tabular-nums text-[#059669]"
                    style={monoStyle}
                  >
                    {Number.isFinite(previewUnit)
                      ? formatCop(Math.round(previewUnit))
                      : '—'}
                  </p>
                  <input
                    type="range"
                    min={STAKE_PCT_MIN}
                    max={STAKE_PCT_MAX}
                    step={STAKE_PCT_STEP}
                    value={draftStake}
                    onChange={(e) => setDraftStake(Number(e.target.value))}
                    className="h-2 w-full cursor-pointer accent-[#8B5CF6]"
                    aria-label={`Porcentaje del capital por unidad: ${draftStake.toFixed(2)} por ciento`}
                    aria-valuemin={STAKE_PCT_MIN}
                    aria-valuemax={STAKE_PCT_MAX}
                    aria-valuenow={draftStake}
                  />
                  <div
                    className="mt-2 flex justify-between text-[9px] text-[#52616a]"
                    style={monoStyle}
                  >
                    <span>{STAKE_PCT_MIN}%</span>
                    <span>2,50%</span>
                    <span>{STAKE_PCT_MAX}%</span>
                  </div>
                </section>
              </div>

              <div className="flex gap-3 px-8 pb-8">
                <button
                  type="button"
                  disabled={blocking}
                  onClick={() => !blocking && onClose()}
                  className={[
                    'flex-1 rounded-2xl py-4 text-sm font-bold text-[#26343d] transition-colors',
                    blocking
                      ? 'cursor-not-allowed bg-[#ddeaf3]/50 text-[#52616a]/60'
                      : 'bg-[#d5e5ef] hover:bg-[#ddeaf3]',
                  ].join(' ')}
                >
                  Descartar
                </button>
                <button
                  type="submit"
                  disabled={!canConfirm}
                  className={[
                    'flex-[2] rounded-2xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-4 text-sm font-bold text-white shadow-lg shadow-[#8B5CF6]/20 transition-all',
                    canConfirm
                      ? 'hover:opacity-95 active:scale-[0.99]'
                      : 'cursor-not-allowed opacity-50',
                  ].join(' ')}
                >
                  Confirmar protocolo
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
