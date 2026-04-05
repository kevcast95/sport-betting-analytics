import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Bt2ShieldCheckIcon } from '@/components/icons/bt2Icons'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import {
  DIAGNOSTIC_INITIAL_INTEGRITY,
  OPERATOR_PROFILE_LABEL_ES,
  computeOperatorProfile,
  disciplinePointsPreview,
  integrityAfterAnswer,
  type OperatorProfileId,
} from '@/lib/diagnosticScoring'
import { useUserStore } from '@/store/useUserStore'

const ACCENT = '#6d3bd7'
const ADVANCE_MS = 800

type IconKind =
  | 'sliders'
  | 'shield'
  | 'logout'
  | 'calm'
  | 'bolt'
  | 'search'
  | 'scale'
  | 'eye_off'
  | 'mask'

function DiagIcon({
  kind,
  className,
}: {
  kind: IconKind
  className?: string
}) {
  const stroke = {
    stroke: 'currentColor',
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    fill: 'none',
  }
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={28}
      height={28}
      aria-hidden
    >
      {kind === 'sliders' && (
        <>
          <path d="M4 7h16M4 12h10M4 17h14" {...stroke} />
          <circle cx="16" cy="7" r="2" {...stroke} />
          <circle cx="14" cy="12" r="2" {...stroke} />
          <circle cx="18" cy="17" r="2" {...stroke} />
        </>
      )}
      {kind === 'shield' && <path d="M12 3l7 4v6c0 5-3 8-7 8s-7-3-7-8V7l7-4z" {...stroke} />}
      {kind === 'logout' && (
        <>
          <path d="M10 5H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h4" {...stroke} />
          <path d="M15 16l4-4-4-4" {...stroke} />
          <path d="M19 12H9" {...stroke} />
        </>
      )}
      {kind === 'calm' && (
        <>
          <circle cx="12" cy="12" r="9" {...stroke} />
          <path d="M9 10h.01M15 10h.01M8.5 15c1.2 1.5 3.2 2 3.5 2s2.3-.5 3.5-2" {...stroke} />
        </>
      )}
      {kind === 'bolt' && <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" {...stroke} />}
      {kind === 'search' && (
        <>
          <circle cx="11" cy="11" r="6" {...stroke} />
          <path d="M20 20l-4-4" {...stroke} />
        </>
      )}
      {kind === 'scale' && (
        <>
          <path d="M12 3v18M5 8l7-3 7 3" {...stroke} />
          <path d="M7 15h10" {...stroke} />
        </>
      )}
      {kind === 'eye_off' && (
        <>
          <path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 3.2 2.2M9.9 5.1A10.3 10.3 0 0 1 12 5c5 0 9 4 9 7a9.7 9.7 0 0 1-4.2 4.3" {...stroke} />
          <path d="M6.4 6.4C4.2 7.8 3 10.3 3 12c0 3 4 7 9 7 .8 0 1.6-.1 2.4-.3" {...stroke} />
        </>
      )}
      {kind === 'mask' && (
        <>
          <ellipse cx="12" cy="12" rx="8" ry="6" {...stroke} />
          <path d="M8 12h2M14 12h2" {...stroke} />
        </>
      )}
    </svg>
  )
}

const PROFILE_BLURB_ES: Record<OperatorProfileId, string> = {
  THE_GUARDIAN:
    'Priorizas la mitigación del riesgo frente a la expansión agresiva. El perfil actual señala alta integridad del sistema.',
  THE_SNIPER:
    'Equilibrio entre protocolo y ejecución. Ajustas con datos y evitas extremos innecesarios en la conducta.',
  THE_VOLATILE:
    'Mayor exposición a impulso y varianza. La vista previa refleja más fricción: conviene anclar el tamaño y el ritual.',
}

function tierFromIntegrity(integrity: number): string {
  if (integrity >= 0.94) return 'TIER III'
  if (integrity >= 0.88) return 'TIER II'
  return 'TIER I'
}

function operatorStatusCode(integrity: number, hasSlice: boolean): string {
  if (!hasSlice) return 'CALIBRATING_V0'
  if (integrity >= 0.92) return 'STABLE_V4'
  if (integrity >= 0.82) return 'STABLE_V2'
  return 'VOLATILE_PROBE'
}

type QuestionDef = {
  dimension: string
  quote: string
  prompt: string
  options: [string, string, string]
  icons: [IconKind, IconKind, IconKind]
}

