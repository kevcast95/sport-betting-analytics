/**
 * US-FE-016 (T-048): Guiones de tours contextuales por vista.
 *
 * Cada script tiene 2–5 pasos con copy en español.
 * Mencionar DP explícitamente en vistas con economía (Bóveda, Liquidación, Cierre).
 * Coherencia con US-FE-012 en vistas que hablen de "día" (Santuario, Cierre).
 */
import type { TourRouteKey } from '@/store/useTourStore'

export type TourStep = {
  id: string
  title: string
  body: string[]
  /** Dato destacado con tipografía Geist Mono */
  highlight?: { label: string; value: string }
}

export type TourScript = {
  routeKey: TourRouteKey
  title: string
  steps: TourStep[]
}

const TOUR_SANCTUARY: TourScript = {
  routeKey: 'sanctuary',
  title: 'Cómo funciona el Santuario',
  steps: [
    {
      id: 'sanctuary-overview',
      title: 'El panel de control del búnker',
      body: [
        'El Santuario es tu punto de aterrizaje diario. Aquí ves el estado de tu patrimonio operativo, la integridad del protocolo y el progreso de misiones.',
        'No es un dashboard de resultados — es un espejo de tu disciplina.',
      ],
    },
    {
      id: 'sanctuary-dp',
      title: 'Riqueza de carácter y DP',
      body: [
        'El indicador de Discipline Points (DP) refleja tu coherencia operativa, no tu capital real. Un saldo alto de DP significa que estás siguiendo el protocolo.',
        'Cada liquidación registrada acredita DP en el servidor (+10 si ganancia, +5 si pérdida). El saldo total sigue otras reglas del protocolo cuando el backend las activa.',
      ],
      highlight: { label: 'DP por liquidación (ganada / perdida)', value: '+10 / +5 DP' },
    },
    {
      id: 'sanctuary-day',
      title: 'El día operativo y la gracia',
      body: [
        'El día operativo sigue el calendario local. A medianoche, el sistema evalúa si tienes picks pendientes o la estación sin cerrar.',
        'Tienes 24 horas de gracia para resolver pendientes del día anterior. Pasado ese tiempo, se aplican consecuencias de disciplina.',
      ],
      highlight: { label: 'Ventana de gracia', value: '24 h' },
    },
  ],
}

const TOUR_VAULT: TourScript = {
  routeKey: 'vault',
  title: 'Cómo funciona La Bóveda',
  steps: [
    {
      id: 'vault-overview',
      title: 'Picks con valor esperado positivo',
      body: [
        'La Bóveda muestra las señales del día generadas por el modelo canónico CDM. Cada pick tiene una clase de mercado y una traducción humana.',
        'Solo los picks del día actual aparecen en el feed activo; los del día anterior quedan bloqueados.',
      ],
    },
    {
      id: 'vault-unlock',
      title: 'Desbloqueo con Discipline Points',
      body: [
        'Hay picks estándar (sin gastar DP) y premium (−50 DP al tomarlos; umbral configurable). El coste se muestra en cada tarjeta.',
        'Desbloquear no garantiza profit — garantiza acceso a más contexto. La disciplina del tamaño y el registro sigue siendo tuya.',
      ],
      highlight: { label: 'Coste premium al tomar pick', value: '50 DP' },
    },
    {
      id: 'vault-settle',
      title: 'Liquidar para ganar DP',
      body: [
        'Después de desbloquear un pick, debes liquidarlo en la Terminal de Liquidación cuando conozcas el resultado.',
        'Cada liquidación completada con reflexión suma DP a tu saldo: +10 DP si ganancia, +5 DP si pérdida. El protocolo importa más que el resultado.',
      ],
      highlight: { label: 'DP por liquidación ganada', value: '+10 DP' },
    },
  ],
}

// ─────────────────────────────────────────
// Lote A (T-054): Liquidación + Cierre del día
// ─────────────────────────────────────────

