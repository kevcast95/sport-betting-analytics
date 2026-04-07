/**
 * US-FE-011 (T-041) + US-FE-015 (T-047): Cierre de onboarding fase A.
 *
 * Muestra una única vez (tras confirmar Treasury por primera vez):
 * — Copy de logro ganado: "Te lo has ganado" + explicación de los 4 hitos.
 * — Resumen visual de hitos completados.
 * — Contador animado de abono único +250 DP.
 * — Ráfaga de confeti sobrio (US-FE-015) al completar el contador.
 * — Botón para continuar al tour de economía (fase B).
 *
 * Reglas de identidad: Zurich Calm; sin confeti en otros flujos (US-FE-015 §2).
 */
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { OnboardingConfettiBurst } from '@/components/OnboardingConfettiBurst'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { ONBOARDING_DP_GRANT } from '@/store/useUserStore'

export type OnboardingCompleteModalProps = {
  open: boolean
  operatorName: string | null
  bankrollFormatted: string
  onContinueToTour: () => void
}

const HITOS = [
  {
    key: 'sesion',
    label: 'Identidad confirmada',
    detail: 'Sesión iniciada con nombre de operador.',
  },
  {
    key: 'contrato',
    label: 'Contrato de disciplina firmado',
    detail: 'Los 3 axiomas del protocolo aceptados.',
  },
  {
    key: 'diagnostico',
    label: 'Diagnóstico de identidad completado',
    detail: 'Perfil operativo calibrado.',
  },
  {
    key: 'capital',
    label: 'Capital declarado',
    detail: 'Unidad de riesgo y bankroll configurados.',
  },
]

export function OnboardingCompleteModal({
  open,
  operatorName,
  bankrollFormatted,
  onContinueToTour,
}: OnboardingCompleteModalProps) {
  const [dpCounter, setDpCounter] = useState(0)
  const [counterDone, setCounterDone] = useState(false)

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  // Contador animado de DP al abrir el modal
  useEffect(() => {
    if (!open) {
      setDpCounter(0)
      setCounterDone(false)
      return
    }
    const target = ONBOARDING_DP_GRANT
    const duration = 1200 // ms
    const steps = 40
    const increment = target / steps
    const interval = duration / steps
    let current = 0
    const timer = window.setInterval(() => {
      current += increment
      if (current >= target) {
        setDpCounter(target)
        setCounterDone(true)
        window.clearInterval(timer)
      } else {
        setDpCounter(Math.round(current))
      }
    }, interval)
    return () => window.clearInterval(timer)
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[80] flex items-center justify-center bg-[#05070A]/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="onboarding-phase-a-title"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
        >
          {/*
           * US-FE-015: ráfaga de confeti dentro del overlay (absolute inset-0).
           * Renderizada ANTES del card → z inferior por orden DOM.
           * El card usa relative z-10 para quedar por encima.
           */}
          <OnboardingConfettiBurst active={counterDone} />

          {/* Card en z-10 por encima del confeti */}
          <motion.div
            className="relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-[#a4b4be]/20 bg-[#f6fafe] shadow-2xl"
              initial={{ scale: 0.97, y: 12 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.97, y: 12 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              {/* Cabecera — copy de logro ganado (US-FE-015) */}
              <div className="border-b border-[#e2e8f0] px-8 pt-8 pb-6">
                <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.2em] text-[#8B5CF6]">
                  Reconocimiento ganado
                </p>
                <h2
                  id="onboarding-phase-a-title"
                  className="text-2xl font-extrabold tracking-tight text-[#26343d]"
                >
                  Te lo has ganado
                  {operatorName && (
                    <span className="ml-2 text-[#8B5CF6]">{operatorName}.</span>
                  )}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-[#52616a]">
                  El sistema certifica que completaste los cuatro pilares del blindaje
                  inicial. No es un bono de bienvenida — es el reconocimiento de que
                  construiste la base antes de operar.
                </p>
              </div>

              {/* Hitos completados */}
              <div className="px-8 pt-6 pb-4">
                <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
                  Cuatro pilares certificados
                </p>
                <ul className="space-y-3" role="list">
                  {HITOS.map((h, i) => (
                    <motion.li
                      key={h.key}
                      className="flex items-start gap-3"
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.08, duration: 0.2 }}
                    >
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#8B5CF6]/15 text-[#8B5CF6]">
                        <Bt2ShieldCheckIcon className="h-3.5 w-3.5" />
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-[#26343d]">
                          {h.label}
                        </p>
                        <p className="text-xs text-[#52616a]">
                          {h.key === 'capital' ? bankrollFormatted : h.detail}
                        </p>
                      </div>
                    </motion.li>
                  ))}
                </ul>
              </div>

              {/* Abono de DP — con copy de "ganado" (US-FE-015) */}
              <motion.div
                className="mx-8 mb-6 rounded-xl border border-[#8B5CF6]/20 bg-[#e9ddff]/40 p-5"
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.35, duration: 0.25 }}
              >
                <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
                  Disciplina de fundación
                </p>
                <div className="flex items-center gap-3">
                  <motion.span
                    key={counterDone ? 'done' : 'counting'}
                    className="font-mono text-3xl font-bold tabular-nums text-[#8B5CF6]"
                    style={monoStyle}
                    animate={counterDone ? { scale: [1, 1.08, 1] } : {}}
                    transition={{ duration: 0.35 }}
                  >
                    +{dpCounter}
                  </motion.span>
                  <span
                    className="font-mono text-lg font-bold text-[#8B5CF6]"
                    style={monoStyle}
                  >
                    DP
                  </span>
                  {counterDone && (
                    <motion.span
                      className="text-xs font-semibold text-[#059669]"
                      initial={{ opacity: 0, x: 4 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      ✓ Acreditados
                    </motion.span>
                  )}
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-[#52616a]">
                  Estos {ONBOARDING_DP_GRANT} DP certifican los cuatro hitos: identidad, contrato,
                  diagnóstico y capital. Se acreditan una sola vez. A partir de aquí,
                  cada punto lo gana la disciplina en acción: liquidaciones, cierres y
                  reconciliaciones.
                </p>
              </motion.div>

              {/* Acción */}
              <div className="px-8 pb-8">
                <button
                  type="button"
                  onClick={onContinueToTour}
                  className="w-full rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-3.5 text-sm font-bold text-white shadow-lg shadow-[#8B5CF6]/20 transition-all hover:opacity-95 active:scale-[0.99]"
                >
                  Entender la economía de disciplina →
                </button>
              </div>
            </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
