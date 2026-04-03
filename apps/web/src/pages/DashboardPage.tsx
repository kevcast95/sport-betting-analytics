import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CardExplain, HelpCueIcon } from '@/components/CardExplain'
import { DashboardPerformanceChart } from '@/components/DashboardPerformanceChart'
import { PickInboxRow } from '@/components/PickInboxRow'
import { fetchJson } from '@/lib/api'
import { useBarDailyRunId } from '@/hooks/useBarDailyRunId'
import { useDashboardUrlState } from '@/hooks/useDashboardUrlState'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { DashboardBundleOut } from '@/types/api'
import { formatCOP } from '@/lib/formatDateTime'

function pct(v: number | null | undefined, digits = 1): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`
}

function pctPlain(v: number | null | undefined, digits = 1): string {
  if (v == null) return '—'
  return `${(v * 100).toFixed(digits)}%`
}

function confidenceFromOddsReference(raw: unknown): string | null {
  if (!raw || typeof raw !== 'object') return null
  const obj = raw as Record<string, unknown>
  const direct = obj.confidence ?? obj.confianza
  if (typeof direct === 'string' && direct.trim().length > 0) return direct.trim()
  return null
}

function confidenceRank(bucket: string): number | null {
  const b = bucket.trim().toLowerCase()
  if (b === 'baja') return 1
  if (b === 'media') return 2
  if (b === 'media-alta' || b === 'media alta') return 3
  if (b === 'alta') return 4
  return null
}

const DASHBOARD_ONBOARDING_COLLAPSED_KEY = 'dashboard_onboarding_collapsed_v1'
/** Migración desde la clave antigua que ocultaba la guía por completo */
const DASHBOARD_ONBOARDING_LEGACY_DISMISSED_KEY = 'dashboard_onboarding_dismissed_v1'

export default function DashboardPage() {
  const { userId } = useTrackingUser()
  const { runDate, sport } = useDashboardUrlState()
  const previewLimit = 5
  const [activeTab, setActiveTab] = useState<'operacion' | 'analitica'>(
    'operacion'
  )
  const [onboardingHydrated, setOnboardingHydrated] = useState(false)
  const [onboardingExpanded, setOnboardingExpanded] = useState(true)
  const [scrollGlossaryAfterAnalitica, setScrollGlossaryAfterAnalitica] = useState(false)

  useEffect(() => {
    try {
      if (localStorage.getItem(DASHBOARD_ONBOARDING_LEGACY_DISMISSED_KEY) === '1') {
        localStorage.setItem(DASHBOARD_ONBOARDING_COLLAPSED_KEY, '1')
        localStorage.removeItem(DASHBOARD_ONBOARDING_LEGACY_DISMISSED_KEY)
      }
      setOnboardingExpanded(localStorage.getItem(DASHBOARD_ONBOARDING_COLLAPSED_KEY) !== '1')
    } catch {
      setOnboardingExpanded(true)
    }
    setOnboardingHydrated(true)
  }, [])

  useEffect(() => {
    if (activeTab !== 'analitica' || !scrollGlossaryAfterAnalitica) return
    const t = window.setTimeout(() => {
      document.getElementById('glosario-metricas')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
      setScrollGlossaryAfterAnalitica(false)
    }, 80)
    return () => window.clearTimeout(t)
  }, [activeTab, scrollGlossaryAfterAnalitica])

  const collapseDashboardOnboarding = () => {
    try {
      localStorage.setItem(DASHBOARD_ONBOARDING_COLLAPSED_KEY, '1')
    } catch {
      /* storage no disponible */
    }
    setOnboardingExpanded(false)
  }

  const expandDashboardOnboarding = () => {
    try {
      localStorage.removeItem(DASHBOARD_ONBOARDING_COLLAPSED_KEY)
    } catch {
      /* ignore */
    }
    setOnboardingExpanded(true)
  }

  const openGlossaryInAnalitica = () => {
    setScrollGlossaryAfterAnalitica(true)
    setActiveTab('analitica')
  }

  const dashQ = useQuery({
    queryKey: ['dashboard', runDate, userId, sport],
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', String(previewLimit))
      sp.set('recent_page', '0')
      if (userId != null) sp.set('user_id', String(userId))
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })
  const takenTodayQ = useQuery({
    queryKey: ['dashboard-taken-today', runDate, userId, sport],
    enabled: userId != null,
    queryFn: async () => {
      const sp = new URLSearchParams({ run_date: runDate, sport })
      sp.set('recent_limit', '20')
      sp.set('recent_page', '0')
      sp.set('only_taken', 'true')
      sp.set('user_id', String(userId))
      return fetchJson<DashboardBundleOut>(`/dashboard?${sp}`)
    },
  })

  const s = dashQ.data?.summary
  const selectedSportRolling = (dashQ.data?.rolling_by_sport ?? []).find(
    (r) => r.sport === sport
  )
  const roi100 = selectedSportRolling?.roi_tradable_100 ?? null
  const dd30 = selectedSportRolling?.drawdown_units_30d ?? null
  const trend = dashQ.data?.calibration?.daily_trend ?? []
  const lastDay = trend.length > 0 ? trend[trend.length - 1] : null
  const prevDay = trend.length > 1 ? trend[trend.length - 2] : null
  const twoRedDays =
    lastDay != null &&
    prevDay != null &&
    (lastDay.roi_unit ?? 0) < 0 &&
    (prevDay.roi_unit ?? 0) < 0
  const mode: 'subir' | 'mantener' | 'bajar' =
    twoRedDays || (roi100 != null && roi100 < 0) || (dd30 != null && dd30 > 10)
      ? 'bajar'
      : roi100 != null && roi100 > 0.1 && (dd30 == null || dd30 <= 6)
        ? 'subir'
        : 'mantener'
  const modeLabel =
    mode === 'subir'
      ? 'Subir exposición (con cuidado)'
      : mode === 'bajar'
        ? 'Bajar exposición'
        : 'Mantener exposición'
  const modeTone =
    mode === 'subir'
      ? 'text-emerald-700 border-emerald-200'
      : mode === 'bajar'
        ? 'text-red-700 border-red-200'
        : 'text-amber-700 border-amber-200'
  const modeCardTone =
    mode === 'subir'
      ? 'border-emerald-200 bg-emerald-50/60'
      : mode === 'bajar'
        ? 'border-red-200 bg-red-50/60'
        : 'border-amber-200 bg-amber-50/60'
  const minBucketSample = 30
  const confidenceRows = dashQ.data?.calibration?.by_confidence ?? []
  const confidenceRowsKnown = confidenceRows
    .map((r) => ({ ...r, rank: confidenceRank(r.bucket) }))
    .filter((r) => r.rank != null)
    .sort((a, b) => (a.rank as number) - (b.rank as number))
  const sufficientSample = confidenceRowsKnown.every((r) => r.settled >= minBucketSample)
  let monotonicOk = true
  for (let i = 1; i < confidenceRowsKnown.length; i += 1) {
    const prev = confidenceRowsKnown[i - 1].hit_rate ?? -1
    const curr = confidenceRowsKnown[i].hit_rate ?? -1
    if (curr < prev) {
      monotonicOk = false
      break
    }
  }
  const calibrationLabel = !sufficientSample
    ? 'Muestra insuficiente'
    : monotonicOk
      ? 'Calibración estable'
      : 'Calibración inestable'
  const calibrationTone = !sufficientSample
    ? 'text-amber-700 border-amber-200'
    : monotonicOk
      ? 'text-emerald-700 border-emerald-200'
      : 'text-red-700 border-red-200'
  const analyticalDecisionHint = !sufficientSample
    ? 'Trata las etiquetas de confianza como orientativas: aún no hay muestra suficiente por bucket.'
    : monotonicOk
      ? 'La confianza ordena el rendimiento como se espera; puedes usarla como apoyo al sizing, sin sustituir el modo del resumen diario.'
      : 'No aumentes el stake basándote solo en la etiqueta de confianza: la calibración no es monótona entre buckets.'

  const { barRunId } = useBarDailyRunId({
    runDate,
    sport,
    primaryDailyRunId: s?.primary_daily_run_id,
  })
  const systemStatus =
    mode === 'subir'
      ? 'AGRESIVO CONTROLADO'
      : mode === 'bajar'
        ? 'DEFENSIVO'
        : 'NEUTRAL'
  const recommendedAction =
    mode === 'subir'
      ? 'Subir stake +10% y mantener límites diarios.'
      : mode === 'bajar'
        ? 'Reducir exposición y bajar stake al 50%.'
        : 'Mantener stake y reevaluar al cierre del día.'
  const topPicksPreview = (dashQ.data?.recent ?? []).slice(0, 5)
  const todayProfitLoss = s?.net_pl_estimate ?? null
  const issuedToday = (dashQ.data?.issued_daily ?? []).find(
    (d) => d.run_date === runDate,
  )
  const feedbackGenerated = issuedToday?.picks_total ?? s?.picks_total ?? 0
  const feedbackTradable = issuedToday?.picks_tradable
  const feedbackMinOdds = s?.min_tradable_odds
  const feedbackAnalysisOnly =
    feedbackTradable != null
      ? Math.max(0, feedbackGenerated - feedbackTradable)
      : null
  const feedbackTradablePct =
    feedbackGenerated > 0 && feedbackTradable != null
      ? Math.round((feedbackTradable / feedbackGenerated) * 100)
      : 0

  return (
    <div>
      {dashQ.isError && (
        <p className="mb-4 text-sm text-app-danger whitespace-pre-wrap">
          {(dashQ.error as Error).message}
        </p>
      )}

      {dashQ.isLoading && (
        <div className="mb-4 rounded-md border border-app-line bg-app-card px-3 py-2 text-sm text-app-muted">
          <p>Cargando resumen…</p>
          <p className="mt-1 text-[11px] leading-relaxed">
            Si se queda así mucho rato: revisa que el API (uvicorn) siga vivo, que la
            web pueda llegar a ese puerto (proxy /{' '}
            <code className="font-mono text-[10px] text-app-fg">VITE_API_BASE_URL</code>
            ), y que ningún otro programa tenga la SQLite bloqueada en escritura
            (p. ej. otro job o herramienta con la base abierta).
          </p>
        </div>
      )}

      {!dashQ.isLoading && onboardingHydrated && (
        <div className="mb-4" id="guia-tablero-dashboard">
          {!onboardingExpanded ? (
            <button
              type="button"
              onClick={expandDashboardOnboarding}
              className="flex w-full items-center justify-between gap-2 rounded-xl border border-violet-200/70 bg-white px-3 py-2.5 text-left text-xs text-violet-950 shadow-sm ring-1 ring-violet-100/40 transition-colors hover:bg-violet-50/60"
              aria-expanded={false}
            >
              <span className="font-serif font-medium tracking-tight">
                Guía rápida · cómo leer el tablero
              </span>
              <span className="shrink-0 text-[10px] font-medium text-violet-700/80">Ampliar</span>
            </button>
          ) : (
            <section
              className="rounded-xl border border-violet-200/70 bg-gradient-to-br from-violet-50/80 to-white p-4 shadow-sm ring-1 ring-violet-100/50"
              aria-label="Guía rápida del dashboard"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="font-serif text-sm font-medium text-violet-950">
                  Guía rápida · cómo leer el tablero
                </p>
                <button
                  type="button"
                  onClick={collapseDashboardOnboarding}
                  className="shrink-0 rounded-md border border-violet-300/60 bg-white px-2 py-1 text-[11px] font-medium text-violet-900 hover:bg-violet-50"
                >
                  Colapsar
                </button>
              </div>
              <ul className="mt-3 list-inside list-disc space-y-1.5 text-[11px] leading-relaxed text-app-muted marker:text-violet-500">
                <li>
                  <strong className="text-app-fg">Fecha y deporte</strong> arriba definen el &quot;día de trabajo&quot;
                  del modelo.
                </li>
                <li>
                  El modelo puede <strong className="text-app-fg">emitir muchos picks</strong>; solo parte suele
                  mostrarse como lista para ejecutar apuestas.
                </li>
                <li>
                  <strong className="text-app-fg">Cuota</strong> es el número junto al pick (p. ej. 1,45). Un{' '}
                  <strong className="text-app-fg">mínimo del día</strong> separa lo que va a la lista operativa de lo
                  que queda como señal interna (&quot;solo análisis&quot;), pero todo cuenta en los totales de generados.
                </li>
                <li>
                  La <strong className="text-app-fg">lista de picks del run</strong> (pantalla donde ves partidos del
                  día y marcas &quot;tomado&quot;) casi siempre muestra solo lo operativo; los de análisis no
                  desaparecen del recuento del modelo.
                </li>
                <li>
                  <strong className="text-app-fg">Tus tomados</strong> son aparte: solo los que marcaste tú; no son el
                  total que emitió el modelo.
                </li>
              </ul>
              <p className="mt-3 text-[11px] text-app-muted">
                Definiciones cortas en{' '}
                <button
                  type="button"
                  onClick={openGlossaryInAnalitica}
                  className="font-medium text-violet-900 underline decoration-violet-300 underline-offset-2 hover:text-violet-950"
                >
                  Glosario (pestaña Modelo · rendimiento)
                </button>
                .
              </p>
            </section>
          )}
        </div>
      )}

      {s && (
        <>
          <section className="mb-6 rounded-2xl border border-violet-200/50 bg-gradient-to-br from-white via-white to-app-accent-soft/80 p-5 shadow-sm ring-1 ring-violet-100/60">
            <p className="font-serif text-xs font-normal uppercase tracking-[0.12em] text-violet-800/70">
              Resumen diario
            </p>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs text-app-muted">Bankroll actual</p>
                <p className="font-mono text-2xl font-semibold tabular-nums text-app-fg">
                  {userId != null && s.bankroll_cop != null ? formatCOP(s.bankroll_cop) : '—'}
                </p>
                <CardExplain summary="Ayuda · bankroll de referencia">
                  <p>
                    {userId != null
                      ? 'Para editar el bankroll de referencia (COP) usa la barra superior bajo el título del dashboard.'
                      : 'Elige un usuario en el menú lateral; el bankroll se edita en la cabecera del dashboard.'}
                  </p>
                </CardExplain>
                <p className="text-xs text-app-muted">
                  Hoy:{' '}
                  <span
                    className={`font-mono ${
                      todayProfitLoss == null
                        ? 'text-app-muted'
                        : todayProfitLoss >= 0
                          ? 'text-emerald-700'
                          : 'text-red-700'
                    }`}
                  >
                    {todayProfitLoss == null
                      ? '—'
                      : `${todayProfitLoss >= 0 ? '+' : ''}${formatCOP(todayProfitLoss)}`}
                  </span>
                </p>
                <p className={`inline-flex rounded border px-2 py-1 text-[11px] font-semibold ${modeTone}`}>
                  Estado: {systemStatus}
                </p>
              </div>
              <div className={`rounded-lg border p-3 ${modeCardTone}`}>
                <p className="text-xs font-semibold text-app-fg">Acción recomendada</p>
                <p className="mt-2 text-sm font-semibold text-app-fg">{modeLabel}</p>
                <p className="mt-1 text-xs text-app-muted">Acción sugerida: {recommendedAction}</p>
                <CardExplain summary="Por qué esta recomendación y siguiente paso">
                  <p>
                    Motivo:{' '}
                    <abbr title="Retorno sobre las últimas ~100 picks tradables (cuota mínima operativa)">ROI100</abbr>{' '}
                    {pct(roi100, 1)} ·{' '}
                    <abbr title="Peor racha acumulada en unidades, ventana ~30 días (tradables)">
                      caída máx. 30d
                    </abbr>{' '}
                    {dd30 ?? '—'}u
                    {twoRedDays ? ' · 2 días rojos seguidos (serie diaria tradable)' : ''}.
                  </p>
                  <p className="mt-2 font-medium text-app-fg">
                    Próximo paso: revisar y cerrar picks en el tablero operativo del día.
                  </p>
                </CardExplain>
                <div className="mt-3 flex flex-wrap gap-2">
                  {barRunId != null && (
                    <Link
                      to={`/runs/${barRunId}/picks`}
                      className="inline-flex items-center rounded-md border border-violet-800 bg-violet-900 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:border-violet-950 hover:bg-violet-950"
                    >
                      Ir al tablero del run
                    </Link>
                  )}
                  <a
                    href="#mis-selecciones"
                    className="inline-flex items-center rounded-md border border-violet-200/80 bg-white/80 px-3 py-1.5 text-xs font-medium text-violet-950 shadow-sm hover:bg-violet-50/90"
                  >
                    Ver mis selecciones
                  </a>
                </div>
              </div>
            </div>
          </section>
<div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-2">
            <div className="rounded-xl border border-app-line bg-app-card p-4">
              <p className="text-xs font-medium text-app-muted">
                Picks del día (modelo) · {runDate}
              </p>
              <CardExplain summary="Qué incluye este número">
                <p>
                  Total emitido por el modelo en la fecha: incluye la <strong className="text-app-fg">lista ejecutable</strong> y
                  los <strong className="text-app-fg">solo análisis</strong>, que siguen contando aunque no aparezcan en
                  el tablero.{' '}
                  {s.picks_total > 0 && feedbackTradable != null ? (
                    <a
                      href="#feedback-dia-modelo"
                      className="font-medium text-violet-900 underline decoration-violet-300 underline-offset-2"
                    >
                      Ver reparto arriba
                    </a>
                  ) : (
                    <>
                      Cuando haya desglose generados / listos para operar, aparecerá el bloque previo con la barra.
                    </>
                  )}
                </p>
              </CardExplain>
              <p className="mt-2 text-2xl font-semibold tabular-nums">
                {s.picks_total}
              </p>
              <p className="mt-1 text-xs text-app-muted">
                {s.outcome_wins} ganados · {s.outcome_losses} perdidos ·{' '}
                {s.outcome_pending} pendientes (todos los picks del día)
              </p>
              <p className="mt-2 border-t border-app-line pt-2 text-[10px] text-app-muted">
                Cerrados (ventana del día):{' '}
                <span className="font-mono text-app-fg">{s.settled_count}</span>
                {' · '}
                ROI total:{' '}
                <span
                  className={`font-mono ${
                    s.roi_unit != null
                      ? s.roi_unit >= 0
                        ? 'text-emerald-800'
                        : 'text-red-800'
                      : 'text-app-muted'
                  }`}
                >
                  {s.roi_unit != null
                    ? `${s.roi_unit >= 0 ? '+' : ''}${(s.roi_unit * 100).toFixed(2)}%`
                    : '—'}
                </span>
              </p>
            </div>
            <div className="rounded-xl border border-app-line bg-app-card p-4">
              <p className="text-xs font-medium text-app-muted">
                Tus picks tomados · resultado
              </p>
              <CardExplain summary="Cómo leer este recuento">
                <p>
                  Solo picks que <strong className="text-app-fg">tú marcaste como tomados</strong> en la fecha. No es
                  el total que generó el modelo ni el total operativo.
                </p>
              </CardExplain>
              <p className="mt-2 text-2xl font-semibold tabular-nums">
                {userId != null ? s.picks_taken_count : '—'}
              </p>
              <p className="mt-1 text-xs text-app-muted">
                {userId != null
                  ? `${s.taken_outcome_wins} gan. · ${s.taken_outcome_losses} perd. · ${s.taken_outcome_pending} pend.`
                  : 'Elige usuario'}
              </p>
            </div>
          </div>
          <section className="mb-6 rounded-xl border border-violet-200/40 bg-app-card p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="font-serif text-base font-medium tracking-tight text-violet-950">
                Picks recientes
              </p>
            </div>
            {topPicksPreview.length === 0 ? (
              <p className="text-xs text-app-muted">No hay picks recientes para mostrar en este corte.</p>
            ) : (
              <div className="overflow-hidden rounded-xl border border-app-line bg-app-card">
                {topPicksPreview.map((r, i) => (
                  <PickInboxRow
                    key={`hero-top-${r.pick_id}`}
                    pickId={r.pick_id}
                    eventId={r.event_id}
                    href={`/picks/${r.pick_id}`}
                    eventLabel={r.event_label}
                    league={r.league}
                    market={r.market}
                    selection={r.selection}
                    selectionDisplay={r.selection_display}
                    pickedValue={r.picked_value}
                    kickoffDisplay={r.kickoff_display ?? null}
                    executionSlotLabelEs={r.execution_slot_label_es ?? null}
                    confidence={confidenceFromOddsReference(r.odds_reference) ?? 'N/D'}
                    outcome={r.outcome}
                    userTaken={r.user_taken}
                    ordinal={i + 1}
                  />
                ))}
              </div>
            )}
          </section>

          <section
            id="mis-selecciones"
            className="mb-6 rounded-xl border border-violet-200/40 bg-app-card p-5 shadow-sm"
          >
            <h2 className="font-serif text-base font-medium tracking-tight text-violet-950">
              Mis selecciones de hoy
            </h2>
            <CardExplain summary="Qué son «mis selecciones»">
              <p>
                Lista de picks que marcaste como <strong className="text-app-fg">tomados</strong> para esta fecha, con su
                resultado. No incluye el resto de picks que emitió el modelo.
              </p>
            </CardExplain>
            {userId == null ? (
              <p className="mt-4 text-xs text-app-muted">
                Selecciona usuario para ver tus selecciones de hoy.
              </p>
            ) : (
              <>
                {(takenTodayQ.data?.recent_total ?? 0) === 0 ? (
                  <p className="mt-4 text-xs text-app-muted">
                    Aún no tienes picks tomados hoy.
                  </p>
                ) : (
                  <div className="mt-4 overflow-hidden rounded-xl border border-app-line bg-app-card shadow-sm">
                    {(takenTodayQ.data?.recent ?? []).map((r, i) => (
                      <PickInboxRow
                        key={`taken-top-${r.pick_id}`}
                        pickId={r.pick_id}
                        eventId={r.event_id}
                        href={`/picks/${r.pick_id}`}
                        eventLabel={r.event_label}
                        league={r.league}
                        market={r.market}
                        selection={r.selection}
                        selectionDisplay={r.selection_display}
                        pickedValue={r.picked_value}
                        kickoffDisplay={r.kickoff_display ?? null}
                        executionSlotLabelEs={r.execution_slot_label_es ?? null}
                        outcome={r.outcome}
                        userTaken={r.user_taken}
                        ordinal={i + 1}
                      />
                    ))}
                  </div>
                )}
              </>
            )}
          </section>

          {s.picks_total > 0 && feedbackTradable != null && feedbackMinOdds != null && (
            <section
              id="feedback-dia-modelo"
              className="mb-6 rounded-xl border border-app-line bg-app-card p-4 shadow-sm"
              aria-label="Cuántos picks van a la lista ejecutable frente a solo análisis"
            >
              <p className="font-serif text-base font-medium tracking-tight text-app-fg">
                Del modelo a tu lista (hoy)
              </p>
              <CardExplain summary="Qué muestra este bloque">
                <p>
                  El modelo ha emitido{' '}
                  <span className="font-mono font-medium text-app-fg">{feedbackGenerated}</span> picks para esta fecha.
                  Parte cumple el mínimo de cuota y entra en la{' '}
                  <strong className="font-medium text-app-fg">lista donde ejecutas</strong> (tablero / lista de picks
                  del run). El resto cuenta en el total pero no se muestra ahí como propuesta operativa: queda como{' '}
                  <strong className="font-medium text-app-fg">solo análisis</strong> para evaluar el modelo. No es un
                  error: son dos capas distintas.
                </p>
              </CardExplain>
              <details className="mt-3 rounded-lg border border-violet-200/50 bg-violet-50/40 px-3 py-2 text-[11px] leading-relaxed text-app-muted">
                <summary className="flex cursor-pointer list-none items-center gap-1.5 font-medium text-violet-950 [list-style:none] [&::-webkit-details-marker]:hidden">
                  <HelpCueIcon />
                  <span>Detalle: umbral de cuota, lista del run y dónde se ve cada cosa</span>
                </summary>
                <div className="mt-2 space-y-2 border-t border-violet-100 pt-2">
                  <p>
                    <strong className="text-app-fg">Cuota</strong> es el valor numérico asociado al pick. Hoy el umbral
                    operativo es{' '}
                    <span className="font-mono text-app-fg">{feedbackMinOdds}</span>
                    : con cuota <strong className="text-app-fg">≥</strong> ese número el pick entra en la lista
                    ejecutable del día; por debajo sigue en el sistema y en los totales &quot;generados&quot;, pero no como fila
                    en esa lista.
                  </p>
                  <p>
                    <strong className="text-app-fg">Lista de picks del run</strong> es la pantalla de partidos del día
                    donde marcas si tomaste un pick. Está alineada con ese umbral: lo que ves allí como apuesta
                    sugerida coincide con la franja verde de abajo.
                  </p>
                  {barRunId != null && (
                    <p>
                      <Link
                        to={`/runs/${barRunId}/picks`}
                        className="font-medium text-violet-900 underline decoration-violet-300 underline-offset-2"
                      >
                        Abrir la lista de picks de este run
                      </Link>
                    </p>
                  )}
                </div>
              </details>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div className="rounded border border-app-line bg-app-card px-2 py-1.5">
                  <p className="text-[10px] uppercase tracking-wide text-app-muted">
                    Generados (modelo)
                  </p>
                  <p className="font-mono text-sm tabular-nums text-app-fg">
                    {feedbackGenerated}
                  </p>
                  <p className="mt-0.5 text-[9px] text-app-muted">Operativos + solo análisis</p>
                </div>
                <div className="rounded border border-app-line bg-app-card px-2 py-1.5 ring-1 ring-emerald-200/80">
                  <p className="text-[10px] uppercase tracking-wide text-app-muted">
                    Listos para operar
                  </p>
                  <p className="font-mono text-sm tabular-nums text-emerald-800">
                    {feedbackTradable}{' '}
                    <span className="text-[11px]">({feedbackTradablePct}%)</span>
                  </p>
                  <p className="mt-0.5 text-[9px] text-app-muted">En la lista ejecutable</p>
                </div>
                <div className="rounded border border-app-line bg-app-card px-2 py-1.5 ring-1 ring-amber-200/80">
                  <p className="text-[10px] uppercase tracking-wide text-app-muted">
                    Solo análisis
                  </p>
                  <p className="font-mono text-sm tabular-nums text-amber-900">
                    {feedbackAnalysisOnly ?? 0}{' '}
                    <span className="text-[11px]">
                      ({feedbackGenerated > 0 ? 100 - feedbackTradablePct : 0}%)
                    </span>
                  </p>
                  <p className="mt-0.5 text-[9px] text-app-muted">
                    Cuota &lt; <span className="font-mono">{feedbackMinOdds}</span> · contados, no en lista operativa
                  </p>
                </div>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full border border-app-line bg-app-card">
                <div
                  className="h-full bg-emerald-600/85"
                  style={{ width: `${feedbackTradablePct}%` }}
                />
              </div>
              <CardExplain summary="Barra, leyenda y términos">
                <p>
                  La barra verde es la parte del total generado que cumple el mínimo de hoy y coincide con la lista
                  ejecutable; el tramo gris son los de solo análisis.
                </p>
                <p className="mt-2">
                  ¿Términos?{' '}
                  <button
                    type="button"
                    onClick={openGlossaryInAnalitica}
                    className="font-medium text-violet-900 underline decoration-violet-300 underline-offset-2 hover:text-violet-950"
                  >
                    Abrir glosario (Modelo · rendimiento)
                  </button>
                </p>
              </CardExplain>
            </section>
          )}
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('operacion')}
              className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                activeTab === 'operacion'
                  ? 'border-violet-400/70 bg-violet-50/90 font-medium text-violet-950 shadow-sm ring-1 ring-violet-200/50'
                  : 'border-violet-200/50 bg-white/60 text-app-muted hover:border-violet-200 hover:bg-violet-50/50 hover:text-violet-950'
              }`}
              title="Listas del día, métricas colapsables y contexto reciente"
            >
              Hoy · operación
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('analitica')}
              className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                activeTab === 'analitica'
                  ? 'border-violet-400/70 bg-violet-50/90 font-medium text-violet-950 shadow-sm ring-1 ring-violet-200/50'
                  : 'border-violet-200/50 bg-white/60 text-app-muted hover:border-violet-200 hover:bg-violet-50/50 hover:text-violet-950'
              }`}
              title="Validar el modelo: solo picks operativos (cuota mínima), rendimiento y calibración"
            >
              Modelo · rendimiento
            </button>
          </div>
          {activeTab === 'operacion' && (
            <>
              <details className="mb-4 rounded-xl border border-app-line bg-app-card p-4 shadow-sm">
                <summary className="cursor-pointer font-serif text-sm font-medium tracking-tight text-app-fg">
                  Contexto del día ({sport})
                </summary>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  {(dashQ.data?.issued_daily ?? []).slice(-4).map((d) => (
                    <div key={d.run_date} className="rounded-md border border-app-line p-2">
                      <p className="text-[10px] text-app-muted">{d.run_date}</p>
                      <p className="mt-1 text-xs text-app-fg">
                        Modelo: <span className="font-mono">{d.picks_total}</span>
                      </p>
                      <p className="text-xs text-app-muted">
                        Listos para operar: <span className="font-mono">{d.picks_tradable}</span>
                      </p>
                      {d.picks_taken != null && (
                        <p className="text-xs text-app-muted">
                          Tomados: <span className="font-mono">{d.picks_taken}</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </details>
          <details className="mt-8 rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
            <summary className="cursor-pointer font-serif text-base font-medium tracking-tight text-app-fg">
              Ver métricas avanzadas de operación
            </summary>
            <CardExplain summary="Cuándo usar esta sección" className="mt-3">
              <p>
                Ábrela cuando quieras justificar el modo del resumen o ajustar cierres del día; no hace falta para
                operar el tablero.
              </p>
            </CardExplain>
            <div className="mt-5 rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                Rendimiento del día
              </h2>
              <CardExplain summary="Qué cuenta este gráfico">
                <p>
                  Proporción ganadas / perdidas / pendientes sobre{' '}
                  <strong className="text-app-fg">todos los picks del día</strong> (operativos y solo análisis), tomados
                  y no tomados. Para series solo con picks operativos (cuota mínima), usa la pestaña{' '}
                  <strong className="text-app-fg">Modelo · rendimiento</strong>.
                </p>
              </CardExplain>
              <div className="mt-6">
                <DashboardPerformanceChart
                  performance={s.performance}
                  hasUser={userId != null}
                />
              </div>
              <CardExplain summary="Cómo leer el gráfico y siguiente paso">
                <p>
                  <strong className="text-app-fg">Lectura:</strong> si hoy hay más verde (ganadas) que rojo (perdidas),
                  la ejecución del día va alineada.
                </p>
                <p className="mt-2">
                  <strong className="text-app-fg">Si encadenas dos días mal:</strong> considera bajar stake al día
                  siguiente (p. ej. mitad) hasta revisar el modo del resumen.
                </p>
              </CardExplain>
            </div>
            <div className="mt-4 rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                Aciertos vs nivel de confianza
              </h2>
              <CardExplain summary="Qué es esta vista">
                <p>
                  Universo de picks <strong className="text-app-fg">operativos</strong> (misma cuota mínima): compara
                  acierto por etiqueta de confianza del modelo.
                </p>
              </CardExplain>
              <div className="mt-4 space-y-2">
                {(dashQ.data?.calibration?.by_confidence ?? []).map((r) => {
                  const hit = r.hit_rate ?? 0
                  const loss = Math.max(0, 1 - hit)
                  return (
                    <div key={r.bucket}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <span className="font-mono text-app-fg">{r.bucket}</span>
                        <span className="text-app-muted">
                          {r.settled} picks cerrados · aciertos {pctPlain(r.hit_rate, 1)}
                        </span>
                      </div>
                      <div className="flex h-2 overflow-hidden rounded border border-app-line">
                        <div
                          className="bg-emerald-500/80"
                          style={{ width: `${Math.max(0, Math.min(100, hit * 100))}%` }}
                        />
                        <div
                          className="bg-red-500/60"
                          style={{ width: `${Math.max(0, Math.min(100, loss * 100))}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
              <CardExplain summary="Interpretar confianza">
                <p>
                  <strong className="text-app-fg">Lectura rápida:</strong> &quot;Alta&quot; debería ir mejor que
                  &quot;Media&quot; y que &quot;Baja&quot;.
                </p>
                <p className="mt-2">
                  <strong className="text-app-fg">Si no se cumple:</strong> la etiqueta de confianza no ordena bien el
                  resultado; no la uses para subir stake.
                </p>
              </CardExplain>
            </div>
            <div className="mt-4 rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
              <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                Aciertos vs nivel de confianza (picks tomados)
              </h2>
              <CardExplain summary="Ámbito: solo tus tomados">
                <p>Solo picks que marcaste como tomados; muestra distinta al universo operativo total.</p>
              </CardExplain>
              {userId == null ? (
                <p className="mt-4 text-xs text-app-muted">
                  Selecciona usuario para ver esta vista.
                </p>
              ) : (dashQ.data?.calibration?.by_confidence_taken?.length ?? 0) === 0 ? (
                <p className="mt-4 text-xs text-app-muted">
                  Aún no hay picks tomados cerrados para esta comparativa.
                </p>
              ) : (
                <div className="mt-4 space-y-2">
                  {(dashQ.data?.calibration?.by_confidence_taken ?? []).map((r) => {
                    const hit = r.hit_rate ?? 0
                    const loss = Math.max(0, 1 - hit)
                    return (
                      <div key={`taken-${r.bucket}`}>
                        <div className="mb-1 flex items-center justify-between text-[11px]">
                          <span className="font-mono text-app-fg">{r.bucket}</span>
                          <span className="text-app-muted">
                            {r.settled} picks cerrados · aciertos {pctPlain(r.hit_rate, 1)}
                          </span>
                        </div>
                        <div className="flex h-2 overflow-hidden rounded border border-app-line">
                          <div
                            className="bg-emerald-500/80"
                            style={{ width: `${Math.max(0, Math.min(100, hit * 100))}%` }}
                          />
                          <div
                            className="bg-red-500/60"
                            style={{ width: `${Math.max(0, Math.min(100, loss * 100))}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </details>
            </>
          )}

          {activeTab === 'analitica' && (
            <div className="mt-2 space-y-4">
              <section className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
                <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                  Síntesis · {sport}
                </h2>
                <CardExplain summary="Relación con el resumen de arriba">
                  <p>
                    Resume las mismas señales que el <strong className="text-app-fg">modo del resumen diario</strong>{' '}
                    del hero: exposición defensiva, neutral o agresiva controlada.
                  </p>
                </CardExplain>
                <div className="mt-4 flex flex-wrap items-start gap-3">
                  <p className={`inline-flex rounded border px-2 py-1 text-[11px] font-semibold ${modeTone}`}>
                    Modo: {systemStatus}
                  </p>
                  <div className={`inline-flex rounded border px-2 py-1 text-[10px] font-semibold ${calibrationTone}`}>
                    Calibración: {calibrationLabel}
                  </div>
                </div>
                <p className="mt-3 font-mono text-xs font-medium tabular-nums text-app-fg">
                  ROI100 (tradable): {pct(roi100, 2)}
                  <span className="mx-2 text-app-line">·</span>
                  Caída máx. 30d:{' '}
                  <span className="tabular-nums">{dd30 ?? '—'}u</span>
                </p>
                <CardExplain summary="Acción sugerida desde la síntesis">
                  <p>
                    <strong className="text-app-fg">Modo de cabecera:</strong> {modeLabel}.{' '}
                    {twoRedDays
                      ? 'Hay dos días seguidos en negativo en la serie diaria; encaja con modo defensivo.'
                      : 'Si la tendencia de abajo encadena dos días rojos, prioriza reducir exposición aunque el hero aún no lo marque.'}
                  </p>
                </CardExplain>
              </section>

              <details className="rounded-lg border border-app-line bg-app-bg px-3 py-2 text-xs leading-relaxed text-app-muted">
                <summary className="flex cursor-pointer list-none items-center gap-1.5 font-medium text-app-fg [list-style:none] [&::-webkit-details-marker]:hidden">
                  <HelpCueIcon />
                  <span>Universo de datos (qué picks cuentan en esta pestaña)</span>
                </summary>
                <p className="mt-2 border-t border-app-line pt-2">
                  Tendencia, rolling y tablas usan solo picks{' '}
                  <strong className="text-app-fg">operativos</strong> (cuota ≥{' '}
                  <span className="font-mono text-app-fg">
                    {dashQ.data?.calibration?.min_tradable_odds ?? s.min_tradable_odds ?? '—'}
                  </span>
                  ), alineados con &quot;Del modelo a tu lista&quot;. El resto del modelo del día no entra en estas
                  agregaciones.
                </p>
              </details>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
                  <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                    Histórico rolling ({sport})
                  </h2>
                  <CardExplain summary="Qué es el rolling">
                    <p>
                      Ventanas recientes sobre picks <strong className="text-app-fg">cerrados</strong> y{' '}
                      <strong className="text-app-fg">operativos</strong> (misma cuota mínima que el tablero).
                    </p>
                  </CardExplain>
                  <div className="mt-4 space-y-3">
                    {selectedSportRolling ? (
                      <div className="rounded-lg border border-app-line p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-app-muted">
                          {selectedSportRolling.sport}
                        </p>
                        <p className="mt-1 text-xs text-app-muted">
                          Cerrados operativos:{' '}
                          <span className="font-mono text-app-fg">{selectedSportRolling.settled_tradable}</span>
                          {' · '}
                          cerrados totales (hist.):{' '}
                          <span className="font-mono text-app-fg">{selectedSportRolling.settled_total}</span>
                        </p>
                        <p className="mt-2 text-xs text-app-muted">
                          ROI50:{' '}
                          <span className="font-mono text-app-fg">
                            {pct(selectedSportRolling.roi_tradable_50, 2)}
                          </span>
                          {' · '}ROI100:{' '}
                          <span className="font-mono text-app-fg">
                            {pct(selectedSportRolling.roi_tradable_100, 2)}
                          </span>
                        </p>
                        <div className="mt-2 flex h-2 overflow-hidden rounded border border-app-line">
                          <div
                            className="bg-emerald-500/80"
                            style={{
                              width: `${Math.max(
                                0,
                                Math.min(100, (selectedSportRolling.hit_rate_tradable_100 ?? 0) * 100),
                              )}%`,
                            }}
                          />
                          <div
                            className="bg-red-500/60"
                            style={{
                              width: `${Math.max(
                                0,
                                100 - Math.min(100, (selectedSportRolling.hit_rate_tradable_100 ?? 0) * 100),
                              )}%`,
                            }}
                          />
                        </div>
                        <p className="mt-1 text-[10px] text-app-muted">
                          Aciertos (ventana 100): {pctPlain(selectedSportRolling.hit_rate_tradable_100, 1)} · Caída
                          máxima (30d):{' '}
                          <span className="font-mono">{selectedSportRolling.drawdown_units_30d ?? '—'}u</span>
                        </p>
                        <CardExplain summary="Cómo leer este bloque">
                          <p>
                            <strong className="text-app-fg">Lectura:</strong>{' '}
                            {roi100 != null && roi100 > 0
                              ? 'rendimiento operativo positivo en la ventana larga.'
                              : 'rendimiento operativo débil o negativo.'}{' '}
                            Riesgo de racha:{' '}
                            {dd30 != null && dd30 <= 6 ? 'relativamente acotado.' : 'elevado.'}
                          </p>
                        </CardExplain>
                      </div>
                    ) : (
                      <p className="text-xs text-app-muted">
                        Sin histórico suficiente para este deporte. Cuando haya más picks cerrados operativos,
                        aparecerán ROI y drawdown.
                      </p>
                    )}
                  </div>
                </div>
                <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
                  <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                    Calibración del modelo ({sport})
                  </h2>
                  <CardExplain summary="Objetivo y universo">
                    <p>
                      Solo picks <strong className="text-app-fg">operativos</strong> (cuota mínima). Sirve para ver si
                      la etiqueta de confianza ordena el P&amp;L como esperas.
                    </p>
                    <p className="mt-2">
                      <strong className="text-app-fg">Decisión analítica:</strong> {analyticalDecisionHint}
                    </p>
                  </CardExplain>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-[11px] font-semibold text-app-muted">Confianza</p>
                      <div
                        className={`mt-2 inline-flex rounded border px-2 py-1 text-[10px] font-semibold ${calibrationTone}`}
                      >
                        {calibrationLabel}
                      </div>
                      <div className="mt-2 space-y-1">
                        {(dashQ.data?.calibration?.by_confidence ?? []).map((r) => (
                          <p key={r.bucket} className="text-xs text-app-fg">
                            <span className="font-mono">{r.bucket}</span> · {r.settled} picks · rendimiento{' '}
                            <span className="font-mono">{pct(r.roi_unit, 1)}</span>
                            {r.settled < minBucketSample && (
                              <span className="ml-2 text-[10px] text-amber-700">(muestra chica)</span>
                            )}
                          </p>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold text-app-muted">Ventaja (edge)</p>
                      <div className="mt-2 space-y-1">
                        {(dashQ.data?.calibration?.by_edge ?? []).map((r) => (
                          <p key={r.bucket} className="text-xs text-app-fg">
                            <span className="font-mono">{r.bucket}</span> · {r.settled} picks · rendimiento{' '}
                            <span className="font-mono">{pct(r.roi_unit, 1)}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-app-line bg-app-card p-5 shadow-sm">
                <h2 className="font-serif text-base font-medium tracking-tight text-app-fg">
                  Tendencia diaria (operativo)
                </h2>
                <CardExplain summary="Cómo leer la tendencia">
                  <p>
                    Últimos días con picks <strong className="text-app-fg">cerrados</strong> y operativos en este
                    deporte (hasta ~14). Cada barra: dirección del resultado % (verde / rojo); el número a la derecha es
                    la magnitud.
                  </p>
                </CardExplain>
                {(dashQ.data?.calibration?.daily_trend ?? []).length === 0 ? (
                  <p className="mt-4 text-xs text-app-muted">
                    Aún no hay suficientes días con cierres operativos para dibujar la serie. Vuelve cuando haya más
                    resultados liquidados.
                  </p>
                ) : (
                  <div className="mt-4 space-y-2">
                    {(dashQ.data?.calibration?.daily_trend ?? []).map((d) => {
                      const roi = d.roi_unit ?? 0
                      const w = Math.max(0, Math.min(100, Math.abs(roi) * 100))
                      return (
                        <div key={d.run_date} className="grid grid-cols-[5.5rem_1fr] items-center gap-3">
                          <div className="text-[11px] text-app-muted">{d.run_date.slice(5)}</div>
                          <div>
                            <div className="flex items-center gap-2">
                              <div className="h-2 flex-1 rounded border border-app-line bg-neutral-900">
                                <div
                                  className={`h-full ${roi >= 0 ? 'bg-emerald-500/80' : 'bg-red-500/80'}`}
                                  style={{ width: `${w}%` }}
                                />
                              </div>
                              <span className="w-20 text-right font-mono text-[11px] text-app-fg">
                                {pct(d.roi_unit, 1)}
                              </span>
                            </div>
                            <p className="mt-0.5 text-[10px] text-app-muted">
                              Aciertos {pctPlain(d.hit_rate, 1)} · cerrados {d.settled}
                            </p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
                <CardExplain summary="Leyenda y regla con el resumen" className="mt-6">
                  <p>
                    <strong className="text-app-fg">Escala:</strong> cada fila es un día; verde = P&amp;L unitario
                    positivo, rojo = negativo. La longitud del tramo depende del valor absoluto del ROI (tope visual
                    100&nbsp;%).
                  </p>
                  <p className="mt-2">
                    <strong className="text-app-fg">Alineación con el hero:</strong>{' '}
                    {twoRedDays
                      ? 'Dos días rojos seguidos encajan con modo defensivo arriba.'
                      : 'Si encadenas dos días rojos aquí, actúa en modo defensivo aunque el hero aún no lo refleje.'}
                  </p>
                </CardExplain>
              </div>

              <details
                id="glosario-metricas"
                className="scroll-mt-4 rounded-xl border border-app-line bg-app-card p-4 text-[11px] leading-relaxed text-app-muted"
              >
                <summary className="flex cursor-pointer list-none items-center gap-2 font-serif text-sm font-medium tracking-tight text-app-fg [list-style:none] [&::-webkit-details-marker]:hidden">
                  <HelpCueIcon className="mt-0.5" />
                  <span>Glosario (lectura del dashboard)</span>
                </summary>
                <div className="mt-3 space-y-2">
                  <p>
                    <strong className="text-app-fg">Lista de picks del run / tablero:</strong> pantalla con los partidos
                    del día y tus marcas de &quot;tomado&quot;. Suele mostrar solo picks que cumplen el mínimo de cuota del
                    día (lista ejecutable); no confundir con el total &quot;generados&quot; del modelo.
                  </p>
                  <p>
                    <strong className="text-app-fg">Umbral o cuota mínima del día:</strong> número de referencia (p. ej.{' '}
                    1,3) desde el cual un pick entra en la lista operativa; por debajo se contabiliza como solo análisis.
                  </p>
                  <p>
                    <strong className="text-app-fg">Generados (modelo):</strong> todos los picks que el modelo emitió en
                    la fecha, con independencia de si luego aparecen en la lista ejecutable.
                  </p>
                  <p>
                    <strong className="text-app-fg">Listos para operar (operativo / tradable):</strong> pick con cuota de
                    referencia ≥ umbral del día; es el subconjunto que alimenta la lista ejecutable y las agregaciones
                    &quot;solo operativos&quot; de esta pestaña.
                  </p>
                  <p>
                    <strong className="text-app-fg">Solo análisis:</strong> pick emitido por el modelo pero con cuota por
                    debajo del umbral: cuenta en generados y sirve para revisar el modelo, pero no como fila en la lista
                    operativa.
                  </p>
                  <p>
                    <strong className="text-app-fg">Tasa de acierto (hit-rate):</strong> entre los picks ya cerrados,
                    proporción que ganaron.
                  </p>
                  <p>
                    <strong className="text-app-fg">Rendimiento (ROI unitario):</strong> ganancia o pérdida por unidad
                    apostada en la ventana indicada (p. ej. últimos 50 o 100 cerrados operativos).
                  </p>
                  <p>
                    <strong className="text-app-fg">Caída máxima (drawdown):</strong> peor racha acumulada de pérdidas en
                    unidades dentro del período (p. ej. 30 días en el rolling).
                  </p>
                  <p>
                    <strong className="text-app-fg">Pre-filtro (cabecera del dashboard):</strong> eventos descartados
                    antes de que el modelo genere picks; es anterior al reparto operativo vs solo análisis.
                  </p>
                </div>
              </details>
            </div>
          )}

        </>
      )}
    </div>
  )
}
