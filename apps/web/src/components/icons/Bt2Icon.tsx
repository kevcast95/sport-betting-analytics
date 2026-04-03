import type { ReactNode, SVGProps } from 'react'

/** viewBox con margen para que el trazo no se recorte en flex / overflow hidden */
const PADDED_VIEWBOX = '-1.25 -1.25 26.5 26.5'

export type Bt2SvgProps = Omit<SVGProps<SVGSVGElement>, 'children' | 'viewBox'> & {
  children: ReactNode
  title?: string
}

/**
 * Contenedor SVG V2: `overflow-visible`, trazo contenido en 24×24 con padding en viewBox.
 */
export function Bt2Svg({
  className = '',
  children,
  title,
  ...rest
}: Bt2SvgProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={PADDED_VIEWBOX}
      fill="none"
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      className={`pointer-events-none block shrink-0 overflow-visible text-current ${className}`.trim()}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  )
}
