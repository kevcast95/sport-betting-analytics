/**
 * US-FE-029 (T-115): Glosario de términos del protocolo BetTracker 2.
 * Cubre DP, PnL → Resultado neto, Bóveda, Liquidación, Santuario,
 * cuota sugerida, estación, etc.
 */
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'

type GlossaryEntry = {
  term: string
  abbr?: string
  definition: string
  tag?: string
}

const GLOSSARY: GlossaryEntry[] = [
  {
    term: 'Puntos de Disciplina',
    abbr: 'DP',
    definition:
      'Moneda interna del búnker. Representan coherencia operativa, no capital real. El servidor acredita +10 DP por cada liquidación registrada con reflexión (recompensa de gestión, mismo valor para ganancia, pérdida o empate/anulado); onboarding +250 DP una vez. Las señales premium suelen costar −50 DP en un paso de desbloqueo en la bóveda, antes de registrar la posición. Otras reglas (cierre de estación) dependen del despliegue.',
    tag: 'Economía',
  },
  {
    term: 'Resultado neto',
    abbr: 'PnL',
    definition:
      'Diferencia entre el capital apostado y el retorno recibido, expresado en COP. Positivo = ganancia; negativo = pérdida. En el ledger aparece como "Resultado neto (COP)".',
    tag: 'Finanzas',
  },
  {
    term: 'ROI',
    definition:
      'Retorno sobre la inversión acumulada. Se calcula dividiendo el resultado neto total entre la suma de stakes. Un ROI del 5 % significa que por cada 100 COP arriesgados obtuviste 5 COP de ganancia neta.',
    tag: 'Finanzas',
  },
  {
    term: 'Cuota decimal sugerida',
    definition:
      'Referencia del protocolo para la selección (consenso / CDM). Úsala para comparar con la cuota que tomaste en tu casa; la diferencia define alineación (Alineada / Cercana / Desviada). No sustituye una promesa de beneficio (D-06-027).',
    tag: 'Mercado',
  },
  {
    term: 'Cuota en tu casa',
    definition:
      'Precio real que ofrece tu operador. Introduce este valor en la Terminal de Liquidación para que el sistema calcule el PnL con tu precio real y evalúe la alineación.',
    tag: 'Mercado',
  },
  {
    term: 'Valor esperado positivo',
    abbr: '+EV',
    definition:
      'En jerga clásica, +EV describe cuando una probabilidad subjetiva supera la implícita en la cuota. En BT2 el criterio de señal privilegia lectura apoyada en datos e histórico del input y coherencia cuota–narrativa, no maximizar el pago como regla suelta (D-06-027).',
    tag: 'Mercado',
  },
  {
    term: 'Edge',
    definition:
      'Métrica técnica (p. ej. bps) que resume diferencial frente a la implícita del mercado en el input. Es orientativa, no garantía de ganancia ni mandato de “más edge = mejor” frente a la premisa de acierto fundamentado en datos (D-06-027).',
    tag: 'Mercado',
  },
  {
    term: 'La Bóveda',
    definition:
      'Feed diario de picks generados por el modelo CDM. Contiene picks estándar (acceso libre) y premium (requieren DP). Solo muestra picks del día operativo activo.',
    tag: 'Módulo',
  },
  {
    term: 'Vektor',
    definition:
      'Vektor es el nombre del bloque que explica por qué el protocolo sugiere una lectura concreta en la Bóveda. Resume la interpretación sobre el insumo del día (datos y cuotas disponibles para ese partido). La línea de confianza describe la postura del modelo respecto a ese insumo, no garantiza un resultado deportivo ni juzga la calidad de la ingesta. No constituye asesoría financiera ni promesa de ganancia.',
    tag: 'Módulo',
  },
  {
    term: 'Terminal de Liquidación',
    definition:
      'Vista donde registras el resultado de un pick: declaras Ganancia, Pérdida o Empate/Anulado, añades tu cuota real y escribes una reflexión post-partido. Al confirmar, se actualizan tu bankroll y tus DP.',
    tag: 'Módulo',
  },
  {
    term: 'Estación operativa',
    definition:
      'Estado diario del búnker. Al cerrar la estación confirmas que liquidaste todos los picks del día y reconciliaste tu saldo. Las recompensas o penalizaciones DP por cierre/gracia se aplican según reglas del servidor.',
    tag: 'Protocolo',
  },
  {
    term: 'Día operativo',
    definition:
      'Periodo de 24 horas que se reinicia a medianoche en tu zona horaria. El feed de picks, los topes y los cómputos de disciplina siguen este calendario.',
    tag: 'Protocolo',
  },
  {
    term: 'Ventana de gracia',
    definition:
      'Las 24 horas posteriores al cierre del día operativo en las que puedes resolver picks pendientes sin penalización. Pasada esa ventana, el sistema aplica consecuencias de disciplina (−DP).',
    tag: 'Protocolo',
  },
  {
    term: 'Bankroll',
    definition:
      'Capital de trabajo que destinas a las apuestas. Se configura en la sección de Tesorería. El sistema calcula el stake de cada pick como un porcentaje fijo de este capital (riesgo por pick).',
    tag: 'Finanzas',
  },
  {
    term: 'Stake',
    definition:
      'Monto apostado en cada posición, calculado como un porcentaje del bankroll. Ejemplo: bankroll de 500 000 COP con riesgo del 2 % → stake de 10 000 COP por pick.',
    tag: 'Finanzas',
  },
  {
    term: 'CDM',
    definition:
      'Canonical Decision Model: capa analítica que, con datos certificados (CDM / input del día), alimenta el criterio DSR hacia la Bóveda. La intención de producto prioriza lectura coherente con histórico y parámetros enviados al modelo, no perseguir el mayor retorno esperado como único eje (D-06-027).',
    tag: 'Sistema',
  },
]

