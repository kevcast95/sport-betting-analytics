import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import {
  fetchBt2AdminFase1OperationalSummary,
  fetchBt2AdminF2PoolEligibilityMetrics,
  postBt2AdminRefreshCdmFromSm,
} from '@/lib/api'
import type {
  Bt2AdminFase1OperationalSummaryOut,
  Bt2AdminF2PoolMetricsOut,
} from '@/lib/bt2Types'

function formatAdminBlockError(msg: string): string {
  if (msg.includes('Falta VITE_BT2_ADMIN_API_KEY')) {
    return 'Configura VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el API).'
  }
  if (msg.startsWith('503') || msg.includes('503')) {
    return 'Admin no disponible: define BT2_ADMIN_API_KEY en el entorno del API.'
  }
  if (msg.startsWith('401') || msg.includes('401')) {
    return 'Clave admin rechazada; revisa VITE_BT2_ADMIN_API_KEY.'
  }
  return msg.length > 240 ? `${msg.slice(0, 240)}…` : msg
}

/** Solo presentación: valores tal cual vienen en `metricsGlobal` (T-263), sin recomputar tasas. */
function fmtF2Num(n: unknown): string {
  if (n == null || typeof n !== 'number' || Number.isNaN(n)) return '—'
  return String(n)
}

function fmtF2Pct(n: unknown): string {
  if (n == null || typeof n !== 'number' || Number.isNaN(n)) return '—'
  return `${n}%`
}

/** Alineado con `bt2_router._operating_day_key` (America/Bogota), no con la TZ del navegador. */
function defaultOperatingDayKeyBogota(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function Kpi(props: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-[#a4b4be]/15 bg-white/90 p-4">
      <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
        {props.label}
      </p>
      <p className="font-mono text-xl font-semibold tabular-nums text-[#26343d]">{props.value}</p>
      {props.hint ? (
        <p className="mt-1 text-[10px] leading-snug text-[#52616a]/90">{props.hint}</p>
      ) : null}
    </div>
  )
}

function PassFail({ ok, label }: { ok: boolean; label: string }) {
  return (
    <li className="flex items-start gap-2 text-sm leading-snug text-[#26343d]">
      <span
        className={ok ? 'font-mono text-emerald-700' : 'font-mono text-amber-800'}
        aria-hidden
      >
        {ok ? '✓' : '○'}
      </span>
      <span>{label}</span>
    </li>
  )
}

/** US-FE-062 / T-254 — lectura binaria desde el mismo payload del summary (sin recalcular métricas). */
function OperationalClosureChecklist(props: {
  pool: Bt2AdminFase1OperationalSummaryOut['poolCoverage']
  loop: Bt2AdminFase1OperationalSummaryOut['officialEvaluationLoop']
}) {
  const { pool, loop } = props
  const c1 = pool.candidateEventsCount > 0
  const c2 = pool.eventsWithLatestAudit > 0
  const c3 = loop.officialEvaluationEnrolled > 0
  /** Loop con filas inscritas debe mostrar algún estado en KPIs (pendiente o resuelto). */
  const c4 =
    loop.officialEvaluationEnrolled === 0 ||
    loop.pendingResult > 0 ||
    loop.evaluatedHit > 0 ||
    loop.evaluatedMiss > 0 ||
    loop.voidCount > 0 ||
    loop.noEvaluable > 0
  return (
    <section
      className="rounded-xl border border-[#0f766e]/25 bg-[#ecfdf5]/60 px-4 py-3"
      aria-label="Checklist cierre operativo US-FE-062"
    >
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f766e]">
        Checklist cierre operativo (T-254)
      </p>
      <p className="mt-1 text-[11px] leading-relaxed text-[#52616a]">
        Umbrales alineados a US-FE-062; valores son los del endpoint{' '}
        <span className="font-mono">fase1-operational-summary</span>, no se corrigen en cliente
        (D-06-052).
      </p>
      <ul className="mt-3 space-y-1.5">
        <PassFail ok={c1} label={`Candidatos > 0 (actual: ${pool.candidateEventsCount})`} />
        <PassFail
          ok={c2}
          label={`Con auditoría reciente > 0 (actual: ${pool.eventsWithLatestAudit})`}
        />
        <PassFail
          ok={c3}
          label={`Fila evaluación oficial > 0 (actual: ${loop.officialEvaluationEnrolled})`}
        />
        <PassFail
          ok={c4}
          label={`KPIs de loop con datos (pending_result=${loop.pendingResult}; hit/miss/void/N.E. según bloque 2)`}
        />
      </ul>
    </section>
  )
}

