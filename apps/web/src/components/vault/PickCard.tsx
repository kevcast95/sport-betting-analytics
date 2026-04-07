/**
 * US-FE-003 / US-FE-025: PickCard unificada para picks mock y API.
 * Acepta tanto VaultPickCdm (mock) como Bt2VaultPickOut (API real).
 */
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
import type { Bt2VaultPickOut } from '@/lib/bt2Types'
import { getMarketLabelEs } from '@/lib/marketLabels'
import { selectStationLocked, useSessionStore } from '@/store/useSessionStore'
import { useTradeStore } from '@/store/useTradeStore'

const KNOB = 40
const PAD = 6

/** Tipo unificado: puede ser un pick del mock o de la API. */
type AnyPick = VaultPickCdm | Bt2VaultPickOut

function isApiPick(p: AnyPick): p is Bt2VaultPickOut {
  return 'accessTier' in p && (p.accessTier === 'standard' || p.accessTier === 'premium')
    && 'eventLabel' in p
}

/** Normaliza cualquier pick a propiedades de display. */
function pickDisplay(p: AnyPick) {
  if (isApiPick(p)) {
    return {
      id: p.id,
      marketLabel: p.marketLabelEs || getMarketLabelEs(p.marketClass),
      marketRaw: p.marketClass,
      selectionSummaryEs: p.selectionSummaryEs,
      eventLabel: p.eventLabel,
      titulo: p.titulo,
      accessTier: p.accessTier as 'standard' | 'premium',
      suggestedDecimalOdds: p.suggestedDecimalOdds,
      edgeBps: p.edgeBps || null,
      traduccionHumana: p.traduccionHumana || null,
      curvaEquidad: p.curvaEquidad?.length > 1 ? p.curvaEquidad : null,
      isAvailable: p.isAvailable,
      externalSearchUrl: p.externalSearchUrl || null,
      unlockCostDp: p.unlockCostDp || VAULT_UNLOCK_COST_DP,
    }
  }
  // Mock pick (VaultPickCdm)
  return {
    id: p.id,
    marketLabel: getMarketLabelEs(p.marketClass),
    marketRaw: p.marketClass,
    selectionSummaryEs: p.selectionSummaryEs,
    eventLabel: p.eventLabel,
    titulo: p.titulo,
    accessTier: p.accessTier as 'open' | 'premium',
    suggestedDecimalOdds: p.suggestedDecimalOdds,
    edgeBps: p.edgeBps,
    traduccionHumana: p.traduccionHumana,
    curvaEquidad: p.curvaEquidad,
    isAvailable: true,
    externalSearchUrl: null,
    unlockCostDp: VAULT_UNLOCK_COST_DP,
  }
}

function isPickFreeAccess(tier: string): boolean {
  return tier === 'standard' || tier === 'open'
}

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
  costDp: number
  onUnlocked: () => void
}

function SlideToUnlock({
  stationLocked,
  insufficientDp,
  costDp,
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
          Se requieren {costDp} DP
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
        Deslizar para desbloquear · {costDp} DP
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
  pick: AnyPick
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
  const d = pickDisplay(pick)
  const insufficient = disciplinePoints < d.unlockCostDp
  const isSettled = useTradeStore((s) => s.settledPickIds.includes(d.id))
  const stationLocked = useSessionStore(selectStationLocked)

  // Para picks API: el link de settlement usa el bt2PickId (si existe en takenApiPicks)
  // La lógica de navegación está en VaultPage que pasa el pick desbloqueado

  return (
    <article
      className="relative flex min-h-[220px] flex-col rounded-xl border border-[#a4b4be]/30 bg-white/85 p-5 shadow-sm"
      data-pick-id={d.id}
    >
      <header className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p
            className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]"
            title={d.marketRaw}
          >
            {d.marketLabel}
          </p>
          {d.selectionSummaryEs ? (
            <p className="mt-0.5 text-xs font-semibold text-[#26343d]">
              {d.selectionSummaryEs}
            </p>
          ) : null}
          <h2 className="mt-1 text-base font-bold leading-snug tracking-tight text-[#26343d]">
            {d.eventLabel}
          </h2>
          <p className="mt-0.5 text-[11px] leading-snug text-[#52616a]">
            {d.titulo}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {d.edgeBps ? (
            <span className="rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] px-2 py-1 font-mono text-xs font-bold tabular-nums text-[#26343d]">
              +{(d.edgeBps / 100).toFixed(2)}%
            </span>
          ) : null}
          {isPickFreeAccess(d.accessTier) ? (
            <span className="rounded-full bg-[#d1fae5] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#065f46]">
              Estándar
            </span>
          ) : (
            <span className="rounded-full bg-[#e9ddff] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#6d3bd7]">
              Premium
            </span>
          )}
          {d.isAvailable === false && (
            <span className="rounded-full bg-[#fee2e2] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#9b1c1c]">
              No disponible
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
          {!isPickFreeAccess(d.accessTier) && (
            <div className="mt-4">
              <SlideToUnlock
                stationLocked={stationLocked}
                insufficientDp={insufficient}
                costDp={d.unlockCostDp}
                onUnlocked={() => onRequestUnlock(d.id)}
              />
            </div>
          )}
        </>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="mt-2 flex flex-1 flex-col gap-3"
        >
          {/* Lectura del modelo */}
          {d.traduccionHumana ? (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[#6e7d86]">
                Lectura del modelo
              </p>
              <p className="text-sm leading-relaxed text-[#26343d]">
                {d.traduccionHumana}
              </p>
            </div>
          ) : null}

          {/* Cuota sugerida + curva (o enlace externo si no hay curva) */}
          <div className="flex items-center gap-4 rounded-lg border border-[#a4b4be]/20 bg-[#f6fafe] px-3 py-2">
            <div>
              <p className="text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                Cuota sugerida
              </p>
              <p className="font-mono text-base font-semibold text-[#26343d]">
                {d.suggestedDecimalOdds.toFixed(2)}
              </p>
            </div>
            {d.curvaEquidad ? (
              <div className="rounded-lg border border-[#a4b4be]/20 bg-[#eef4fa] p-2 flex-1">
                <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#6e7d86]">
                  Curva de equity (CDM)
                </p>
                <EquitySparkline
                  values={d.curvaEquidad}
                  className="h-10 w-full text-[#059669]"
                />
              </div>
            ) : d.externalSearchUrl ? (
              <a
                href={d.externalSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-[#a4b4be]/20 bg-[#eef4fa] p-2 flex-1 text-center text-[10px] font-semibold text-[#6d3bd7] hover:bg-[#e9ddff]/30"
              >
                Ver resultado ↗
              </a>
            ) : null}
          </div>

          {isSettled ? (
            <p className="rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-2 text-center text-xs font-semibold text-[#52616a]">
              Archivado en ledger
            </p>
          ) : (
            <NavLink
              to={`/v2/settlement/${d.id}`}
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
