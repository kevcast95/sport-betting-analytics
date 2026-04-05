import type { CSSProperties } from 'react'

export function RankBadge(props: {
  label: string
  monoStyle: CSSProperties
}) {
  return (
    <span
      className="inline-flex items-center rounded-full border border-[#8B5CF6]/35 bg-[#e9ddff]/30 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#6d3bd7]"
      style={props.monoStyle}
    >
      {props.label}
    </span>
  )
}
