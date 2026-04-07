/**
 * US-FE-022 / US-FE-023: Mapa `marketClass` CDM → etiqueta legible en español.
 * Fuente de verdad única para SettlementPage y PickCard.
 * Los códigos CDM (ML_TOTAL, etc.) solo deben aparecer en tooltip/title o logs.
 */
export const MARKET_LABEL_ES: Record<string, string> = {
  ML_TOTAL:     'Totales (más/menos)',
  ML_SIDE:      'Ganador del partido',
  ML_HOME:      'Victoria local',
  ML_AWAY:      'Victoria visitante',
  SPREAD_HOME:  'Hándicap local',
  SPREAD_AWAY:  'Hándicap visitante',
  TOTAL_OVER:   'Más de (Over)',
  TOTAL_UNDER:  'Menos de (Under)',
  PLAYER_PROP:  'Prop de jugador',
  FIRST_HALF:   'Primer tiempo',
  PARLAY_LEG:   'Pierna de combinada',
  SERIES_PRICE: 'Precio de serie',
  LIVE_ADJ:     'Ajuste en vivo',
  ALT_LINE:     'Línea alternativa',
}

/** Devuelve la etiqueta en español o el código original como fallback. */
export function getMarketLabelEs(marketClass: string): string {
  return MARKET_LABEL_ES[marketClass] ?? marketClass
}
