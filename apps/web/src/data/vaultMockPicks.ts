/**
 * CDM mock para la bóveda V2: sin datos crudos de proveedor ni marcas externas.
 * US-FE-022 / US-FE-023: tipo ampliado con evento, cuota sugerida y accessTier.
 */

/** Tier de acceso: open = lectura libre sin DP; premium = requiere desbloqueo con DP. */
export type AccessTier = 'open' | 'premium'

export type VaultPickCdm = {
  id: string
  /** Clase de mercado canónica (CDM) — usar `getMarketLabelEs` para mostrar en UI. */
  marketClass: string
  /** Etiqueta de evento legible: "Local vs Visitante · Competición". */
  eventLabel: string
  /** Tesis o narrativa del modelo (subtítulo en terminal de liquidación). */
  titulo: string
  /** Cuota decimal sugerida por el sistema (fuente CDM). Geist Mono en UI. */
  suggestedDecimalOdds: number
  edgeBps: number
  /**
   * Selección concreta de la apuesta en español (US-FE-024).
   * Ej: «Más de 2.5 goles», «Local -0.5 hándicap», «Victoria visitante».
   * Máx. ~80 caracteres.
   */
  selectionSummaryEs: string
  /** Lectura del modelo: se renderiza solo tras desbloqueo. */
  traduccionHumana: string
  curvaEquidad: number[]
  /** Tier de acceso: open = desbloqueado sin coste DP; premium = 50 DP. */
  accessTier: AccessTier
}

export const VAULT_UNLOCK_COST_DP = 50

/**
 * Feed demo: ~7 señales (US-FE-023 §2).
 * - 3 premium (v2-p-001 … v2-p-003): flujo normal de desbloqueo con DP.
 * - 4 open (v2-p-004 … v2-p-007): lectura libre, sin gasto de DP.
 * Los picks premium mantienen los IDs históricos para compatibilidad con tests.
 */
export const vaultMockPicks: VaultPickCdm[] = [
  // ── Premium ──────────────────────────────────────────────────────────────
  {
    id: 'v2-p-001',
    marketClass: 'ML_TOTAL',
    eventLabel: 'Atlético Norte vs Rápidos · Jornada 14',
    titulo: 'Sobrecarga ofensiva vs. defensa cansada',
    suggestedDecimalOdds: 1.87,
    edgeBps: 120,
    selectionSummaryEs: 'Más de 218.5 puntos',
    accessTier: 'premium',
    traduccionHumana:
      'El mercado subestima el ritmo cuando ambos equipos priorizan transición rápida; tu ventaja es asumir más posesiones efectivas de las que precia el cierre.',
    curvaEquidad: [0, 0.4, 0.2, 0.9, 1.1, 0.8, 1.4, 1.2, 1.6],
  },
  {
    id: 'v2-p-002',
    marketClass: 'SPREAD_HOME',
    eventLabel: 'Centauros vs Halcones · Jornada 22',
    titulo: 'Local con descanso asimétrico',
    suggestedDecimalOdds: 1.92,
    edgeBps: 95,
    selectionSummaryEs: 'Local -4.5 puntos',
    accessTier: 'premium',
    traduccionHumana:
      'Condición física y rotación favorecen al local en el tramo final; el spread no refleja el desgaste acumulado del visitante.',
    curvaEquidad: [0, -0.1, 0.3, 0.5, 0.4, 0.7, 0.6, 0.9],
  },
  {
    id: 'v2-p-003',
    marketClass: 'ML_SIDE',
    eventLabel: 'Tigres vs Leones · Jornada 8',
    titulo: 'Sesgo de cierre por noticias tardías',
    suggestedDecimalOdds: 2.10,
    edgeBps: 140,
    selectionSummaryEs: 'Victoria Leones (visitante)',
    accessTier: 'premium',
    traduccionHumana:
      'Ajustes tardíos empujaron el precio hacia el favorito público; el valor queda del lado opuesto si la tesis previa sigue intacta.',
    curvaEquidad: [0, 0.2, 0.5, 0.3, 0.8, 1.0, 0.9, 1.3],
  },
  // ── Open ─────────────────────────────────────────────────────────────────
  {
    id: 'v2-p-004',
    marketClass: 'TOTAL_UNDER',
    eventLabel: 'Cóndores vs Panteras · Jornada 31',
    titulo: 'Clima y superficie: menos posesiones limpias',
    suggestedDecimalOdds: 1.95,
    edgeBps: 88,
    selectionSummaryEs: 'Menos de 42.5 puntos',
    accessTier: 'open',
    traduccionHumana:
      'Condiciones que aumentan errores no forzados reducen eficiencia real; el total no incorpora bien esa fricción.',
    curvaEquidad: [0, 0.1, 0.15, 0.35, 0.2, 0.45, 0.5],
  },
  {
    id: 'v2-p-005',
    marketClass: 'PLAYER_PROP',
    eventLabel: 'Águilas vs Delfines · Jornada 19',
    titulo: 'Rol ampliado sin repricing',
    suggestedDecimalOdds: 1.80,
    edgeBps: 110,
    selectionSummaryEs: 'Jugador 7 — más de 24.5 puntos',
    accessTier: 'open',
    traduccionHumana:
      'Minutos y uso creador subieron; la línea sigue anclada al rol anterior. La disciplina es no sobre-apostar si el precio alcanza fair.',
    curvaEquidad: [0, -0.2, 0.1, 0.4, 0.2, 0.6, 0.55, 0.7],
  },
  {
    id: 'v2-p-006',
    marketClass: 'ML_AWAY',
    eventLabel: 'Víboras vs Gladiadores · Jornada 5',
    titulo: 'Visitante con matchup de esquemas favorable',
    suggestedDecimalOdds: 2.25,
    edgeBps: 72,
    selectionSummaryEs: 'Victoria Gladiadores (visitante)',
    accessTier: 'open',
    traduccionHumana:
      'El estilo del visitante explota la cobertura del rival; el mercado pondera más el factor cancha que el ajuste táctico.',
    curvaEquidad: [0, 0.05, 0.2, 0.15, 0.35, 0.3, 0.5],
  },
  {
    id: 'v2-p-007',
    marketClass: 'TOTAL_OVER',
    eventLabel: 'Gaviotas vs Tormentas · Jornada 27',
    titulo: 'Ritmo proyectado por árbitros y faltas',
    suggestedDecimalOdds: 1.89,
    edgeBps: 99,
    selectionSummaryEs: 'Más de 226.5 puntos',
    accessTier: 'open',
    traduccionHumana:
      'Tendencia arbitral a cortar juego interior genera más tiros libres y posesiones alargadas; el over está infravalorado.',
    curvaEquidad: [0, 0.2, 0.4, 0.35, 0.55, 0.7, 0.65, 0.85],
  },
]
