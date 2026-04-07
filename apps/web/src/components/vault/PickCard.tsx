import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import { NavLink } from 'react-router-dom'
import type { VaultPickCdm } from '@/data/vaultMockPicks'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'
import { getMarketLabelEs } from '@/lib/marketLabels'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'

const KNOB = 40
const PAD = 6

function EquitySparkline({
  values,
  className,
}: {
  values: number[]
  className?: string
}) {
  if (values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const w = 240
  const h = 56
  const p = 6
  const span = max - min || 1
  const pts = values.map((v, i) => {
    const x = p + (i / (values.length - 1)) * (w - p * 2)
    const y = h - p - ((v - min) / span) * (h - p * 2)
    return `${x},${y}`
  })
  return (
    <svg
      className={className}
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
        points={pts.join(' ')}
      />
    </svg>
  )
}

type SlideToUnlockProps = {
  stationLocked: boolean
  insufficientDp: boolean
  onUnlocked: () => void
}

function SlideToUnlock({
  stationLocked,
  insufficientDp,
  onUnlocked,
}: SlideToUnlockProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [maxX, setMaxX] = useState(0)
  const x = useMotionValue(0)
  const labelOpacity = useTransform(x, [0, maxX * 0.35], [1, 0.25])

  useLayoutEffect(() => {
    const el = trackRef.current
    if (!el) return
    const measure = () => {
      const w = el.clientWidth
      setMaxX(Math.max(0, w - KNOB - PAD * 2))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const onDragEnd = useCallback(() => {
    const current = x.get()
    const threshold = maxX * 0.88
    if (maxX <= 0 || current < threshold) {
      void animate(x, 0, { type: 'spring', stiffness: 520, damping: 38 })
      return
    }
    onUnlocked()
    void animate(x, 0, { duration: 0.2 })
  }, [maxX, onUnlocked, x])

  if (stationLocked) {
    return (
      <div className="rounded-full border border-[#8B5CF6]/30 bg-[#e9ddff]/25 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-[#6d3bd7]">
          Estación cerrada: sin nuevos desbloqueos hasta el próximo ciclo
        </p>
      </div>
    )
  }

  if (insufficientDp) {
    return (
      <div className="rounded-full border border-[#a4b4be]/40 bg-[#eef4fa]/80 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-[#9e3f4e]">
          Disciplina insuficiente
        </p>
        <p className="mt-1 font-mono text-[10px] tabular-nums text-[#52616a]">
          Se requieren {VAULT_UNLOCK_COST_DP} DP
        </p>
      </div>
    )
  }

  return (
    <div
      ref={trackRef}
      className="relative h-12 w-full overflow-hidden rounded-full border border-[#a4b4be]/35 bg-white/90 shadow-inner"
    >
      <motion.span
        style={{ opacity: labelOpacity }}
        className="pointer-events-none absolute inset-0 flex items-center justify-center px-12 text-center text-[11px] font-bold uppercase tracking-wider text-[#6e7d86]"
      >
        Deslizar para desbloquear · {VAULT_UNLOCK_COST_DP} DP
      </motion.span>
      <motion.div
        className="absolute top-[6px] left-[6px] flex h-10 w-10 cursor-grab items-center justify-center rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#612aca] text-white shadow-md shadow-[#8B5CF6]/25 active:cursor-grabbing"
        style={{ x }}
        drag="x"
        dragConstraints={{ left: 0, right: maxX }}
        dragElastic={0}
        dragMomentum={false}
        onDragEnd={onDragEnd}
        whileTap={{ scale: 0.97 }}
        aria-label="Deslizar para desbloquear pick"
      >
        <span className="text-xs font-bold">→</span>
      </motion.div>
    </div>
  )
}

export type PickCardProps = {
  pick: VaultPickCdm
  isUnlocked: boolean
  disciplinePoints: number
  onRequestUnlock: (pickId: string) => void
}

export function PickCard({
  pick,
  isUnlocked,
  disciplinePoints,
  onRequestUnlock,
}: PickCardProps) {
  const insufficient = disciplinePoints < VAULT_UNLOCK_COST_DP
  const isSettled = useTradeStore((s) => s.settledPickIds.includes(pick.id))
  const stationLocked = useSessionStore(selectStationLocked)
  const marketLabel = getMarketLabelEs(pick.marketClass)

  return (
    <article
      className="relative flex min-h-[220px] flex-col rounded-xl border border-[#a4b4be]/30 bg-white/85 p-5 shadow-sm"
      data-pick-id={pick.id}
    >
      <header className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          {/* US-FE-022/023: mercado en español (código CDM en title para debug) */}
          <p
            className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]"
            title={pick.marketClass}
          >
            {marketLabel}
          </p>
          {/* US-FE-024: selección visible en preview (open y premium desbloqueado) */}
          {pick.selectionSummaryEs ? (
            <p className="mt-0.5 text-xs font-semibold text-[#26343d]">
              {pick.selectionSummaryEs}
            </p>
          ) : null}
          {/* Evento: línea principal legible */}
          <h2 className="mt-1 text-base font-bold leading-snug tracking-tight text-[#26343d]">
            {pick.eventLabel}
          </h2>
          {/* Tesis del modelo como subtítulo */}
          <p className="mt-0.5 text-[11px] leading-snug text-[#52616a]">
            {pick.titulo}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] px-2 py-1 font-mono text-xs font-bold tabular-nums text-[#26343d]">
            +{(pick.edgeBps / 100).toFixed(2)}%
          </span>
          {/* US-FE-023: chip de tier */}
          {pick.accessTier === 'open' ? (
            <span className="rounded-full bg-[#d1fae5] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#065f46]">
              Abierto
            </span>
          ) : (
            <span className="rounded-full bg-[#e9ddff] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#6d3bd7]">
              Premium
            </span>
          )}
        </div>
      </header>

      {!isUnlocked ? (
        <>
          <div className="relative mt-auto min-h-[72px] flex-1 overflow-hidden rounded-lg border border-[#26343d]/10 bg-[#eef4fa]/50">
            <div
              className="pointer-events-none absolute inset-0 flex items-center justify-center p-4 backdrop-blur-md"
              aria-hidden
            >
              <p className="text-center text-xs font-semibold text-[#52616a]">
                Contenido conductual protegido
              </p>
            </div>
          </div>
          <div className="mt-4">
            <SlideToUnlock
              stationLocked={stationLocked}
              insufficientDp={insufficient}
              onUnlocked={() => onRequestUnlock(pick.id)}
            />
          </div>
        </>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="mt-2 flex flex-1 flex-col gap-3"
        >
          {/* US-FE-022/023: "Lectura del modelo" */}
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#6e7d86]">
              Lectura del modelo
            </p>
            <p className="text-sm leading-relaxed text-[#26343d]">
              {pick.traduccionHumana}
            </p>
          </div>
          {/* Cuota sugerida */}
          <div className="flex items-center gap-4 rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] px-3 py-2">
            <div>
              <p className="text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                Cuota sugerida
              </p>
              <p className="font-mono text-base font-semibold text-[#26343d]">
                {pick.suggestedDecimalOdds.toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg border border-[#a4b4be]/20 bg-[#eef4fa] p-2 flex-1">
              <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                Curva de equity (CDM)
              </p>
              <EquitySparkline
                values={pick.curvaEquidad}
                className="h-10 w-full text-[#059669]"
              />
            </div>
          </div>
          {isSettled ? (
            <p className="rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-2 text-center text-xs font-semibold text-[#52616a]">
              Archivado en ledger
            </p>
          ) : (
            <NavLink
              to={`/v2/settlement/${pick.id}`}
              className="block rounded-lg border border-[#8B5CF6]/35 bg-[#e9ddff]/25 py-2.5 text-center text-sm font-bold text-[#6d3bd7] transition-colors hover:bg-[#e9ddff]/45"
            >
              Abrir terminal de liquidación
            </NavLink>
          )}
        </motion.div>
      )}
    </article>
  )
}