const QUESTIONS: QuestionDef[] = [
  {
    dimension: 'Nominalidad',
    quote:
      'La disciplina del tamaño importa más que el acierto aislado: el borde está en repetir el proceso, no en forzar el retorno.',
    prompt:
      'Te sugieren una ganancia de 5.000 COP por un nivel de riesgo dado. ¿Qué haces?',
    options: [
      'Respeto el monto sugerido',
      'Subo la apuesta para ganar más',
      'Busco un pick más arriesgado',
    ],
    icons: ['scale', 'bolt', 'search'],
  },
  {
    dimension: 'Tilt',
    quote:
      'El mercado es un mecanismo para transferir capital del impaciente al paciente.',
    prompt:
      'Perdiste al minuto 90. Cinco minutos después, ¿cuál es tu reacción más probable?',
    options: [
      'Cierro la app o acepto la varianza',
      'Busco un evento en vivo para recuperar',
      'Duplico el stake en la siguiente jugada',
    ],
    icons: ['calm', 'search', 'bolt'],
  },
  {
    dimension: 'Intuición',
    quote:
      'Sin marco, la intuición es ruido; con marco, la intuición es hipótesis a contrastar.',
    prompt: 'Hay un favorito claro pero sin datos suficientes. ¿Operas?',
    options: [
      'No opero sin marco',
      'Meto fuerte por instinto',
      'Meto por emoción / narrativa',
    ],
    icons: ['shield', 'bolt', 'mask'],
  },
  {
    dimension: 'Drawdown',
    quote:
      'El mercado es un mecanismo para transferir capital del impaciente al paciente.',
    prompt: 'Tu capital baja un 5% en la semana. ¿Primer ajuste?',
    options: [
      'Recalibrar unidad de stake',
      'Mantengo todo igual',
      'Aumento el riesgo para recuperar',
    ],
    icons: ['sliders', 'shield', 'logout'],
  },
  {
    dimension: 'Honestidad',
    quote:
      'Registrar el desvío es el primer paso para recuperar el control estadístico.',
    prompt:
      'Te diste cuenta de que apostaste por encima de tu plan. ¿Qué haces?',
    options: [
      'Lo registro y asumo el desvío',
      'Lo ignoro si la jugada ganó',
      'Intento compensar en silencio',
    ],
    icons: ['scale', 'eye_off', 'mask'],
  },
]

function FooterStatusBar() {
  const stroke = {
    stroke: 'currentColor',
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    fill: 'none',
  }
  return (
    <footer className="pointer-events-none fixed bottom-0 left-0 z-50 flex w-full justify-center bg-gradient-to-t from-[#f6fafe] via-[#f6fafe]/90 to-transparent px-4 pb-8 pt-12">
      <div className="pointer-events-auto flex flex-wrap items-center justify-center gap-8 rounded-full border border-[#a4b4be]/15 bg-white/80 px-6 py-3 shadow-sm backdrop-blur-md sm:gap-12 sm:px-8">
        <div className="flex items-center gap-2 text-[#26343d]">
          <svg className="text-[#6d3bd7]" viewBox="0 0 24 24" width={18} height={18} aria-hidden>
            <path d="M4 18V6M8 14v4M12 8v10M16 12v6M20 6v12" {...stroke} />
          </svg>
          <span className="font-mono text-[10px] font-semibold uppercase tracking-widest">
            Estado técnico: nominal
          </span>
        </div>
        <div className="flex items-center gap-2 opacity-30">
          <Bt2ShieldCheckIcon className="h-[18px] w-[18px]" />
          <span className="font-mono text-[10px] font-semibold uppercase tracking-widest">
            Integridad del sistema
          </span>
        </div>
        <div className="flex items-center gap-2 opacity-30">
          <svg viewBox="0 0 24 24" width={18} height={18} aria-hidden>
            <path
              d="M12 3a7 7 0 0 0-7 7c0 4 3 9 7 11 4-2 7-7 7-11a7 7 0 0 0-7-7z"
              {...stroke}
            />
            <circle cx="12" cy="10" r="2" {...stroke} />
          </svg>
          <span className="font-mono text-[10px] font-semibold uppercase tracking-widest">
            ID operador
          </span>
        </div>
      </div>
    </footer>
  )
}

