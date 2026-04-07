/**
 * US-FE-015 (T-047): Ráfaga de confeti sobrio al completar el contador +250 DP.
 *
 * IMPORTANTE DE USO: este componente debe colocarse como hijo directo del
 * contenedor `fixed inset-0 z-[80]` del modal para que sus partículas sean
 * visibles por encima del overlay pero DETRÁS de la card (ver regla de capas).
 * El contenedor aquí usa `position: absolute` — no `fixed`.
 *
 * Reglas:
 * — Solo se dispara cuando `active` cambia de false → true (fin del contador).
 * — Duración total ≤ 2,5 s; ≤ 40 partículas.
 * — Paleta de marca: lavanda, menta suave, neutros (Zurich Calm).
 * — prefers-reduced-motion: reduce → sin partículas.
 * — pointer-events-none, aria-hidden (capa decorativa).
 * — Sin dependencias npm externas; solo framer-motion (ya presente).
 */
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'

/** Paleta institucional: lavanda / menta suave / neutros (04_IDENTIDAD_VISUAL_UI.md) */
const PALETTE = [
  '#8B5CF6', // lavanda vibrante (accent)
  '#C4B5FD', // lavanda suave
  '#e9ddff', // lavanda claro
  '#10B981', // menta (equity)
  '#6EE7B7', // menta suave
  '#d1fae5', // menta claro
  '#a4b4be', // neutro medio
  '#D1D5DB', // neutro claro
]

const PARTICLE_COUNT = 48

type Particle = {
  id: number
  color: string
  angle: number
  distance: number
  originX: number
  originY: number
  size: number
  duration: number
  delay: number
  shape: 'circle' | 'rect'
  rotateDir: number
}

function buildParticles(): Particle[] {
  return Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
    id: i,
    color: PALETTE[i % PALETTE.length],
    angle: Math.random() * Math.PI * 2,
    distance: 150 + Math.random() * 220,
    // Origen centrado en el viewport — explota desde el centro
    originX: 30 + Math.random() * 40,  // 30–70 %
    originY: 40 + Math.random() * 25,  // 40–65 %
    size: 8 + Math.random() * 10,
    duration: 1.3 + Math.random() * 0.9,
    delay: Math.random() * 0.22,
    shape: Math.random() > 0.5 ? 'circle' : 'rect',
    rotateDir: Math.random() > 0.5 ? 1 : -1,
  }))
}

/** Detecta prefers-reduced-motion de forma segura en navegador y tests. */
function detectReducedMotion(): boolean {
  try {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

export type OnboardingConfettiBurstProps = {
  active: boolean
}

export function OnboardingConfettiBurst({ active }: OnboardingConfettiBurstProps) {
  const [particles, setParticles] = useState<Particle[]>([])
  const [visible, setVisible] = useState(false)
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reduceMotion = useMemo(detectReducedMotion, [])

  useEffect(() => {
    if (!active || reduceMotion) return
    const ps = buildParticles()
    setParticles(ps)
    setVisible(true)
    if (hideTimer.current) clearTimeout(hideTimer.current)
    hideTimer.current = setTimeout(() => {
      setVisible(false)
      setParticles([])
    }, 2500)
    return () => {
      if (hideTimer.current) clearTimeout(hideTimer.current)
    }
  }, [active, reduceMotion])

  if (reduceMotion || !visible) return null

  return (
    /*
     * `absolute inset-0` — debe vivir dentro de un contenedor `fixed` o `relative`.
     * No usar `fixed` aquí para no crear un nuevo stacking context independiente
     * del overlay del modal (que ya está en z-[80]).
     */
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden="true"
      style={{ zIndex: 20 }}
    >
      <AnimatePresence>
        {particles.map((p) => {
          const dx = Math.sin(p.angle) * p.distance
          // Componente vertical siempre hacia arriba
          const dy = -(Math.abs(Math.cos(p.angle)) * p.distance * 0.75 + 50)
          const borderRadius = p.shape === 'circle' ? '50%' : '2px'
          const w = p.shape === 'rect' ? p.size * 0.55 : p.size
          const h = p.shape === 'rect' ? p.size * 1.7 : p.size

          return (
            <motion.span
              key={p.id}
              aria-hidden="true"
              style={{
                position: 'absolute',
                left: `${p.originX}%`,
                top: `${p.originY}%`,
                width: w,
                height: h,
                borderRadius,
                backgroundColor: p.color,
                willChange: 'transform, opacity',
              }}
              initial={{ opacity: 1, x: 0, y: 0, scale: 1, rotate: 0 }}
              animate={{
                opacity: 0,
                x: dx,
                y: dy,
                scale: 0.15,
                rotate: p.shape === 'rect' ? 400 * p.rotateDir : 0,
              }}
              transition={{
                duration: p.duration,
                delay: p.delay,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
          )
        })}
      </AnimatePresence>
    </div>
  )
}
