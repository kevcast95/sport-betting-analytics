/**
 * Textos fijos en la web (no van a Telegram): explican mercado y selección.
 */

function parseVs(label: string | null | undefined): { home?: string; away?: string } {
  if (!label?.trim()) return {}
  const m = label.split(/\s+vs\.?\s+/i)
  if (m.length >= 2) {
    return { home: m[0].trim(), away: m[1].trim() }
  }
  return {}
}

function normMarket(m: string) {
  return m.trim().toUpperCase().replace(/\s+/g, '')
}

/** Explicación breve sin jerga (tarjetas y ficha). */
export function describeMarketKind(market: string): string {
  const k = normMarket(market)
  const mu = market.toUpperCase()
  if (k === '1X2')
    return 'Aciertas si al terminar el partido gana el local, queda empate o gana el visitante — según lo que elegiste.'
  if (
    k === 'OVERUNDER' ||
    k === 'O/U' ||
    k === 'TOTAL' ||
    k.startsWith('O/U') ||
    (mu.includes('OVER') && mu.includes('UNDER'))
  )
    return 'Apuestas a que habrá más o menos goles (u otra cifra) que el número que marca la casa.'
  if (k === 'BTTS' || k === 'BOTH_TEAMSTOSCORE')
    return 'Apuestas a si los dos equipos anotan al menos un gol, o no.'
  if (k === 'DNB' || k === 'DRAWNOBET')
    return 'Si el partido termina empatado, normalmente te devuelven el dinero de esa apuesta.'
  if (k === 'DOUBLECHANCE' || k === 'DOBLEOPORTUNIDAD')
    return 'Cubres dos resultados posibles del partido en una sola apuesta (por ejemplo local o empate).'
  return `Tipo de apuesta «${market.trim()}». Si no estás segura, revisa cómo lo explica tu casa de apuestas.`
}

/** Qué significa la selección cruda (1, X, Over 2.5, etc.). */
export function describeSelectionPlain(
  market: string,
  selection: string,
  eventLabel?: string | null,
): string {
  const k = normMarket(market)
  const sel = selection.trim()
  const { home, away } = parseVs(eventLabel)

  if (k === '1X2') {
    const u = sel.toUpperCase()
    if (u === '1')
      return home
        ? `Tu apuesta es a que gana ${home} (el que juega de local).`
        : 'Tu apuesta es a que gana el equipo de local.'
    if (u === 'X') return 'Tu apuesta es a que el partido termina empatado.'
    if (u === '2')
      return away
        ? `Tu apuesta es a que gana ${away} (visitante).`
        : 'Tu apuesta es a que gana el equipo visitante.'
  }

  if (
    k === 'OVERUNDER' ||
    k === 'O/U' ||
    k === 'TOTAL' ||
    market.toUpperCase().includes('OVER') ||
    market.toUpperCase().includes('UNDER')
  ) {
    const su = sel.toUpperCase()
    if (su.includes('OVER') || su.startsWith('+'))
      return `Apuestas a que habrá más goles (o más de esa cifra) de lo que indica la línea: ${sel}.`
    if (su.includes('UNDER') || su.startsWith('-'))
      return `Apuestas a que habrá menos goles (o menos de esa cifra) de lo que indica la línea: ${sel}.`
  }

  if (k === 'BTTS') {
    const su = sel.toUpperCase()
    if (su === 'YES' || su === 'SÍ' || su === 'SI')
      return 'Ambos equipos marcan.'
    if (su === 'NO') return 'Al menos uno de los dos no marca.'
  }

  return `En resumen: apuestas a «${sel}» en este mercado.`
}

/** Línea corta para listados (combo legs). */
export function selectionShortLabel(
  market: string,
  selection: string,
  eventLabel?: string | null,
): string {
  const k = normMarket(market)
  const { home, away } = parseVs(eventLabel)
  if (k === '1X2') {
    const u = selection.trim().toUpperCase()
    if (u === '1') return home ? `${home} (local)` : 'Local (1)'
    if (u === 'X') return 'Empate'
    if (u === '2') return away ? `${away} (visita)` : 'Visita (2)'
  }
  return selection.trim()
}