function SectionCard(props: {
  sectionId: string
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <section
      className="rounded-2xl border border-[#26343d]/10 bg-[#f8fafc]/95 p-6 shadow-sm"
      aria-labelledby={props.sectionId}
    >
      <header className="mb-4 border-b border-[#a4b4be]/20 pb-3">
        <h2
          id={props.sectionId}
          className="font-serif text-lg font-semibold tracking-tight text-[#26343d]"
        >
          {props.title}
        </h2>
        <p className="mt-1 text-xs text-[#52616a]">{props.subtitle}</p>
      </header>
      {props.children}
    </section>
  )
}

/** T-265 — KPIs F2 solo desde GET f2-pool-eligibility-metrics (T-263); sin recalcular en cliente. */
function F2PoolSection(props: {
  accumulatedView: boolean
  f2Data: Bt2AdminF2PoolMetricsOut | null
  f2Error: string | null
  loading: boolean
}) {
  const { accumulatedView, f2Data, f2Error, loading } = props
  const subtitle = accumulatedView
    ? 'Ventana rolling (kickoff en America/Bogota): todos los bt2_events de las 5 ligas F2 en esos días; fin de ventana anclado al último operating_day_key con picks (o hoy Bogotá si no hay). Valores = payload T-263.'
    : 'Día calendario Bogotá: eventos F2 con kickoff ese día. Oficial = norma F2 (min familias canónico); relajado = observabilidad (min fam = 1).'

  return (
    <div data-testid="fase1-f2-block">
      <SectionCard
        sectionId="fase1-admin-f2-pool"
        title="4 · Pool elegibilidad F2 (oficial vs relajado)"
        subtitle={subtitle}
      >
        {loading && !f2Data && !f2Error ? (
          <p className="text-sm text-[#52616a]">Cargando métricas F2…</p>
        ) : null}
        {f2Error ? (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50/90 px-3 py-2 text-sm text-red-900"
          >
            {f2Error}
          </div>
        ) : null}
        {!f2Error && f2Data ? (
          <>
            <p className="font-mono text-[11px] leading-relaxed text-[#475569]">
              Ventana:{' '}
              <span className="tabular-nums">
                {f2Data.windowFrom ?? '—'} … {f2Data.windowTo ?? '—'}
              </span>
              {' · '}
              <span className="font-sans text-[#52616a]">operatingDayKeyFilter (API):</span>{' '}
              <span className="tabular-nums">{f2Data.operatingDayKeyFilter ?? '—'}</span>
              {' · '}
              <span className="font-sans text-[#52616a]">ligas BT2 resueltas:</span>{' '}
              <span className="tabular-nums">
                {f2Data.leagueBt2IdsResolved.length > 0
                  ? f2Data.leagueBt2IdsResolved.join(', ')
                  : '—'}
              </span>
            </p>
            {f2Data.noteEs ? (
              <p className="mt-2 text-xs leading-relaxed text-[#52616a]">{f2Data.noteEs}</p>
            ) : null}

            <h3 className="mt-4 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Globales (payload)
            </h3>
            <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi
                label="Candidatos (eventos)"
                value={fmtF2Num(f2Data.metricsGlobal.candidate_events_count)}
              />
              <Kpi
                label="Elegibles · oficial (norma F2)"
                value={fmtF2Num(f2Data.metricsGlobal.eligible_official_count)}
                hint="min familias canónico (re-evaluación en vivo)"
              />
              <Kpi
                label="Elegibles · relajado (observabilidad)"
                value={fmtF2Num(f2Data.metricsGlobal.eligible_relaxed_count)}
                hint="min familias = 1"
              />
              <Kpi
                label="INSUFFICIENT_MARKET_FAMILIES dominante"
                value={
                  f2Data.insufficientMarketFamiliesDominant == null
                    ? '—'
                    : f2Data.insufficientMarketFamiliesDominant
                      ? 'Sí'
                      : 'No'
                }
              />
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <Kpi
                label="Tasa pool elegibilidad · oficial"
                value={fmtF2Pct(f2Data.metricsGlobal.pool_eligibility_rate_official_pct)}
              />
              <Kpi
                label="Tasa pool elegibilidad · relajado"
                value={fmtF2Pct(f2Data.metricsGlobal.pool_eligibility_rate_relaxed_pct)}
              />
            </div>

            <h3 className="mt-6 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Umbrales (payload)
            </h3>
            <ul className="mt-2 space-y-1 text-sm text-[#26343d]">
              <li>
                <span className="font-mono text-[#52616a]">pass_global_60:</span>{' '}
                {String(f2Data.thresholds['pass_global_60'] ?? '—')}
              </li>
              <li>
                <span className="font-mono text-[#52616a]">pass_all_leagues_40:</span>{' '}
                {String(f2Data.thresholds['pass_all_leagues_40'] ?? '—')}
              </li>
              <li>
                <span className="font-mono text-[#52616a]">target_global_official_pct:</span>{' '}
                {String(f2Data.thresholds['target_global_official_pct'] ?? '—')}
              </li>
              <li>
                <span className="font-mono text-[#52616a]">target_per_league_official_pct:</span>{' '}
                {String(f2Data.thresholds['target_per_league_official_pct'] ?? '—')}
              </li>
            </ul>

            <h3 className="mt-6 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Descarte primario (oficial)
            </h3>
            {f2Data.metricsGlobal.primary_discard_breakdown_official &&
            Object.keys(f2Data.metricsGlobal.primary_discard_breakdown_official).length > 0 ? (
              <table className="mt-2 w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Motivo</th>
                    <th className="py-2 font-mono tabular-nums">Cant.</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(f2Data.metricsGlobal.primary_discard_breakdown_official)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, v]) => (
                      <tr key={k} className="border-b border-[#a4b4be]/10">
                        <td className="py-2 pr-2 font-mono text-xs text-[#26343d]">{k}</td>
                        <td className="py-2 font-mono tabular-nums text-[#26343d]">{v}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            ) : (
              <p className="mt-2 text-sm text-[#52616a]">Sin desglose en el payload.</p>
            )}

            <h3 className="mt-6 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Cobertura núcleo (conteos)
            </h3>
            {f2Data.metricsGlobal.core_family_coverage_counts &&
            Object.keys(f2Data.metricsGlobal.core_family_coverage_counts).length > 0 ? (
              <table className="mt-2 w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Clave</th>
                    <th className="py-2 font-mono tabular-nums">Cant.</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(f2Data.metricsGlobal.core_family_coverage_counts).map(
                    ([k, v]) => (
                      <tr key={k} className="border-b border-[#a4b4be]/10">
                        <td className="py-2 pr-2 font-mono text-xs text-[#26343d]">{k}</td>
                        <td className="py-2 font-mono tabular-nums text-[#26343d]">{String(v)}</td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            ) : (
              <p className="mt-2 text-sm text-[#52616a]">Sin conteos en el payload.</p>
            )}

            <h3 className="mt-6 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Por liga (payload)
            </h3>
            {f2Data.metricsByLeague.length === 0 ? (
              <p className="mt-2 text-sm text-[#52616a]">Sin filas en metricsByLeague.</p>
            ) : (
              <table className="mt-2 w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Liga</th>
                    <th className="py-2 font-mono">Candidatos</th>
                    <th className="py-2 font-mono">% oficial</th>
                    <th className="py-2 font-mono">pass_league_40</th>
                  </tr>
                </thead>
                <tbody>
                  {f2Data.metricsByLeague.map((row) => (
                    <tr
                      key={`${row.league_id ?? 'x'}-${row.league_name ?? ''}`}
                      className="border-b border-[#a4b4be]/10"
                    >
                      <td className="py-2 pr-2 font-mono text-[#26343d]">
                        {row.league_name ?? '—'}{' '}
                        <span className="text-[#52616a]">(id {row.league_id ?? '—'})</span>
                      </td>
                      <td className="py-2 font-mono tabular-nums">
                        {fmtF2Num(row.candidate_events_count)}
                      </td>
                      <td className="py-2 font-mono tabular-nums">
                        {fmtF2Pct(row.pool_eligibility_rate_official_pct)}
                      </td>
                      <td className="py-2 font-mono tabular-nums">
                        {row.pass_league_40 == null ? '—' : String(row.pass_league_40)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        ) : null}
        {!f2Error && !f2Data && !loading ? (
          <p className="text-sm text-[#52616a]">Sin datos F2.</p>
        ) : null}
      </SectionCard>
    </div>
  )
}

export default function AdminFase1OperationalPage() {
  const [operatingDayKey, setOperatingDayKey] = useState(defaultOperatingDayKeyBogota)
  const [accumulatedView, setAccumulatedView] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Bt2AdminFase1OperationalSummaryOut | null>(null)
  const [f2Data, setF2Data] = useState<Bt2AdminF2PoolMetricsOut | null>(null)
  const [f2Error, setF2Error] = useState<string | null>(null)
  const [refreshSmBusy, setRefreshSmBusy] = useState(false)
  const [refreshSmMsg, setRefreshSmMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setF2Error(null)
    const f2Opts = accumulatedView ? { days: 30 } : { operatingDayKey }
    const [r1, r2] = await Promise.allSettled([
      fetchBt2AdminFase1OperationalSummary(operatingDayKey, {
        accumulated: accumulatedView,
      }),
      fetchBt2AdminF2PoolEligibilityMetrics(f2Opts),
    ])

    if (r1.status === 'fulfilled') {
      setData(r1.value)
      setError(null)
    } else {
      const msg = r1.reason instanceof Error ? r1.reason.message : String(r1.reason)
      setData(null)
      setError(formatAdminBlockError(msg))
    }

    if (r2.status === 'fulfilled') {
      setF2Data(r2.value)
      setF2Error(null)
    } else {
      setF2Data(null)
      const msg = r2.reason instanceof Error ? r2.reason.message : String(r2.reason)
      setF2Error(formatAdminBlockError(msg))
    }

    setLoading(false)
  }, [operatingDayKey, accumulatedView])

  const onRefreshCdmFromSm = useCallback(async () => {
    if (accumulatedView) return
    setRefreshSmBusy(true)
    setRefreshSmMsg(null)
    try {
      const out = await postBt2AdminRefreshCdmFromSm(operatingDayKey)
      const extra =
        out.notes?.length > 0 ? ` · ${out.notes.slice(0, 6).join(' · ')}` : ''
      setRefreshSmMsg(`${out.messageEs}${extra}`)
      await load()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setRefreshSmMsg(msg.length > 400 ? `${msg.slice(0, 400)}…` : msg)
    } finally {
      setRefreshSmBusy(false)
    }
  }, [accumulatedView, operatingDayKey, load])

  useEffect(() => {
    void load()
  }, [load])

  const pool = data?.poolCoverage
  const loop = data?.officialEvaluationLoop
  const isEmpty =
    data != null &&
    pool != null &&
    loop != null &&
    pool.candidateEventsCount === 0 &&
    loop.suggestedPicksCount === 0

  const scopeHint = accumulatedView
    ? 'Vista acumulada: todos los días con picks en BT2 (12 abr incluido si hay filas).'
    : 'Solo el día operativo seleccionado (Bogotá). Cambiá la fecha para ver 12, 13 u otro día.'

  return (
    <div className="w-full space-y-8" aria-label="Operación Fase 1 administración">
      <BunkerViewHeader
        title="Verdad oficial · pool · loop (Fase 1)"
        subtitle="Métricas contra resultado CDM, no contra liquidación del usuario en app"
        rightActions={
          <div className="flex flex-col items-stretch gap-2 sm:items-end">
            <label className="flex cursor-pointer items-center justify-end gap-2 text-right">
              <input
                type="checkbox"
                checked={accumulatedView}
                onChange={(e) => setAccumulatedView(e.target.checked)}
                className="h-4 w-4 rounded border-[#a4b4be]/40"
              />
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                Acumulado histórico
              </span>
            </label>
            <label className="flex flex-col gap-1 text-right">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                Día operativo (Bogotá)
              </span>
              <input
                type="date"
                value={operatingDayKey}
                onChange={(e) => setOperatingDayKey(e.target.value)}
                disabled={accumulatedView}
                className="rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-1.5 font-mono text-xs text-[#26343d] disabled:cursor-not-allowed disabled:opacity-50"
              />
            </label>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="rounded-lg border border-[#8B5CF6]/40 bg-white px-3 py-1.5 text-xs font-semibold text-[#5b21b6] hover:bg-violet-50 disabled:opacity-50"
            >
              {loading ? 'Cargando…' : 'Actualizar'}
            </button>
            <button
              type="button"
              onClick={() => void onRefreshCdmFromSm()}
              disabled={loading || refreshSmBusy || accumulatedView}
              title={
                accumulatedView
                  ? 'Desactivá «Acumulado histórico» para refrescar un día concreto desde SportMonks.'
                  : 'SportMonks → raw → bt2_events y re-evaluación oficial (no usa snapshot de bóveda).'
              }
              className="rounded-lg border border-[#0d9488]/40 bg-white px-3 py-1.5 text-xs font-semibold text-[#0f766e] hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {refreshSmBusy ? 'Refrescando CDM…' : 'Refrescar CDM (SM) + evaluar'}
            </button>
          </div>
        }
      />

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-900"
        >
          {error}
        </div>
      ) : null}

      {refreshSmMsg ? (
        <div
          role="status"
          className="rounded-xl border border-teal-200/80 bg-teal-50/80 px-4 py-3 text-sm text-[#134e4a]"
        >
          <p className="font-semibold text-[#0f766e]">Último refresco CDM (SportMonks)</p>
          <p className="mt-1 font-mono text-xs leading-relaxed text-[#115e59]">{refreshSmMsg}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <p className="text-sm text-[#52616a]">Cargando resumen operativo…</p>
      ) : null}

      {isEmpty ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-950">
          Sin candidatos ni picks sugeridos para este día operativo. Probá otra fecha o verificá
          snapshots / jobs de evaluación.
        </p>
      ) : null}

      {data && pool && loop ? (
        <>
          <p className="rounded-lg border border-[#a4b4be]/20 bg-white/80 px-4 py-3 text-sm leading-relaxed text-[#26343d]">
            {data.summaryHumanEs}
          </p>
          <div
            className={`rounded-lg border px-4 py-2 text-xs leading-relaxed ${
              data.poolEligibilityObservabilityRelaxed
                ? 'border-amber-300/80 bg-amber-50/90 text-amber-950'
                : 'border-[#a4b4be]/25 bg-[#f1f5f9]/80 text-[#475569]'
            }`}
            data-testid="fase1-pool-eligibility-config"
          >
            <p className="font-mono text-[11px] text-[#334155]">
              Pool elegibilidad (familias): umbral activo env ={' '}
              {data.poolEligibilityMinFamiliesRequired} · referencia oficial S6.3 ={' '}
              {data.poolEligibilityOfficialReferenceS63}
              {data.poolEligibilityObservabilityRelaxed ? ' · modo observabilidad' : ''}
            </p>
            {data.poolEligibilityConfigNoteEs ? (
              <p className="mt-1 text-[11px] text-[#92400e]">{data.poolEligibilityConfigNoteEs}</p>
            ) : null}
          </div>
          {!accumulatedView ? (
            <p
              className="font-mono text-xs text-[#52616a]"
              data-testid="fase1-operating-day-api"
            >
              <span className="font-sans font-semibold text-[#26343d]">
                operatingDayKey (respuesta API):{' '}
              </span>
              {data.operatingDayKey}
            </p>
          ) : null}
          <p className="text-xs leading-relaxed text-[#52616a]">{scopeHint}</p>

          <OperationalClosureChecklist pool={pool} loop={loop} />

          <SectionCard
            sectionId="fase1-admin-pool"
            title="1 · Cobertura del pool"
            subtitle={
              accumulatedView
                ? 'Auditoría por evento distinto con pick histórico (todos los operating_day_key).'
                : 'Auditoría `bt2_pool_eligibility_audit` (última fila por evento del día). Sin fila = no elegible en la tasa.'
            }
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi label="Eventos candidatos" value={String(pool.candidateEventsCount)} />
              <Kpi label="Eventos elegibles" value={String(pool.eligibleEventsCount)} />
              <Kpi
                label="Con auditoría reciente"
                value={String(pool.eventsWithLatestAudit)}
                hint="Al menos una fila en tabla de auditoría"
              />
              <Kpi
                label="Pool eligibility rate"
                value={
                  pool.poolEligibilityRatePct != null
                    ? `${pool.poolEligibilityRatePct}%`
                    : '—'
                }
                hint="elegibles ÷ candidatos"
              />
            </div>
            <h3 className="mt-6 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Motivos de descarte (pool)
            </h3>
            {Object.keys(pool.poolDiscardReasonBreakdown).length === 0 ? (
              <p className="mt-2 text-sm text-[#52616a]">Sin descartes registrados.</p>
            ) : (
              <table className="mt-2 w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Motivo</th>
                    <th className="py-2 font-mono tabular-nums">Cant.</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(pool.poolDiscardReasonBreakdown)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, v]) => (
                      <tr key={k} className="border-b border-[#a4b4be]/10">
                        <td className="py-2 pr-2 font-mono text-xs text-[#26343d]">{k}</td>
                        <td className="py-2 font-mono tabular-nums text-[#26343d]">{v}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </SectionCard>

          <SectionCard
            sectionId="fase1-admin-loop"
            title="2 · Cierre de loop (evaluación oficial)"
            subtitle={
              accumulatedView
                ? 'Todos los `daily_picks` con fila de evaluación oficial (cualquier día).'
                : 'Estados ACTA T-244 para el día elegido. Pendientes y no evaluables aparte del hit rate.'
            }
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi
                label="Picks sugeridos (filas)"
                value={String(loop.suggestedPicksCount)}
              />
              <Kpi
                label="Con fila evaluación oficial"
                value={String(loop.officialEvaluationEnrolled)}
              />
              <Kpi
                label="Pendientes (pending_result)"
                value={String(loop.pendingResult)}
                hint="Aún sin resultado oficial trazable"
              />
              <Kpi
                label="No evaluable"
                value={String(loop.noEvaluable)}
                hint="Fuera de mercado v1 u otras reglas"
              />
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <Kpi label="Void oficial" value={String(loop.voidCount)} />
              <Kpi label="Hit (oficial)" value={String(loop.evaluatedHit)} />
              <Kpi label="Miss (oficial)" value={String(loop.evaluatedMiss)} />
            </div>
            <div className="mt-4 rounded-lg border border-[#8B5CF6]/20 bg-violet-50/50 px-4 py-3">
              <p className="font-mono text-sm font-semibold text-[#4c1d95]">
                {accumulatedView
                  ? 'Hit rate (scored, acumulado histórico)'
                  : 'Hit rate (scored, este día)'}{' '}
                <span className="tabular-nums">
                  {loop.hitRateOnScoredPct != null ? `${loop.hitRateOnScoredPct}%` : '—'}
                </span>
              </p>
              <p className="mt-1 text-xs text-[#5b21b6]/90">
                Fórmula: hit ÷ (hit + miss). No incluye pendientes, void ni no evaluable. Partidos sin
                resultado siguen en pending → hit/miss en cero hasta que corra el job de evaluación.
              </p>
            </div>
            <h3 className="mt-6 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              No evaluable por motivo
            </h3>
            {Object.keys(loop.noEvaluableByReason).length === 0 ? (
              <p className="mt-2 text-sm text-[#52616a]">Ninguno en este día.</p>
            ) : (
              <table className="mt-2 w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Código</th>
                    <th className="py-2 font-mono tabular-nums">Cant.</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(loop.noEvaluableByReason)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, v]) => (
                      <tr key={k} className="border-b border-[#a4b4be]/10">
                        <td className="py-2 pr-2 font-mono text-xs text-[#26343d]">{k}</td>
                        <td className="py-2 font-mono tabular-nums text-[#26343d]">{v}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </SectionCard>

          <SectionCard
            sectionId="fase1-admin-precision"
            title="3 · Desempeño por mercado y confianza"
            subtitle={
              accumulatedView
                ? 'Buckets sobre todas las filas de evaluación enlazadas a picks (histórico).'
                : 'Solo picks del día seleccionado; hit rate por bucket excluye pending/void/N.E.'
            }
          >
            <h3 className="font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Por mercado canónico
            </h3>
            {data.precisionByMarket.length === 0 ? (
              <p className="mt-2 text-sm text-[#52616a]">Sin filas para este día.</p>
            ) : (
              <table className="mt-2 w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Mercado</th>
                    <th className="py-2 font-mono">Hit</th>
                    <th className="py-2 font-mono">Miss</th>
                    <th className="py-2 font-mono">Pend.</th>
                    <th className="py-2 font-mono">N/E</th>
                    <th className="py-2 font-mono">Void</th>
                    <th className="py-2 font-mono">HR %</th>
                  </tr>
                </thead>
                <tbody>
                  {data.precisionByMarket.map((row) => (
                    <tr key={row.bucketKey} className="border-b border-[#a4b4be]/10">
                      <td className="py-2 pr-2 font-mono text-[#26343d]">{row.bucketKey}</td>
                      <td className="py-2 font-mono tabular-nums">{row.evaluatedHit}</td>
                      <td className="py-2 font-mono tabular-nums">{row.evaluatedMiss}</td>
                      <td className="py-2 font-mono tabular-nums">{row.pendingResult}</td>
                      <td className="py-2 font-mono tabular-nums">{row.noEvaluable}</td>
                      <td className="py-2 font-mono tabular-nums">{row.voidCount}</td>
                      <td className="py-2 font-mono tabular-nums">
                        {row.hitRateOnScoredPct != null ? `${row.hitRateOnScoredPct}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <h3 className="mt-8 font-mono text-xs font-bold uppercase tracking-wide text-[#52616a]">
              Por etiqueta de confianza DSR
            </h3>
            {data.precisionByConfidence.length === 0 ? (
              <p className="mt-2 text-sm text-[#52616a]">Sin filas para este día.</p>
            ) : (
              <table className="mt-2 w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#a4b4be]/25 text-[10px] uppercase text-[#52616a]">
                    <th className="py-2 pr-2">Confianza</th>
                    <th className="py-2 font-mono">Hit</th>
                    <th className="py-2 font-mono">Miss</th>
                    <th className="py-2 font-mono">Pend.</th>
                    <th className="py-2 font-mono">N/E</th>
                    <th className="py-2 font-mono">Void</th>
                    <th className="py-2 font-mono">HR %</th>
                  </tr>
                </thead>
                <tbody>
                  {data.precisionByConfidence.map((row) => (
                    <tr key={row.bucketKey} className="border-b border-[#a4b4be]/10">
                      <td className="py-2 pr-2 font-mono text-[#26343d]">{row.bucketKey}</td>
                      <td className="py-2 font-mono tabular-nums">{row.evaluatedHit}</td>
                      <td className="py-2 font-mono tabular-nums">{row.evaluatedMiss}</td>
                      <td className="py-2 font-mono tabular-nums">{row.pendingResult}</td>
                      <td className="py-2 font-mono tabular-nums">{row.noEvaluable}</td>
                      <td className="py-2 font-mono tabular-nums">{row.voidCount}</td>
                      <td className="py-2 font-mono tabular-nums">
                        {row.hitRateOnScoredPct != null ? `${row.hitRateOnScoredPct}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </SectionCard>

          <F2PoolSection
            accumulatedView={accumulatedView}
            f2Data={f2Data}
            f2Error={f2Error}
            loading={loading}
          />
        </>
      ) : null}

      {!data && (f2Data || f2Error) ? (
        <F2PoolSection
          accumulatedView={accumulatedView}
          f2Data={f2Data}
          f2Error={f2Error}
          loading={loading}
        />
      ) : null}
    </div>
  )
}