const TOUR_SETTLEMENT: TourScript = {
  routeKey: 'settlement',
  title: 'Cómo funciona la liquidación',
  steps: [
    {
      id: 'settlement-overview',
      title: 'La terminal de auditoría',
      body: [
        'Aquí cierras cada posición: declaras el resultado (Ganancia, Pérdida o Empate) y reconcilias el impacto en tu bankroll.',
        'El encabezado muestra el evento (equipos y competición) y el mercado en español. La "Sugerencia del modelo" es la tesis operativa del sistema CDM.',
      ],
    },
    {
      id: 'settlement-odds',
      title: 'Cuota sugerida vs cuota en tu casa',
      body: [
        'El sistema muestra la "Cuota decimal sugerida" del modelo. Introduce la cuota que realmente tomaste en tu casa para ver si está Alineada, Cercana o Desviada.',
        'Si tu cuota difiere notablemente, el sistema lo indica antes de confirmar. El PnL se calcula con tu cuota real si la introduces.',
      ],
      highlight: { label: 'Tolerancia de alineación', value: '≤ 0.02' },
    },
    {
      id: 'settlement-reflection',
      title: 'Reflexión post-partido',
      body: [
        'Escribe tu estado emocional y decisiones clave de la sesión (mínimo 10 caracteres). Esto alimenta tu índice de equilibrio emocional.',
        'Una reflexión genuina te ayuda a identificar patrones de comportamiento que los números solos no revelan.',
      ],
      highlight: { label: 'DP por liquidación (ganancia / pérdida)', value: '+10 / +5 DP' },
    },
  ],
}

const TOUR_DAILY_REVIEW: TourScript = {
  routeKey: 'daily-review',
  title: 'Cómo funciona el cierre del día',
  steps: [
    {
      id: 'daily-overview',
      title: 'El análisis post-sesión',
      body: [
        'Al finalizar el día, reconcilias tu saldo real contra el proyectado por el sistema. Esto detecta discrepancias y cierra la estación operativa.',
        'El cierre es obligatorio — sin él, el sistema aplica consecuencias de disciplina tras la ventana de gracia de 24 horas.',
      ],
      highlight: { label: 'Ventana para cerrar', value: '24 h de gracia' },
    },
    {
      id: 'daily-reconciliation',
      title: 'Reconciliación de capital',
      body: [
        'Introduce el saldo real de tu casa de apuestas. El sistema compara con el proyectado y te pide una nota aclaratoria si la diferencia supera el 1 %.',
        'Esta verificación protege la integridad del ledger y evita distorsiones en tus métricas de ROI.',
      ],
    },
    {
      id: 'daily-discipline',
      title: 'Disciplina del día y cierre',
      body: [
        'El score de disciplina refleja cuántas liquidaciones completaste y la calidad de tu reflexión. No mide si ganaste o perdiste.',
        'Al confirmar el cierre, la estación se bloquea para el resto del día calendario. Mañana empieza un nuevo ciclo limpio.',
      ],
    },
  ],
}

// ─────────────────────────────────────────
// Lote B (T-055): Ledger, Rendimiento, Perfil, Ajustes
// ─────────────────────────────────────────

const TOUR_LEDGER: TourScript = {
  routeKey: 'ledger',
  title: 'Cómo funciona el ledger',
  steps: [
    {
      id: 'ledger-overview',
      title: 'El libro de auditoría',
      body: [
        'El ledger es el historial completo de tus liquidaciones. Cada fila representa una posición cerrada con su resultado, reflexión y marca de tiempo.',
        'Es la fuente de verdad de todas tus métricas: ROI, win rate y factor de disciplina se calculan desde aquí.',
      ],
    },
    {
      id: 'ledger-filters',
      title: 'Filtrar y buscar entradas',
      body: [
        'Filtra por clase de mercado para analizar segmentos específicos de tu actividad. Usa la búsqueda por ID para localizar posiciones concretas.',
        'El análisis por segmento revela dónde tu protocolo es más consistente y dónde hay margen de mejora.',
      ],
    },
    {
      id: 'ledger-discipline',
      title: 'Factor total de disciplina',
      body: [
        'La barra de factor de disciplina refleja tu consistencia operativa sobre el historial total. Sube con DP acumulados y se escala de 0 a 10.',
        'Este indicador no depende del resultado monetario: puedes tener buen factor con pérdidas si seguiste el protocolo.',
      ],
    },
  ],
}

