/**
 * US-FE-060 / D-06-041 §2 — mismo texto en Bóveda (lista) y detalle de pick.
 * Énfasis como en DECISIONES.md (negritas en “no garantiza” y “ni”).
 */
export function VektorShortDisclaimer({ className = '' }: { className?: string }) {
  return (
    <p
      role="note"
      className={`text-[11px] leading-relaxed text-[#52616a] ${className}`.trim()}
    >
      La lectura resume por qué se sugiere la señal con los datos del día;{' '}
      <strong className="font-semibold text-[#435368]">no garantiza</strong> el resultado
      del partido{' '}
      <strong className="font-semibold text-[#435368]">ni</strong> constituye asesoría
      financiera.
    </p>
  )
}
