/**
 * US-FE-016 (T-048): Modal de tour contextual por vista.
 *
 * Motor genérico de pasos para tours de primeras visitas y reaperturas.
 * — "Saltar tour" visible desde el primer paso (US-FE-016 Regla 1).
 * — Máximo 5 pasos; progreso visible.
 * — Copy en español; DP mencionados donde aplique según el guion.
 * — Estética Zurich Calm; sin urgencia ni bloqueo sin salida.
 * — Uso: montar lazy por ruta para no afectar performance global.
 */
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import type { TourStep } from '@/components/tours/tourScripts'

export type ViewTourModalProps = {
  open: boolean
  /** Título del tour (p. ej. "Cómo funciona el Santuario") */
  title: string
  steps: TourStep[]
  onComplete: () => void
}

export function ViewTourModal({
  open,
  title,
  steps,
  onComplete,
}: ViewTourModalProps) {
  const [step, setStep] = useState(0)

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  useEffect(() => {
    if (!open) setStep(0)
  }, [open])

  const current = steps[step]
  const isLast = step === steps.length - 1

  const goNext = () => {
    if (isLast) onComplete()
    else setStep((s) => s + 1)
  }

  if (!current) return null

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[75] flex items-end justify-center bg-[#05070A]/50 p-4 backdrop-blur-[2px] sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-labelledby="view-tour-title"
          aria-describedby="view-tour-step-body"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <motion.div
            className="w-full max-w-sm overflow-hidden rounded-2xl border border-[#a4b4be]/20 bg-[#f6fafe] shadow-2xl"
            initial={{ scale: 0.97, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.97, y: 16 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* Barra de progreso */}
            <div className="h-0.5 w-full bg-[#e2e8f0]">
              <motion.div
                className="h-full bg-[#8B5CF6]"
                initial={false}
                animate={{ width: `${((step + 1) / steps.length) * 100}%` }}
                transition={{ duration: 0.3, ease: 'easeInOut' }}
              />
            </div>

            <div className="px-6 pt-5 pb-2">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-[10px] font-bold uppercase tracking-[0.18em] text-[#8B5CF6]">
                    {title}
                  </p>
                  <span
                    className="font-mono text-[10px] text-[#6e7d86]"
                    style={monoStyle}
                  >
                    {step + 1} / {steps.length}
                  </span>
                </div>
                {/* Saltar — siempre visible (US-FE-016 Regla 1) */}
                <button
                  type="button"
                  onClick={onComplete}
                  className="shrink-0 rounded-lg border border-[#a4b4be]/30 px-2.5 py-1 text-[10px] font-semibold text-[#6e7d86] transition-colors hover:border-[#a4b4be]/60 hover:text-[#52616a]"
                  aria-label="Saltar tour"
                >
                  Saltar
                </button>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={current.id}
                  id="view-tour-step-body"
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -12 }}
                  transition={{ duration: 0.16 }}
                >
                  <h2
                    id="view-tour-title"
                    className="mt-1 text-lg font-extrabold tracking-tight text-[#26343d]"
                  >
                    {current.title}
                  </h2>

                  <div className="mt-3 space-y-2">
                    {current.body.map((p, i) => (
                      <p key={i} className="text-sm leading-relaxed text-[#52616a]">
                        {p}
                      </p>
                    ))}
                  </div>

                  {current.highlight && (
                    <div className="mt-4 flex items-center gap-3 rounded-lg border border-[#8B5CF6]/15 bg-[#e9ddff]/30 px-3 py-2.5">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#8B5CF6]/15 text-[#8B5CF6]">
                        <Bt2ShieldCheckIcon className="h-3.5 w-3.5" />
                      </span>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                          {current.highlight.label}
                        </p>
                        <p
                          className="font-mono text-base font-bold text-[#8B5CF6]"
                          style={monoStyle}
                        >
                          {current.highlight.value}
                        </p>
                      </div>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Acción principal */}
            <div className="px-6 pb-6 pt-4">
              <button
                type="button"
                onClick={goNext}
                className="w-full rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-2.5 text-sm font-bold text-white shadow-md shadow-[#8B5CF6]/15 transition-all hover:opacity-95 active:scale-[0.99]"
              >
                {isLast ? 'Entendido →' : 'Siguiente →'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
