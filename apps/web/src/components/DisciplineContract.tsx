import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'

type DisciplineContractProps = {
  open: boolean
  /**
   * Se dispara al completar los 3 axiomas y presionar el compromiso con el protocolo.
   */
  onCommitted: () => void
}

function AxiomCard({
  title,
  description,
  checked,
  onChange,
}: {
  title: string
  description: string
  checked: boolean
  onChange: (next: boolean) => void
}) {
  return (
    <label
      className={[
        'group flex cursor-pointer items-start gap-4 rounded-2xl p-5 transition-all',
        checked
          ? 'bg-[#eef4fa] border border-[#8B5CF6]/30'
          : 'bg-white/0 border border-transparent hover:bg-[#eef4fa] hover:border-[#a4b4be]/30',
      ].join(' ')}
    >
      <div className="mt-1">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="h-5 w-5 rounded border-[#a4b4be] text-[#8B5CF6] focus:ring-[#8B5CF6]/20 bg-[#f6fafe]"
        />
      </div>
      <div className="flex-1">
        <p className="font-semibold text-[#26343d] group-hover:text-[#8B5CF6] transition-colors">
          {title}
        </p>
        <p className="mt-1 text-sm leading-relaxed text-[#52616a]">
          {description}
        </p>
      </div>
    </label>
  )
}

/**
 * Solo montado cuando el modal está abierto: estado inicial limpio sin efectos de reset.
 */
function DisciplineContractPanel({ onCommitted }: { onCommitted: () => void }) {
  const [checks, setChecks] = useState({
    ledger: false,
    stakes: false,
    emotional: false,
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        console.warn(
          '[BT2] Observabilidad: intento de cerrar el contrato con Escape (modal bloqueado).',
        )
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const allAccepted = checks.ledger && checks.stakes && checks.emotional

  const axioms = useMemo(
    () => [
      {
        key: 'ledger' as const,
        title: 'Exactitud absoluta del libro',
        description:
          'Me comprometo a reportar todos los puntos de entrada, precios de cierre y deslizamiento exactamente como ocurren, sin excepciones ni retrasos.',
      },
      {
        key: 'stakes' as const,
        title: 'Adherencia estricta a la cuota recomendada',
        description:
          'No excederé el tamaño de apuesta recomendado calculado por el Sentinel Vault; reconoceré que la sobre-exposición es el catalizador principal del desastre.',
      },
      {
        key: 'emotional' as const,
        title: 'Equilibrio emocional',
        description:
          'Acepto que una secuencia de pérdidas es una certeza matemática. Mantendré el cumplimiento del protocolo durante los drawdowns.',
      },
    ],
    [],
  )

  const commit = () => {
    if (!allAccepted) return
    onCommitted()
  }

  return (
    <motion.section
      className="w-full max-w-3xl rounded-[2rem] border border-[#a4b4be]/20 bg-white/90 p-8 shadow-[0px_20px_40px_rgba(38,52,61,0.04)] backdrop-blur-xl overflow-hidden"
      initial={{ scale: 0.98, y: 8 }}
      animate={{ scale: 1, y: 0 }}
      exit={{ scale: 0.98, y: 8 }}
      transition={{ duration: 0.18 }}
      onMouseDown={(e) => {
        e.stopPropagation()
      }}
    >
      <div className="mb-6 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#eef4fa] px-3 py-1">
          <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#52616a]">
            Protocolo institucional
          </span>
        </div>
        <h2 className="text-3xl font-extrabold tracking-tight text-[#26343d] leading-tight">
          El Contrato de Disciplina
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-[15px] text-[#52616a] leading-relaxed">
          La transparencia es la base del beneficio. Al continuar, alineas tu estrategia con la
          mecánica central del búnker.
        </p>
      </div>

      <div className="space-y-4">
        {axioms.map((a) => (
          <AxiomCard
            key={a.key}
            title={a.title}
            description={a.description}
            checked={checks[a.key]}
            onChange={(next) => setChecks((s) => ({ ...s, [a.key]: next }))}
          />
        ))}
      </div>

      <div className="mt-8 border-t border-[#a4b4be]/20 pt-6">
        <button
          type="button"
          className={[
            'w-full rounded-xl py-4 text-white font-bold transition-all active:scale-95 flex items-center justify-center gap-3',
            'bg-gradient-to-r from-[#8B5CF6] to-[#612aca] shadow-lg shadow-[#8B5CF6]/20',
            allAccepted ? 'hover:translate-y-[-2px]' : 'opacity-60 cursor-not-allowed',
          ].join(' ')}
          disabled={!allAccepted}
          onClick={commit}
        >
          Confirmar el protocolo
          <span aria-hidden className="transition-transform group-hover:translate-x-1">
            →
          </span>
        </button>
      </div>

      <p className="mt-4 text-center text-[11px] text-[#52616a]">
        El modal del contrato está bloqueado: no puedes cerrarlo hasta completar los 3 axiomas.
      </p>
    </motion.section>
  )
}

export function DisciplineContract({ open, onCommitted }: DisciplineContractProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 p-4"
          role="dialog"
          aria-modal="true"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => {
            e.preventDefault()
          }}
        >
          <DisciplineContractPanel onCommitted={onCommitted} />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
