import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import type { VaultPickCdm } from '@/data/vaultMockPicks'
import { VAULT_UNLOCK_COST_DP } from '@/data/vaultMockPicks'

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
  insufficientDp: boolean
  onUnlocked: () => void
}

function SlideToUnlock({ insufficientDp, onUnlocked }: SlideToUnlockProps) {
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

  return (
    <article
      className="relative flex min-h-[220px] flex-col rounded-xl border border-[#a4b4be]/30 bg-white/85 p-5 shadow-sm"
      data-pick-id={pick.id}
    >
      <header className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]">
            {pick.marketClass}
          </p>
          <h2 className="mt-1 text-base font-bold leading-snug tracking-tight text-[#26343d]">
            {pick.titulo}
          </h2>
        </div>
        <span className="shrink-0 rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] px-2 py-1 font-mono text-xs font-bold tabular-nums text-[#26343d]">
          +{(pick.edgeBps / 100).toFixed(2)}%
        </span>
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
          <p className="text-sm leading-relaxed text-[#26343d]">
            {pick.traduccionHumana}
          </p>
          <div className="rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] p-3">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
              Curva de equity (mock CDM)
            </p>
            <EquitySparkline
              values={pick.curvaEquidad}
              className="h-14 w-full text-[#059669]"
            />
          </div>
        </motion.div>
      )}
    </article>
  )
}
