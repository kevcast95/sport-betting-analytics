import { useId } from 'react'
import type { CSSProperties } from 'react'
import type { EquityPoint } from '@/lib/ledgerAnalytics'

export function EquityChart(props: {
  series: EquityPoint[]
  monoStyle: CSSProperties
  useLog?: boolean
  /** Sin borde ni padding; ocupa el contenedor (p. ej. área h-72 del ref). */
  embed?: boolean
}) {
  const gradId = useId().replace(/:/g, '')

  if (props.series.length < 2) {
    return (
      <div
        className={
          props.embed
            ? 'flex h-full min-h-[12rem] items-center justify-center text-sm text-[#52616a]'
            : 'flex h-48 items-center justify-center rounded-xl border border-dashed border-[#a4b4be]/40 bg-white/60 text-sm text-[#52616a]'
        }
      >
        Liquida picks para ver la curva de equity acumulada.
      </div>
    )
  }

  const w = 560
  const h = 200
  const pad = 24
  const values = props.series.map((p) =>
    props.useLog && p.cumulativePnl > 0
      ? Math.log10(p.cumulativePnl + 1)
      : p.cumulativePnl,
  )
  const minV = Math.min(...values, 0)
  const maxV = Math.max(...values, 1)
  const span = maxV - minV || 1

  const pts = props.series.map((p, i) => {
    const vx =
      props.useLog && p.cumulativePnl > 0
        ? Math.log10(p.cumulativePnl + 1)
        : p.cumulativePnl
    const x = pad + (i / (props.series.length - 1)) * (w - pad * 2)
    const y = h - pad - ((vx - minV) / span) * (h - pad * 2)
    return `${x},${y}`
  })

  const area = `0,${h - pad} ${pts.join(' ')} ${w},${h - pad}`

  const svg = (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={props.embed ? 'h-full w-full' : 'w-full'}
      preserveAspectRatio="xMidYMid meet"
      aria-label="Curva de equity"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#${gradId})`} points={area} />
      <polyline
        fill="none"
        stroke="#8B5CF6"
        strokeWidth="2.5"
        points={pts.join(' ')}
      />
    </svg>
  )

  if (props.embed) {
    return (
      <div className="absolute inset-0 z-[1] flex flex-col justify-end">{svg}</div>
    )
  }

  return (
    <div className="rounded-xl border border-[#a4b4be]/30 bg-white/90 p-4">
      {svg}
      <p className="mt-2 text-[10px] text-[#52616a]" style={props.monoStyle}>
        {props.useLog ? 'Escala log (aprox.)' : 'Escala lineal · PnL acumulado COP'}
      </p>
    </div>
  )
}