export default function DiagnosticPage() {
  const navigate = useNavigate()
  const hasCompletedDiagnostic = useUserStore((s) => s.hasCompletedDiagnostic)
  const completeDiagnostic = useUserStore((s) => s.completeDiagnostic)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)

  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<(0 | 1 | 2)[]>([])
  const [integrity, setIntegrity] = useState(DIAGNOSTIC_INITIAL_INTEGRITY)
  const [pendingOption, setPendingOption] = useState<0 | 1 | 2 | null>(null)
  const [highlightedOption, setHighlightedOption] = useState<0 | 1 | 2 | null>(
    null,
  )
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  useEffect(() => {
    return () => {
      if (advanceTimer.current) clearTimeout(advanceTimer.current)
    }
  }, [])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const previewIntegrity = useMemo(() => {
    if (pendingOption == null) return integrity
    return integrityAfterAnswer(integrity, pendingOption)
  }, [integrity, pendingOption])

  const previewProfile = useMemo(() => {
    const slice =
      pendingOption == null ? answers : [...answers, pendingOption]
    if (slice.length === 0) return null
    return computeOperatorProfile(slice)
  }, [answers, pendingOption])

  const previewDp = useMemo(
    () => disciplinePointsPreview(disciplinePoints, previewIntegrity),
    [disciplinePoints, previewIntegrity],
  )

  const progressPct = ((step + 1) / QUESTIONS.length) * 100

  const flushAdvance = useCallback(
    (opt: 0 | 1 | 2) => {
      const nextIntegrity = integrityAfterAnswer(integrity, opt)
      const nextAnswers = [...answers, opt]
      if (nextAnswers.length >= QUESTIONS.length) {
        const profile = computeOperatorProfile(nextAnswers)
        completeDiagnostic({
          profile,
          systemIntegrity: nextIntegrity,
        })
        navigate('/v2/sanctuary', { replace: true })
        return
      }
      setAnswers(nextAnswers)
      setIntegrity(nextIntegrity)
      setStep((s) => s + 1)
      setPendingOption(null)
      setHighlightedOption(null)
    },
    [answers, completeDiagnostic, integrity, navigate],
  )

  const onSelectOption = (opt: 0 | 1 | 2) => {
    if (pendingOption != null) return
    setHighlightedOption(opt)
    setPendingOption(opt)
    if (advanceTimer.current) clearTimeout(advanceTimer.current)
    advanceTimer.current = setTimeout(() => {
      advanceTimer.current = null
      flushAdvance(opt)
    }, ADVANCE_MS)
  }

  const onExitFocus = () => {
    const dirty = step > 0 || answers.length > 0 || pendingOption != null
    if (
      dirty &&
      !window.confirm(
        '¿Salir del diagnóstico? Perderás el progreso de esta sesión.',
      )
    ) {
      return
    }
    if (advanceTimer.current) {
      clearTimeout(advanceTimer.current)
      advanceTimer.current = null
    }
    navigate('/v2/session', { replace: true })
  }

  if (hasCompletedDiagnostic) {
    return <Navigate to="/v2/sanctuary" replace />
  }

  const q = QUESTIONS[step]
  const hasPreviewSlice =
    pendingOption != null ? answers.length + 1 > 0 : answers.length > 0
  const integrityPercent = Math.round(previewIntegrity * 100)
  const tier = tierFromIntegrity(previewIntegrity)
  const statusCode = operatorStatusCode(previewIntegrity, hasPreviewSlice)

  const profileTitle =
    previewProfile != null
      ? OPERATOR_PROFILE_LABEL_ES[previewProfile]
      : 'Calibrando…'
  const profileBlurb =
    previewProfile != null
      ? `${PROFILE_BLURB_ES[previewProfile]} Señal actual: ${integrityPercent}% integridad.`
      : 'Selecciona una opción para asignar un perfil preliminar y ver la integridad en tiempo real.'

  const identitySection: ReactNode = (
    <section
      className="mt-20 border-t border-[#a4b4be]/10 pt-14 sm:mt-24 sm:pt-16"
      aria-label="Perfil operador en evolución"
    >
      <div className="flex flex-col items-center">
        <span
          className="mb-8 font-mono text-[10px] font-semibold uppercase tracking-widest text-[#52616a]"
          style={monoStyle}
        >
          Perfil operador en evolución
        </span>
        <div className="grid w-full grid-cols-1 gap-8 md:grid-cols-2">
          {/* Tarjeta identidad / asignación de perfil (ref: Identity Badge) */}
          <div className="flex items-center gap-6 rounded-xl bg-[#eef4fa] p-8">
            <div className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#6d3bd7]">
              <div
                className="absolute inset-0 opacity-35 mix-blend-overlay"
                style={{
                  background:
                    'linear-gradient(135deg, #e9ddff 0%, #612aca 50%, #26343d 100%)',
                }}
              />
              <Bt2ShieldCheckIcon className="relative z-10 h-9 w-9 text-white" />
            </div>
            <div className="min-w-0">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <h3 className="text-xl font-bold tracking-tight text-[#26343d]">
                  {profileTitle}
                </h3>
                <span
                  className="rounded-full bg-[#6d3bd7]/10 px-2 py-0.5 font-mono text-[10px] font-bold tracking-tighter text-[#6d3bd7]"
                  style={monoStyle}
                >
                  {tier}
                </span>
              </div>
              <p className="max-w-[280px] text-sm leading-relaxed text-[#52616a]">
                {profileBlurb}
              </p>
            </div>
          </div>
          {/* Tarjeta stats técnicos (ref: Technical Stats) */}
          <div className="space-y-4 rounded-xl bg-[#eef4fa] p-8">
            <div className="flex items-end justify-between border-b border-[#a4b4be]/10 pb-2">
              <span
                className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[#52616a]"
                style={monoStyle}
              >
                Integridad del sistema
              </span>
              <span
                className="font-mono text-lg font-bold text-[#6d3bd7]"
                style={monoStyle}
              >
                {previewIntegrity.toFixed(3)}
              </span>
            </div>
            <div className="flex items-end justify-between border-b border-[#a4b4be]/10 pb-2">
              <span
                className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[#52616a]"
                style={monoStyle}
              >
                Puntos de disciplina
              </span>
              <div className="flex items-center gap-2">
                <Bt2ShieldCheckIcon className="h-4 w-4 shrink-0 text-[#6d3bd7]" />
                <span
                  className="font-mono text-lg font-bold text-[#26343d]"
                  style={monoStyle}
                >
                  {previewDp.toLocaleString('es-CO')} XP
                </span>
              </div>
            </div>
            <div className="flex items-end justify-between border-b border-[#a4b4be]/10 pb-2">
              <span
                className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[#52616a]"
                style={monoStyle}
              >
                Estado operador
              </span>
              <span
                className="font-mono text-xs font-bold text-[#914d00]"
                style={monoStyle}
              >
                {statusCode}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )

  return (
    <div className="relative min-h-[100dvh] w-full min-w-0 bg-[#f6fafe] text-[#26343d]">
      <div
        className="fixed left-0 top-0 z-[60] h-1 w-full bg-[#e5eff7]"
        aria-hidden
      >
        <div
          className="h-full transition-[width] duration-500 ease-out"
          style={{
            width: `${progressPct}%`,
            backgroundColor: ACCENT,
            boxShadow: '0 0 12px rgba(139, 92, 246, 0.3)',
          }}
        />
      </div>

      <header className="fixed top-0 z-50 flex w-full items-center justify-between border-b-[0.5px] border-[#8B5CF6]/15 bg-[#f6fafe]/80 px-6 py-4 backdrop-blur-md sm:px-8">
        <span
          className="text-xs font-semibold uppercase tracking-[0.05em] text-[#52616a]"
          style={monoStyle}
        >
          Diagnóstico de identidad
        </span>
        <span className="text-sm font-semibold tracking-tight text-[#26343d]">
          Paso {String(step + 1).padStart(2, '0')} /{' '}
          {String(QUESTIONS.length).padStart(2, '0')}
        </span>
        <button
          type="button"
          className="rounded-xl px-4 py-1.5 text-sm font-medium text-[#52616a] transition-colors hover:bg-[#eef4fa]"
          onClick={onExitFocus}
        >
          Salir del foco
        </button>
      </header>

      <main className="mx-auto w-full max-w-4xl px-6 pb-40 pt-24">
        <section className="mt-10 space-y-8 sm:mt-12">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="space-y-6 px-2 text-center sm:px-8 md:px-12">
                <blockquote className="text-lg font-light italic leading-relaxed text-[#52616a]">
                  «{q.quote}»
                </blockquote>
                <p
                  className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6d3bd7]"
                  style={monoStyle}
                >
                  {q.dimension}
                </p>
                <h1 className="text-2xl font-bold leading-snug tracking-tight text-[#26343d] sm:text-3xl">
                  {q.prompt}
                </h1>
              </div>
              <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-4">
                {q.options.map((label, idx) => {
                  const opt = idx as 0 | 1 | 2
                  const selected = highlightedOption === opt
                  return (
                    <button
                      key={label}
                      type="button"
                      disabled={pendingOption != null}
                      onClick={() => onSelectOption(opt)}
                      className={[
                        'group relative flex flex-col items-center justify-center rounded-xl border border-[#a4b4be]/20 bg-white p-8 text-center transition-all duration-300',
                        'hover:border-[#6d3bd7]/40 hover:bg-[#e9ddff]/10',
                        selected
                          ? 'border-[#8B5CF6] shadow-[inset_0_0_0_1px_rgba(139,92,246,0.5)]'
                          : '',
                      ].join(' ')}
                    >
                      <DiagIcon
                        kind={q.icons[idx]}
                        className={[
                          'mb-4 text-[#6d3bd7] opacity-60 transition-opacity',
                          'group-hover:opacity-100',
                          selected ? 'opacity-100' : '',
                        ].join(' ')}
                      />
                      <span className="text-sm font-semibold uppercase tracking-wide text-[#26343d]">
                        {label}
                      </span>
                      <div
                        className="pointer-events-none absolute inset-0 rounded-xl border-2 border-[#6d3bd7] opacity-0 transition-opacity group-focus-visible:opacity-100"
                        aria-hidden
                      />
                    </button>
                  )
                })}
              </div>
            </motion.div>
          </AnimatePresence>
        </section>

        {identitySection}
      </main>

      <FooterStatusBar />
    </div>
  )
}