const TOUR_PERFORMANCE: TourScript = {
  routeKey: 'performance',
  title: 'Cómo leer el rendimiento',
  steps: [
    {
      id: 'performance-metrics',
      title: 'Los cuatro indicadores clave',
      body: [
        'ROI global, tasa de éxito, caída máxima y DP ganados son los pilares del análisis ejecutivo. Cada uno mide un aspecto distinto de tu operativa.',
        'Un buen operador equilibra los cuatro: rentabilidad sin exposición excesiva y disciplina consistente.',
      ],
    },
    {
      id: 'performance-equity',
      title: 'La curva de equity',
      body: [
        'La curva muestra la evolución de tu capital en función de las liquidaciones. Una curva ascendente y suave indica protocolo sólido.',
        'Los picos abruptos o caídas bruscas señalan sesiones fuera de parámetros. Alterna entre escala lineal y logarítmica para distintas perspectivas.',
      ],
    },
    {
      id: 'performance-protocol',
      title: 'Checklist del Protocolo Alpha',
      body: [
        'El checklist valida que los tres pilares del protocolo estén activos: liquidez de mercado, varianza aceptable y preparación psicológica.',
        'Si algún pilar está pendiente, el sistema lo señala para que tomes acción antes de operar.',
      ],
    },
  ],
}

const TOUR_PROFILE: TourScript = {
  routeKey: 'profile',
  title: 'Cómo funciona tu perfil',
  steps: [
    {
      id: 'profile-overview',
      title: 'Tu identidad operativa',
      body: [
        'El perfil refleja tu posición en el sistema: rango, racha activa y perfil diagnóstico calibrado en el cuestionario inicial.',
        'No es un perfil de redes sociales — es un mapa de tu conducta operativa a lo largo del tiempo.',
      ],
    },
    {
      id: 'profile-dp',
      title: 'Puntos de disciplina y nivel',
      body: [
        'Tu saldo de DP determina tu nivel (Novato → Sentinel → Elite → Master). Cada nivel desbloquea picks de mayor acceso en La Bóveda.',
        'Los DP se acumulan liquidando, cerrando el día y reflexionando. No tienen vencimiento.',
      ],
      highlight: { label: 'Próximo nivel', value: 'Sentinel · 1500 DP' },
    },
    {
      id: 'profile-recalibration',
      title: 'Recalibración del diagnóstico',
      body: [
        'Después de 30 días y 50 liquidaciones, podrás recalibrar tu perfil diagnóstico para reflejar la evolución de tu conducta.',
        'La recalibración no borra el historial — ajusta el perfil con datos más maduros.',
      ],
    },
  ],
}

const TOUR_SETTINGS: TourScript = {
  routeKey: 'settings',
  title: 'Ajustes del entorno',
  steps: [
    {
      id: 'settings-overview',
      title: 'Configuración del protocolo',
      body: [
        'Los ajustes del entorno te permiten gestionar preferencias y reiniciar datos locales. El capital de trabajo y el stake se configuran desde el modal de tesorería.',
        'Los cambios aquí no afectan tu historial de liquidaciones ni tus DP acumulados.',
      ],
    },
    {
      id: 'settings-reset',
      title: 'Reinicio de datos locales',
      body: [
        'El reinicio borra el estado local del búnker (sesión, ledger, perfil). Úsalo solo si necesitas empezar un ciclo completamente nuevo.',
        'Esta acción es irreversible. Todos tus DP, liquidaciones y configuraciones se perderán.',
      ],
    },
  ],
}

export const TOUR_SCRIPTS: Record<string, TourScript> = {
  sanctuary: TOUR_SANCTUARY,
  vault: TOUR_VAULT,
  settlement: TOUR_SETTLEMENT,
  'daily-review': TOUR_DAILY_REVIEW,
  ledger: TOUR_LEDGER,
  performance: TOUR_PERFORMANCE,
  profile: TOUR_PROFILE,
  settings: TOUR_SETTINGS,
}

export function getTourScript(routeKey: TourRouteKey): TourScript | null {
  return TOUR_SCRIPTS[routeKey] ?? null
}