const TAG_COLORS: Record<string, string> = {
  Economía: 'bg-[#ede9fe] text-[#6d28d9]',
  Finanzas: 'bg-[#d1fae5] text-[#065f46]',
  Mercado: 'bg-[#fef9c3] text-[#854d0e]',
  Módulo: 'bg-[#dbeafe] text-[#1e40af]',
  Protocolo: 'bg-[#fee2e2] text-[#9b1c1c]',
  Sistema: 'bg-[#f3f4f6] text-[#374151]',
}

export type GlossaryModalProps = {
  open: boolean
  onClose: () => void
}

export function GlossaryModal({ open, onClose }: GlossaryModalProps) {
  const [queryRaw, setQueryRaw] = useState('')
  const [queryDebounced, setQueryDebounced] = useState('')

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
    if (!open) {
      setQueryRaw('')
      setQueryDebounced('')
      return
    }
    const t = window.setTimeout(() => {
      setQueryDebounced(queryRaw.trim().toLowerCase())
    }, 220)
    return () => window.clearTimeout(t)
  }, [open, queryRaw])

  const filteredGlossary = useMemo(() => {
    if (!queryDebounced) return GLOSSARY
    return GLOSSARY.filter((entry) => {
      const blob = [
        entry.term,
        entry.abbr ?? '',
        entry.definition,
        entry.tag ?? '',
      ]
        .join(' ')
        .toLowerCase()
      return blob.includes(queryDebounced)
    })
  }, [queryDebounced])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[95] flex items-end justify-center sm:items-center bg-[#05070A]/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Glosario del protocolo"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => {
            if (e.target === e.currentTarget) onClose()
          }}
        >
          <motion.div
            className="relative w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl border border-[#a4b4be]/20 bg-[#f6fafe] shadow-2xl flex flex-col"
            initial={{ scale: 0.97, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.97, y: 16 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[#a4b4be]/15 px-6 py-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8B5CF6]">
                  Protocolo BT2
                </p>
                <h2
                  className="mt-0.5 text-lg font-extrabold tracking-tight text-[#26343d]"
                  style={{ fontFamily: 'Georgia, serif' }}
                >
                  Glosario de términos
                </h2>
              </div>
              <button
                type="button"
                aria-label="Cerrar glosario"
                onClick={onClose}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e2e8f0] text-[#52616a] transition-colors hover:bg-[#cbd5e1] hover:text-[#26343d]"
              >
                <svg viewBox="0 0 16 16" className="h-4 w-4 fill-current">
                  <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto px-6 pb-6 pt-4">
              <label className="mb-4 block">
                <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-[#6e7d86]">
                  Buscar en el glosario
                </span>
                <input
                  type="search"
                  value={queryRaw}
                  onChange={(e) => setQueryRaw(e.target.value)}
                  placeholder="Término o fragmento…"
                  className="w-full rounded-xl border border-[#a4b4be]/25 bg-white px-4 py-2.5 text-sm text-[#26343d] placeholder:text-[#6e7d86]/70 focus:border-[#8B5CF6]/40 focus:outline-none focus:ring-1 focus:ring-[#8B5CF6]/30"
                  autoComplete="off"
                />
              </label>
              {filteredGlossary.length === 0 ? (
                <p className="rounded-xl border border-[#a4b4be]/15 bg-[#eef4fa] px-4 py-6 text-center text-sm text-[#52616a]">
                  Sin coincidencias. Prueba otra palabra clave.
                </p>
              ) : null}
              <div className="space-y-3">
                {filteredGlossary.map((entry) => (
                  <div
                    key={entry.term}
                    className="rounded-xl border border-[#a4b4be]/15 bg-white p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span
                        className="text-sm font-bold text-[#26343d]"
                        style={{ fontFamily: 'Georgia, serif' }}
                      >
                        {entry.term}
                      </span>
                      {entry.abbr && (
                        <span
                          className="font-mono text-xs font-bold text-[#8B5CF6]"
                          style={monoStyle}
                        >
                          ({entry.abbr})
                        </span>
                      )}
                      {entry.tag && (
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TAG_COLORS[entry.tag] ?? 'bg-[#f3f4f6] text-[#374151]'}`}
                        >
                          {entry.tag}
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-[#52616a]">
                      {entry.definition}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
