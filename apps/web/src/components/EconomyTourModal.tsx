/**
 * US-FE-011 (T-042): Tour de economía DP (fase B del onboarding).
 *
 * 4 pasos que explican:
 *  1. ¿Qué son los DP?
 *  2. Picks del día: abiertos vs premium
 *  3. Cómo ganar y gastar DP
 *  4. El día calendario (referencia a US-FE-012)
 *
 * Reglas:
 * — "Entendido, ir al Santuario" visible desde el primer paso (US-FE-011 Regla 2).
 * — Máximo 4 pasos con progreso visible (US-FE-011 §8 mitigación abandono).
 * — Estética Zurich Calm: sin urgencia, tipografía Geist Mono para datos.
 */
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { useUserStore } from '@/store/useUserStore'

export type EconomyTourModalProps = {
  open: boolean
  onComplete: () => void
}

type TourStep = {
  id: string
  title: string
  body: string[]
  highlight?: { label: string; value: string }
}

function buildTourSteps(dpBalance: number): TourStep[] {
  return [
    {
      id: 'que-son-dp',
      title: '¿Qué son los Puntos de Disciplina?',
      body: [
        'Los DP son la moneda interna del búnker. Representan tu coherencia operativa, no tu capital real.',
        'Cuantos más DP acumulas, mayor acceso tienes a las señales y mayores los reconocimientos de protocolo.',
      ],
      highlight: {
        label: 'Tu saldo actual (sincronizado)',
        value: `${dpBalance.toLocaleString('es-CO')} DP`,
      },
    },
    {
      id: 'picks-del-dia',
      title: 'Picks del día: estándar y premium',
      body: [
        'Cada día el sistema genera señales. Las lecturas estándar son accesibles sin coste. Las premium requieren DP.',
        'Con un bajo saldo de DP solo verás el bloque básico. Disciplina sostenida desbloquea análisis más profundos.',
      ],
      highlight: { label: 'Coste de desbloqueo premium', value: '50 DP / pick' },
    },
    {
      id: 'ganar-gastar',
      title: 'Cómo ganar y gastar DP',
      body: [
        'Ganas +10 DP al tomar un pick en la bóveda (registro en protocolo) y +15 DP al liquidar con reflexión (mismo baremo de gestión en ganancia, pérdida o empate/anulado; el servidor acredita). El onboarding abona +250 DP una sola vez.',
        'Gastas DP desbloqueando señales premium en bóveda (−50 DP al desbloqueo, distinto del registro de posición). La clave es el hábito, no el volumen.',
      ],
      highlight: { label: 'DP por tomar + liquidar', value: '+10 + +15' },
    },
    {
      id: 'dia-calendario',
      title: 'El día operativo es el día calendario',
      body: [
        'Los topes de DP y el feed diario se reinician a medianoche en tu zona horaria local.',
        'Si no cierras la estación antes de medianoche, tienes 24 h de gracia. Pasado ese tiempo se aplican consecuencias de disciplina.',
      ],
      highlight: { label: 'Ventana de gracia', value: '24 h' },
    },
  ]
}

export function EconomyTourModal({ open, onComplete }: EconomyTourModalProps) {
  const [step, setStep] = useState(0)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints ?? 0)

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const tourSteps = useMemo(
    () => buildTourSteps(disciplinePoints),
    [disciplinePoints],
  )

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  useEffect(() => {
    if (!open) setStep(0)
  }, [open])

  const current = tourSteps[step]
  const isLast = step === tourSteps.length - 1

  const goNext = () => {
    if (isLast) {
      onComplete()
    } else {
      setStep((s) => s + 1)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[90] flex items-center justify-center bg-[#05070A]/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="economy-tour-title"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <motion.div
            className="relative w-full max-w-md overflow-hidden rounded-2xl border border-[#a4b4be]/20 bg-[#f6fafe] shadow-2xl"
            initial={{ scale: 0.97, y: 10 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.97, y: 10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* Barra de progreso */}
            <div className="h-1 w-full bg-[#e2e8f0]">
              <motion.div
                className="h-full bg-[#8B5CF6]"
                initial={false}
                animate={{
                  width: `${((step + 1) / tourSteps.length) * 100}%`,
                }}
                transition={{ duration: 0.3, ease: 'easeInOut' }}
              />
            </div>

            <div className="px-8 pt-7 pb-2">
              <div className="mb-1 flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8B5CF6]">
                  Economía de disciplina
                </p>
                <span
                  className="font-mono text-[10px] text-[#6e7d86]"
                  style={monoStyle}
                >
                  {step + 1} / {tourSteps.length}
                </span>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={current.id}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.18 }}
                >
                  <h2
                    id="economy-tour-title"
                    className="mt-3 text-xl font-extrabold tracking-tight text-[#26343d]"
                  >
                    {current.title}
                  </h2>

                  <div className="mt-4 space-y-3">
                    {current.body.map((paragraph, i) => (
                      <p
                        key={i}
                        className="text-sm leading-relaxed text-[#52616a]"
                      >
                        {paragraph}
                      </p>
                    ))}
                  </div>

                  {current.highlight && (
                    <div className="mt-5 flex items-center gap-3 rounded-xl border border-[#8B5CF6]/15 bg-[#e9ddff]/35 p-4">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#8B5CF6]/15 text-[#8B5CF6]">
                        <Bt2ShieldCheckIcon className="h-4 w-4" />
                      </span>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                          {current.highlight.label}
                        </p>
                        <p
                          className="font-mono text-lg font-bold text-[#8B5CF6]"
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

            {/* Acciones */}
            <div className="flex flex-col gap-2 px-8 pb-8 pt-5">
              <button
                type="button"
                onClick={goNext}
                className="w-full rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-3 text-sm font-bold text-white shadow-md shadow-[#8B5CF6]/20 transition-all hover:opacity-95 active:scale-[0.99]"
              >
                {isLast ? 'Entendido — ir al Santuario' : 'Siguiente →'}
              </button>
              {/* Regla 2 US-FE-011: salida siempre visible desde el primer paso */}
              <button
                type="button"
                onClick={onComplete}
                className="py-2 text-xs font-semibold text-[#6e7d86] transition-colors hover:text-[#52616a]"
              >
                Saltar tour
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
