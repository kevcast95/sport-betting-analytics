/**
 * Mocks CDM para la bóveda V2: sin datos crudos de proveedor ni marcas externas.
 */
export type VaultPickCdm = {
  id: string
  /** Clase de mercado canónica (CDM). */
  marketClass: string
  titulo: string
  edgeBps: number
  /** Solo debe renderizarse en DOM tras desbloqueo. */
  traduccionHumana: string
  curvaEquidad: number[]
}

export const VAULT_UNLOCK_COST_DP = 50

export const vaultMockPicks: VaultPickCdm[] = [
  {
    id: 'v2-p-001',
    marketClass: 'ML_TOTAL',
    titulo: 'Sobrecarga ofensiva vs. defensa cansada',
    edgeBps: 120,
    traduccionHumana:
      'El mercado subestima el ritmo cuando ambos equipos priorizan transición rápida; tu ventaja es asumir más posesiones efectivas de las que precia el cierre.',
    curvaEquidad: [0, 0.4, 0.2, 0.9, 1.1, 0.8, 1.4, 1.2, 1.6],
  },
  {
    id: 'v2-p-002',
    marketClass: 'SPREAD_HOME',
    titulo: 'Local con descanso asimétrico',
    edgeBps: 95,
    traduccionHumana:
      'Condición física y rotación favorecen al local en el tramo final; el spread no refleja el desgaste acumulado del visitante.',
    curvaEquidad: [0, -0.1, 0.3, 0.5, 0.4, 0.7, 0.6, 0.9],
  },
  {
    id: 'v2-p-003',
    marketClass: 'ML_SIDE',
    titulo: 'Sesgo de cierre por noticias tardías',
    edgeBps: 140,
    traduccionHumana:
      'Ajustes tardíos empujaron el precio hacia el favorito público; el valor queda del lado opuesto si la tesis previa sigue intacta.',
    curvaEquidad: [0, 0.2, 0.5, 0.3, 0.8, 1.0, 0.9, 1.3],
  },
  {
    id: 'v2-p-004',
    marketClass: 'TOTAL_UNDER',
    titulo: 'Clima y superficie: menos posesiones limpias',
    edgeBps: 88,
    traduccionHumana:
      'Condiciones que aumentan errores no forzados reducen eficiencia real; el total no incorpora bien esa fricción.',
    curvaEquidad: [0, 0.1, 0.15, 0.35, 0.2, 0.45, 0.5],
  },
  {
    id: 'v2-p-005',
    marketClass: 'PLAYER_PROP',
    titulo: 'Rol ampliado sin repricing',
    edgeBps: 110,
    traduccionHumana:
      'Minutos y uso creador subieron; la línea sigue anclada al rol anterior. La disciplina es no sobre-apostar si el precio alcanza fair.',
    curvaEquidad: [0, -0.2, 0.1, 0.4, 0.2, 0.6, 0.55, 0.7],
  },
  {
    id: 'v2-p-006',
    marketClass: 'ML_AWAY',
    titulo: 'Visitante con matchup de esquemas favorable',
    edgeBps: 72,
    traduccionHumana:
      'El estilo del visitante explota la cobertura del rival; el mercado pondera más el factor cancha que el ajuste táctico.',
    curvaEquidad: [0, 0.05, 0.2, 0.15, 0.35, 0.3, 0.5],
  },
  {
    id: 'v2-p-007',
    marketClass: 'FIRST_HALF',
    titulo: 'Arranque agresivo planificado',
    edgeBps: 99,
    traduccionHumana:
      'Guion de primer cuarto con alta intensidad; las líneas de medio tiempo quedan rezagadas respecto al scouting.',
    curvaEquidad: [0, 0.3, 0.25, 0.5, 0.45, 0.6],
  },
  {
    id: 'v2-p-008',
    marketClass: 'PARLAY_LEG',
    titulo: 'Correlación suave ignorada (una pierna)',
    edgeBps: 65,
    traduccionHumana:
      'Esta pierna comparte varianza con el evento principal; el libro la trata como independiente. Usar tamaño menor.',
    curvaEquidad: [0, -0.05, 0.1, 0.08, 0.2, 0.18, 0.25],
  },
  {
    id: 'v2-p-009',
    marketClass: 'TOTAL_OVER',
    titulo: 'Ritmo proyectado por árbitros y faltas',
    edgeBps: 105,
    traduccionHumana:
      'Tendencia arbitral a cortar juego interior genera más tiros libres y posesiones alargadas; el over está infravalorado.',
    curvaEquidad: [0, 0.2, 0.4, 0.35, 0.55, 0.7, 0.65, 0.85],
  },
  {
    id: 'v2-p-010',
    marketClass: 'SPREAD_AWAY',
    titulo: 'Back-to-back suave para el local',
    edgeBps: 81,
    traduccionHumana:
      'El local viene de viaje corto pero con minutos altos; el visitante entra más fresco de lo que sugiere el precio.',
    curvaEquidad: [0, 0.1, 0.05, 0.25, 0.22, 0.4],
  },
  {
    id: 'v2-p-011',
    marketClass: 'ML_TOTAL',
    titulo: 'Defensa elite vs. volumen exterior',
    edgeBps: 118,
    traduccionHumana:
      'El rival forzará tiros externos de baja calidad; el total asume eficiencia media histórica, no contextual.',
    curvaEquidad: [0, 0.15, 0.35, 0.5, 0.45, 0.75, 0.7, 0.95],
  },
  {
    id: 'v2-p-012',
    marketClass: 'SERIES_PRICE',
    titulo: 'Serie larga: profundidad de banquillo',
    edgeBps: 92,
    traduccionHumana:
      'En series, la rotación manda más que una victoria aislada; el precio del favorito no paga la fatiga acumulada.',
    curvaEquidad: [0, -0.1, 0.05, 0.2, 0.15, 0.35, 0.4],
  },
  {
    id: 'v2-p-013',
    marketClass: 'LIVE_ADJ',
    titulo: 'Inercia del scoreboard vs. métricas de posesión',
    edgeBps: 130,
    traduccionHumana:
      'El marcador arrastra el live, pero los xP (proxy interno CDM) favorecen la remontada medida; operar con calma.',
    curvaEquidad: [0, -0.3, -0.1, 0.2, 0.5, 0.4, 0.8],
  },
  {
    id: 'v2-p-014',
    marketClass: 'ALT_LINE',
    titulo: 'Línea alternativa con cola gruesa',
    edgeBps: 77,
    traduccionHumana:
      'La cola de la distribución no está bien modelada en alt; pequeño edge con varianza alta.',
    curvaEquidad: [0, 0.05, 0.2, 0.1, 0.3, 0.25, 0.35],
  },
  {
    id: 'v2-p-015',
    marketClass: 'ML_SIDE',
    titulo: 'Lesión menor mal ponderada',
    edgeBps: 101,
    traduccionHumana:
      'Baja de rol secundario inflada por narrativa; el reemplazo ya tiene minutos de calidad en el sample.',
    curvaEquidad: [0, 0.1, 0.25, 0.2, 0.45, 0.5, 0.48, 0.65],
  },
  {
    id: 'v2-p-016',
    marketClass: 'TOTAL_UNDER',
    titulo: 'Rival con pérdidas forzadas altas',
    edgeBps: 86,
    traduccionHumana:
      'Presión al balón reduce calidad de ataque; el under es conductual: no perseguir si el total cae demasiado.',
    curvaEquidad: [0, 0.12, 0.18, 0.3, 0.28, 0.42],
  },
  {
    id: 'v2-p-017',
    marketClass: 'SPREAD_HOME',
    titulo: 'Motivación doble y homenaje interno',
    edgeBps: 69,
    traduccionHumana:
      'Factores intangibles empujan esfuerzo defensivo; el modelo CDM los marca como premium pequeño, no certeza.',
    curvaEquidad: [0, 0.08, 0.05, 0.22, 0.2, 0.3],
  },
  {
    id: 'v2-p-018',
    marketClass: 'PLAYER_PROP',
    titulo: 'Uso en clutch sin ajuste de cuota',
    edgeBps: 112,
    traduccionHumana:
      'Cierre ajustado aumenta touches del motor ofensivo; la prop sigue en línea de temporada regular.',
    curvaEquidad: [0, -0.15, 0.1, 0.35, 0.3, 0.55, 0.5, 0.7],
  },
  {
    id: 'v2-p-019',
    marketClass: 'ML_AWAY',
    titulo: 'Desacople entre ranking y forma reciente',
    edgeBps: 94,
    traduccionHumana:
      'El visitante llega en mejor trayectoria que el local; el precio ancla demasiado al seed histórico.',
    curvaEquidad: [0, 0.1, 0.2, 0.15, 0.4, 0.38, 0.55],
  },
  {
    id: 'v2-p-020',
    marketClass: 'FIRST_HALF',
    titulo: 'Guion de estudio en primeros minutos',
    edgeBps: 79,
    traduccionHumana:
      'Ajuste táctico visible en warm-up; el 1H no reacciona hasta que el mercado ve caja en vivo.',
    curvaEquidad: [0, 0.2, 0.18, 0.35, 0.32, 0.48],
  },
]
