import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { fetchBt2AdminMonitorResultados, fetchBt2AdminMonitorResultadosShadow } from '@/lib/api'
import type {
  Bt2AdminMonitorResultadosOut,
  Bt2AdminMonitorShadowOut,
  Bt2MonitorOutcome,
} from '@/lib/bt2Types'
import { useUserStore } from '@/store/useUserStore'

/** Periodo de consulta (UI). */
type MonitorPeriodPreset = 'today' | '7d' | '30d' | 'range'

const MONITOR_PAGE_SIZE = 25

type MonitorOutcomeFilter = 'all' | 'si' | 'no' | 'pendiente' | 'void' | 'ne'
type MonitorMode = 'prod' | 'shadow'
type ShadowViewKind = 'daily_shadow' | 'historico'

type OutcomeBadge = Bt2MonitorOutcome

type TableRow = {
  dailyPickId: number
  dayKey: string
  eventLabel: string
  marketLabel: string
  selectionLabel: string
  scoreText: string
  outcome: OutcomeBadge
  decimalOdds: number | null
  flatStakeReturnUnits: number | null
  /** Marca en `bt2_picks.user_result_claim` (no modifica pendiente CDM). */
  userResultClaim: string | null
  dsrNarrativeEs: string | null
  dsrConfidenceLabel: string | null
  dsrSource: string | null
}

function todayIsoBogota(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function addDaysIso(isoDay: string, delta: number): string {
  const [y, m, d] = isoDay.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() + delta)
  const yy = dt.getUTCFullYear()
  const mm = String(dt.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(dt.getUTCDate()).padStart(2, '0')
  return `${yy}-${mm}-${dd}`
}

function operatingRangeForPreset(
  preset: MonitorPeriodPreset,
  rangeFrom: string,
  rangeTo: string,
): { from: string; to: string } {
  const t = todayIsoBogota()
  switch (preset) {
    case 'today':
      return { from: t, to: t }
    case '7d':
      return { from: addDaysIso(t, -6), to: t }
    case '30d':
      return { from: addDaysIso(t, -29), to: t }
    case 'range':
      return { from: rangeFrom, to: rangeTo }
    default:
      return { from: t, to: t }
  }
}

function outcomeLabel(o: OutcomeBadge): string {
  switch (o) {
    case 'si':
      return 'Sí'
    case 'no':
      return 'No'
    case 'pendiente':
      return 'Pendiente'
    case 'void':
      return 'Void'
    case 'ne':
      return 'N.E.'
    default:
      return '—'
  }
}

function outcomeClass(o: OutcomeBadge): string {
  switch (o) {
    case 'si':
      return 'border-[#8B5CF6]/35 bg-[#eef4fa] text-[#6d3bd7]'
    case 'no':
      return 'border-[#ea580c]/30 bg-[#fff7ed] text-[#c2410c]'
    case 'pendiente':
      return 'border-[#a4b4be]/40 bg-white text-[#52616a]'
    case 'void':
      return 'border-[#a4b4be]/35 bg-[#f8fafc] text-[#64748b]'
    case 'ne':
      return 'border-[#a4b4be]/35 bg-[#f1f5f9] text-[#64748b]'
    default:
      return 'border-[#a4b4be]/35 bg-[#f8fafc] text-[#64748b]'
  }
}

/** Contenido del panel DSR en la fila expandible (ancho completo). */
function DsrCollapsePanelBody(props: {
  narrativeEs: string | null
  confidenceLabel: string | null
  source: string | null
}) {
  const narrative =
    props.narrativeEs != null && props.narrativeEs.trim() !== ''
      ? props.narrativeEs.trim()
      : null
  const confidence = props.confidenceLabel?.trim() || null
  const source = props.source?.trim() || null

  return (
    <div className="space-y-3 border-l-2 border-[#8B5CF6]/40 pl-4">
      {(confidence != null || source != null) && (
        <div className="flex flex-wrap gap-2 font-mono text-[10px] leading-tight text-[#6e7d86]">
          {confidence != null ? (
            <span className="rounded border border-[#a4b4be]/25 bg-white px-1.5 py-0.5">
              conf: {confidence}
            </span>
          ) : null}
          {source != null ? (
            <span className="rounded border border-[#a4b4be]/25 bg-white px-1.5 py-0.5">
              fuente: {source}
            </span>
          ) : null}
        </div>
      )}
      <p className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-[#435368]">
        {narrative ?? 'Sin narrativa DSR guardada para esta fila de bóveda.'}
      </p>
    </div>
  )
}

/** Badge de `user_result_claim` en ledger — no cambia pendiente oficial CDM / monitor. */
function OperatorClaimPill(props: { claim: string | null }) {
  const claim = props.claim
  if (claim === null || claim === '') {
    return (
      <span className="font-sans text-[10px] text-[#a4b4be]" title="Sin marca en ledger">
        —
      </span>
    )
  }
  const presets: Record<string, { sym: string; cls: string }> = {
    pending: {
      sym: '…',
      cls: 'border-amber-200/90 bg-amber-50/95 text-amber-950',
    },
    won: {
      sym: 'G',
      cls: 'border-emerald-200/80 bg-emerald-50/95 text-emerald-900',
    },
    lost: {
      sym: 'L',
      cls: 'border-orange-200/70 bg-orange-50/95 text-orange-950',
    },
    void: {
      sym: '∅',
      cls: 'border-[#cbd5e1]/80 bg-[#f8fafc] text-[#475569]',
    },
  }
  const x = presets[claim] ?? {
    sym: claim.slice(0, 3),
    cls: 'border-[#a4b4be]/35 bg-white text-[#52616a]',
  }
  return (
    <span
      title="Marca «Tu criterio» en ledger (no altera resultado oficial pendiente)."
      className={`inline-flex min-h-[1.375rem] min-w-[1.375rem] items-center justify-center rounded border px-1 font-sans text-[10px] font-bold uppercase tracking-tight ${x.cls}`}
    >
      {x.sym}
    </span>
  )
}

function DefinitionsPanel(props: { open: boolean; onClose: () => void }) {
  if (!props.open) return null
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-[#26343d]/40 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="monitor-def-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-[#a4b4be]/25 bg-white p-6 text-sm text-[#52616a] shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="monitor-def-title" className="font-serif text-xl font-semibold text-[#26343d]">
            Definiciones
          </h2>
          <button
            type="button"
            onClick={props.onClose}
            className="rounded-lg border border-[#a4b4be]/35 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-[#52616a] hover:bg-[#eef4fa]"
          >
            Cerrar
          </button>
        </div>
        <ul className="list-inside list-disc space-y-2">
          <li>
            <strong className="text-[#26343d]">Tasa del sistema:</strong> aciertos ÷ (aciertos +
            fallos) solo sobre picks con resultado scored; pendientes, void y no evaluable no
            entran en el porcentaje.
          </li>
          <li>
            <strong className="text-[#26343d]">Tu tasa:</strong> misma fórmula (aciertos ÷ aciertos +
            fallos), sólo entre tus picks operados con veredicto oficial ya emitido; los pendientes
            no bajan el % hasta que pasen a Sí/No.
          </li>
          <li>
            <strong className="text-[#26343d]">N.E.:</strong> no evaluable (mercado o reglas fuera
            del alcance de evaluación v1).
          </li>
          <li>
            Fuente: filas de bóveda <span className="font-mono text-[#6d3bd7]">bt2_daily_picks</span>{' '}
            + <span className="font-mono text-[#6d3bd7]">bt2_pick_official_evaluation</span>.
          </li>
          <li>
            <strong className="text-[#26343d]">No es el calendario deportivo global:</strong> solo
            aparecen picks que la bóveda ya materializó para ese{' '}
            <span className="font-mono">operating_day_key</span>. Partidos jugados “hoy” sin pick en
            bóveda no cuentan aquí.
          </li>
          <li>
            Con <strong className="text-[#26343d]">Sync SportMonks</strong> activo,{' '}
            <strong className="text-[#26343d]">Actualizar + SM</strong> refresca marcadores (SM → CDM),
            evalúa pendientes y re-intenta filas marcadas N.E. por soporte antiguo del resolver (misma
            corrida en servidor actualizado).
          </li>
          <li>
            <strong className="text-[#26343d]">ROI plano:</strong> una unidad por pick; cuota ={' '}
            <span className="font-mono">reference_decimal_odds</span> si existe, si no mediana del
            consenso CDM del evento (monitor usa umbral inclusivo para no perder piernas válidas).
            Acierto: +(O−1); fallo: −1; pendientes / void / N.E. no entran.
          </li>
        </ul>
      </div>
    </div>
  )
}

function formatAdminMonitorError(msg: string): string {
  if (msg.includes('Falta VITE_BT2_ADMIN_API_KEY')) {
    return 'Configura VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).'
  }
  if (msg.startsWith('503') || msg.includes('503')) {
    return 'Admin no disponible: define BT2_ADMIN_API_KEY en el entorno del API.'
  }
  if (msg.startsWith('401') || msg.includes('401')) {
    return 'Clave admin rechazada; revisa VITE_BT2_ADMIN_API_KEY.'
  }
  return msg.length > 260 ? `${msg.slice(0, 260)}…` : msg
}

function pct01(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function dsrStatusTone(parseStatus: string | null | undefined): string {
  const s = (parseStatus ?? '').trim()
  if (s === 'ok') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (s === 'dsr_empty_signal') return 'border-amber-200 bg-amber-50 text-amber-900'
  if (s === 'dsr_failed') return 'border-red-200 bg-red-50 text-red-900'
  return 'border-[#a4b4be]/35 bg-[#f8fafc] text-[#52616a]'
}

function settlementLabel(stage: string | null | undefined): string {
  const s = (stage ?? '').trim()
  if (s === 'cierre_oficial') return 'Cierre oficial'
  if (s === 'resultado_visible_no_oficial') return 'Visible no oficial'
  if (s === 'pending_recheck') return 'Pending recheck'
  if (s === 'cierre_manual_auditado') return 'Manual auditado'
  return '—'
}

function ShadowMonitorPanel(props: {
  data: Bt2AdminMonitorShadowOut | null
  loading: boolean
  page: number
  totalPages: number
  onPrev: () => void
  onNext: () => void
}) {
  const k = props.data?.kpis
  const rows = props.data?.rows ?? []
  return (
    <section className="mt-10 space-y-6 border-t border-[#a4b4be]/15 pt-8">
      <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-[#a4b4be]/15 md:grid-cols-2 xl:grid-cols-4">
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Fixtures seen</p>
          <p className="font-mono text-3xl text-[#26343d]">{k?.fixturesSeen ?? '—'}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Match rate</p>
          <p className="font-mono text-3xl text-[#26343d]">{pct01(k?.matchRate)}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">h2h T-60</p>
          <p className="font-mono text-3xl text-[#26343d]">{k?.fixturesWithH2hT60 ?? '—'}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Value pool pass</p>
          <p className="font-mono text-3xl text-[#26343d]">{pct01(k?.valuePoolPassRate)}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Shadow picks</p>
          <p className="font-mono text-3xl text-[#26343d]">{k?.shadowPicksGenerated ?? '—'}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Matched w/odds</p>
          <p className="font-mono text-3xl text-[#26343d]">{k?.matchedWithOddsT60 ?? '—'}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Unmatched event</p>
          <p className="font-mono text-3xl text-[#26343d]">{k?.unmatchedEvent ?? '—'}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Credits avg/fixture</p>
          <p className="font-mono text-3xl text-[#26343d]">
            {k?.avgCreditsPerFixture != null ? k.avgCreditsPerFixture.toFixed(2) : '—'}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-[#a4b4be]/15 md:grid-cols-2 xl:grid-cols-4">
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Scored picks</p>
          <p className="font-mono text-3xl text-[#26343d]">{k?.scoredPicks ?? '—'}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Hit / Miss / Void</p>
          <p className="font-mono text-xl text-[#26343d]">
            {k?.evaluatedHit ?? 0} / {k?.evaluatedMiss ?? 0} / {k?.voidCount ?? 0}
          </p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Hit rate (scored)</p>
          <p className="font-mono text-3xl text-[#26343d]">{pct01(k?.hitRateOnScored)}</p>
        </div>
        <div className="bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">Pending / N.E.</p>
          <p className="font-mono text-xl text-[#26343d]">
            {k?.pendingResult ?? 0} / {k?.noEvaluable ?? 0}
          </p>
        </div>
        <div className="bg-white p-4 md:col-span-2 xl:col-span-2">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">ROI flat stake (1u)</p>
          <p className="font-mono text-3xl text-[#26343d]">
            {k?.roiFlatStakePct != null ? `${k.roiFlatStakePct.toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-[#52616a]">
            Net: {k?.roiFlatStakeUnits != null ? k.roiFlatStakeUnits.toFixed(2) : '—'}u
          </p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-[#a4b4be]/15 bg-white">
        <table className="w-full border-separate border-spacing-0 text-left">
          <thead>
            <tr className="bg-[#eef4fa]">
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Run</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Día</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Fixture / Event</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Liga</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Market</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Selección</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">DSR</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Taxonomía</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-right text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Odds</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Visibilidad DSR</th>
              <th className="border-b border-[#a4b4be]/20 p-3 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">Settlement</th>
            </tr>
          </thead>
          <tbody className="font-mono text-sm text-[#26343d]">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={12} className="p-8 text-center text-[#52616a]">
                  {props.loading ? 'Cargando…' : 'Sin filas shadow para el rango/filtros actuales.'}
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={`${r.smFixtureId}-${r.operatingDayKey}`} className="hover:bg-[#f6fafe]">
                  <td className="border-b border-[#e5eff7] p-3 text-xs">
                    <span className="block">{r.runKey}</span>
                    <span className="block text-[#52616a]">{r.selectionSource ?? '—'}</span>
                  </td>
                  <td className="border-b border-[#e5eff7] p-3">{r.operatingDayKey}</td>
                  <td className="border-b border-[#e5eff7] p-3">{r.fixtureEventLabel}</td>
                  <td className="border-b border-[#e5eff7] p-3">{r.leagueName}</td>
                  <td className="border-b border-[#e5eff7] p-3">{r.market}</td>
                  <td className="border-b border-[#e5eff7] p-3">{r.selection ?? '—'}</td>
                  <td className="border-b border-[#e5eff7] p-3 text-xs">
                    <span className={`inline-block rounded border px-2 py-0.5 ${dsrStatusTone(r.dsrParseStatus)}`}>
                      {r.dsrParseStatus ?? '—'}
                    </span>
                    <span className="mt-1 block text-[#52616a]">{r.statusShadow}</span>
                  </td>
                  <td className="border-b border-[#e5eff7] p-3">{r.classificationTaxonomy}</td>
                  <td className="border-b border-[#e5eff7] p-3 text-right">
                    {r.decimalOdds != null ? r.decimalOdds.toFixed(2) : '—'}
                  </td>
                  <td className="border-b border-[#e5eff7] p-3 text-xs">
                    <span className="block">src={r.dsrSource ?? '—'} · model={r.dsrModel ?? '—'}</span>
                    <span className="block">contract={r.dsrPromptVersion ?? '—'}</span>
                    <span className="block">
                      canon={r.dsrMarketCanonical ?? '—'} / {r.dsrSelectionCanonical ?? '—'}
                    </span>
                    <span className="block">selected={r.dsrSelectedTeam ?? '—'}</span>
                    <span className="block text-[#52616a]">{r.dsrNoPickReason ?? r.dsrFailureReason ?? '—'}</span>
                    <span className="block text-[#52616a]">
                      {(r.dsrResponseExcerpt ?? '').slice(0, 120) || '—'}
                    </span>
                  </td>
                  <td className="border-b border-[#e5eff7] p-3 text-xs">
                    <span className="block">{settlementLabel(r.settlementStage)}</span>
                    <span className="block">{r.evaluationStatus ?? '—'}</span>
                    <span className="block text-[#52616a]">{r.resultScoreText ?? r.evaluationReason ?? '—'}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <div className="flex items-center justify-between border-t border-[#e5eff7] px-3 py-3 text-xs text-[#52616a]">
          <span>
            Página <span className="font-mono text-[#26343d]">{props.page}</span> /{' '}
            <span className="font-mono text-[#26343d]">{props.totalPages}</span>
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={props.onPrev}
              disabled={props.page <= 1 || props.loading}
              className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-1.5 disabled:opacity-40"
            >
              Anterior
            </button>
            <button
              type="button"
              onClick={props.onNext}
              disabled={props.page >= props.totalPages || props.loading}
              className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-1.5 disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default function MonitorResultadosPage() {
  const userId = useUserStore((s) => s.userId)
  const [mode, setMode] = useState<MonitorMode>('prod')
  const [preset, setPreset] = useState<MonitorPeriodPreset>('7d')
  const t0 = todayIsoBogota()
  const [rangeFrom, setRangeFrom] = useState(() => addDaysIso(t0, -6))
  const [rangeTo, setRangeTo] = useState(t0)
  const [tableFilter, setTableFilter] = useState<'all' | 'mine'>('all')
  const [onlyScored, setOnlyScored] = useState(false)
  const [defsOpen, setDefsOpen] = useState(false)
  const [data, setData] = useState<Bt2AdminMonitorResultadosOut | null>(null)
  const [shadowData, setShadowData] = useState<Bt2AdminMonitorShadowOut | null>(null)
  const [shadowViewKind, setShadowViewKind] = useState<ShadowViewKind>('historico')
  const [shadowRunKey, setShadowRunKey] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  /** Trae marcadores desde SportMonks, actualiza CDM y re-evalúa pendientes (más lento, cuota API). */
  const [syncFromSportmonks, setSyncFromSportmonks] = useState(false)
  /** Solo GET SM para fixtures con evaluación oficial pending (ahorra cuota vs. refrescar todos). */
  const [smSyncPendingOnly, setSmSyncPendingOnly] = useState(true)
  const [monitorPage, setMonitorPage] = useState(1)
  const [outcomeFilter, setOutcomeFilter] = useState<MonitorOutcomeFilter>('all')
  const [marketFilter, setMarketFilter] = useState('')
  const [tableSearch, setTableSearch] = useState('')
  /** Fila cuyo panel DSR está expandido (segunda `<tr>` a ancho completo). */
  const [dsrExpandedPickId, setDsrExpandedPickId] = useState<number | null>(null)

  const rangeKeys = useMemo(
    () => operatingRangeForPreset(preset, rangeFrom, rangeTo),
    [preset, rangeFrom, rangeTo],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const offset = (monitorPage - 1) * MONITOR_PAGE_SIZE
      if (mode === 'prod') {
        const out = await fetchBt2AdminMonitorResultados(rangeKeys.from, rangeKeys.to, {
          monitorUserId: userId ?? undefined,
          syncFromSportmonks,
          smSyncPendingOnly: smSyncPendingOnly ? undefined : false,
          rowsOffset: offset,
          rowsLimit: MONITOR_PAGE_SIZE,
          outcomeFilter: outcomeFilter === 'all' ? undefined : outcomeFilter,
          marketSubstring: marketFilter.trim() || undefined,
          search: tableSearch.trim() || undefined,
        })
        setData(out)
      } else {
        const out = await fetchBt2AdminMonitorResultadosShadow(rangeKeys.from, rangeKeys.to, {
          rowsOffset: offset,
          rowsLimit: MONITOR_PAGE_SIZE,
          classificationFilter: outcomeFilter === 'all' ? undefined : outcomeFilter,
          marketSubstring: marketFilter.trim() || undefined,
          search: tableSearch.trim() || undefined,
          runKind: shadowViewKind === 'historico' ? 'backfill_window' : 'daily_shadow',
          runKey: shadowRunKey.trim() || undefined,
          groupByRun: true,
        })
        setShadowData(out)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setData(null)
      setShadowData(null)
      setError(formatAdminMonitorError(msg))
    } finally {
      setLoading(false)
    }
  }, [
    rangeKeys.from,
    rangeKeys.to,
    userId,
    syncFromSportmonks,
    smSyncPendingOnly,
    monitorPage,
    outcomeFilter,
    marketFilter,
    tableSearch,
    mode,
    shadowViewKind,
    shadowRunKey,
  ])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    setMonitorPage(1)
  }, [
    mode,
    shadowViewKind,
    shadowRunKey,
    preset,
    rangeFrom,
    rangeTo,
    outcomeFilter,
    marketFilter,
    tableSearch,
    syncFromSportmonks,
    smSyncPendingOnly,
  ])

  useEffect(() => {
    setDsrExpandedPickId(null)
  }, [
    mode,
    monitorPage,
    preset,
    rangeFrom,
    rangeTo,
    outcomeFilter,
    marketFilter,
    tableSearch,
    tableFilter,
    onlyScored,
  ])

  const sys = data?.system
  const sysRoi = sys?.roiFlatStake
  const yrs = data?.yours
  const yrsRoi = yrs?.roiFlatStake
  const today = data?.today
  const tasaPct = sys?.hitRatePct ?? null

  const tusShowEmpty = yrs != null && yrs.totalPicks === 0
  const yoursHasPending = yrs != null && yrs.pending > 0

  const apiRowsToTable = (rows: Bt2AdminMonitorResultadosOut['rows']): TableRow[] =>
    rows.map((r) => ({
      dailyPickId: r.dailyPickId,
      dayKey: r.operatingDayKey,
      eventLabel: r.eventLabel,
      marketLabel: r.marketLabelEs,
      selectionLabel: r.selectionSummaryEs,
      scoreText: r.scoreText,
      outcome: r.outcome,
      decimalOdds: r.decimalOdds ?? null,
      flatStakeReturnUnits: r.flatStakeReturnUnits ?? null,
      userResultClaim: r.userResultClaim ?? null,
      dsrNarrativeEs: r.dsrNarrativeEs ?? null,
      dsrConfidenceLabel: r.dsrConfidenceLabel ?? null,
      dsrSource: r.dsrSource ?? null,
    }))

  const rowsTotalFromApi = data?.rowsTotal
  const shadowRowsTotal = shadowData?.rowsTotal
  const monitorTotalPages =
    rowsTotalFromApi != null && rowsTotalFromApi > 0
      ? Math.max(1, Math.ceil(rowsTotalFromApi / MONITOR_PAGE_SIZE))
      : 1
  const shadowTotalPages =
    shadowRowsTotal != null && shadowRowsTotal > 0
      ? Math.max(1, Math.ceil(shadowRowsTotal / MONITOR_PAGE_SIZE))
      : 1

  const filteredRows = useMemo(() => {
    if (!data?.rows) return []
    let src = data.rows
    if (tableFilter === 'mine' && userId) {
      src = src.filter((r) => r.userId === userId && r.iOperated)
    }
    let rows = apiRowsToTable(src)
    if (onlyScored) {
      rows = rows.filter((r) => r.outcome === 'si' || r.outcome === 'no')
    }
    return rows
  }, [data, onlyScored, tableFilter, userId])

  const handleRefresh = useCallback(() => {
    void load()
  }, [load])

  return (
    <div className="font-sans">
      <DefinitionsPanel open={defsOpen} onClose={() => setDefsOpen(false)} />

      {error ? (
        <div
          className="mb-6 rounded-xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-900"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {!loading && !error && data?.smSync?.attempted && data.smSync.messageEs ? (
        <div
          className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
            data.smSync.ok
              ? 'border-emerald-200 bg-emerald-50/95 text-emerald-950'
              : 'border-amber-200 bg-amber-50/95 text-amber-950'
          }`}
          role="status"
        >
          <strong className="font-semibold">SportMonks / CDM:</strong> {data.smSync.messageEs}
          {data.smSync.attempted ? (
            <span className="mt-1 block font-mono text-[11px] opacity-90">
              Modo SM:{' '}
              {data.smSync.pendingOnly !== false ? 'solo pendientes' : 'todos (hasta límite)'}
              {data.smSync.uniqueFixturesProcessed > 0 ? (
                <>
                  {' · '}
                  Fixtures SM únicos: {data.smSync.uniqueFixturesProcessed}
                </>
              ) : null}
              {data.smSync.closedPendingToFinal != null
                ? ` · pending→final: ${data.smSync.closedPendingToFinal}`
                : ''}
            </span>
          ) : null}
          {data.smSync.notes && data.smSync.notes.length > 0 ? (
            <ul className="mt-2 list-inside list-disc space-y-0.5 font-mono text-[10px] text-[#4a5a63]">
              {data.smSync.notes.slice(0, 20).map((n, i) => (
                <li key={`${i}-${n.slice(0, 40)}`}>{n}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {!loading && !error && preset === 'today' && data && data.system.totalPicks === 0 ? (
        <div
          className="mb-6 rounded-xl border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          <strong className="font-semibold">Sin picks para este día operativo ({rangeKeys.from}).</strong>{' '}
          El monitor solo lista filas ya guardadas en la bóveda (
          <span className="font-mono">bt2_daily_picks</span>). Si aún no corrió la generación del
          slate para hoy o no hay eventos elegibles, verás ceros aunque existan partidos terminados en
          otras fuentes. Probá <span className="font-semibold">7d</span> para ver en qué días sí hay
          datos.
        </div>
      ) : null}

      <section className="rounded-2xl border border-[#a4b4be]/15 bg-white/95 p-6 text-[#26343d] shadow-sm md:p-8">
        <div className="flex flex-col justify-between gap-6 border-b border-[#a4b4be]/15 pb-8 md:flex-row md:items-end">
          <div>
            <h1 className="font-serif text-3xl font-bold tracking-tight text-[#26343d] md:text-4xl">
              Monitor de resultados
            </h1>
            <p className="mt-2 text-sm font-medium tracking-wide text-[#52616a]">
              {mode === 'prod'
                ? 'Picks del sistema vs picks que operaste'
                : 'Carril shadow subset5 (SM fixture master + TOA h2h T-60)'}{' '}
              <span className="mx-2 text-[#a4b4be]">|</span>{' '}
              <span className="font-mono text-xs text-[#8B5CF6]">
                TZ: {data?.timezoneLabel ?? shadowData?.timezoneLabel ?? 'America/Bogota'}
              </span>
            </p>
            <div className="mt-4 inline-flex rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] p-1">
              {(
                [
                  ['prod', 'Prod'],
                  ['shadow', 'Shadow'],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setMode(k)}
                  className={[
                    'rounded-md px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest transition-colors',
                    mode === k ? 'bg-white text-[#8B5CF6] shadow-sm' : 'text-[#52616a] hover:text-[#26343d]',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
            {mode === 'shadow' ? (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <div className="inline-flex rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] p-1">
                  {(
                    [
                      ['daily_shadow', 'Diario'],
                      ['historico', 'Histórico'],
                    ] as const
                  ).map(([k, label]) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => {
                        setShadowViewKind(k)
                        setShadowRunKey('')
                      }}
                      className={[
                        'rounded-md px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest transition-colors',
                        shadowViewKind === k
                          ? 'bg-white text-[#8B5CF6] shadow-sm'
                          : 'text-[#52616a] hover:text-[#26343d]',
                      ].join(' ')}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {shadowViewKind === 'historico' ? (
                  <label className="flex min-w-[280px] flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                    Run histórico
                    <select
                      value={shadowRunKey}
                      onChange={(e) => setShadowRunKey(e.target.value)}
                      className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 text-sm text-[#26343d]"
                    >
                      <option value="">Todos (backfill_window)</option>
                      {(shadowData?.runGroups ?? [])
                        .filter((g) => g.runKind === 'backfill_window' || g.runKind === 'day1_lab')
                        .map((g) => (
                          <option key={g.runKey} value={g.runKey}>
                            {g.runKey} · {g.dayFrom}..{g.dayTo} · {g.picksCount} picks
                          </option>
                        ))}
                    </select>
                  </label>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
            <div className="flex rounded-lg border border-[#a4b4be]/25 bg-[#eef4fa] p-1">
              {(
                [
                  ['today', 'Hoy'],
                  ['7d', '7d'],
                  ['30d', '30d'],
                  ['range', 'Rango'],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setPreset(key)}
                  className={[
                    'rounded-md px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest transition-colors',
                    preset === key
                      ? 'bg-white text-[#8B5CF6] shadow-sm'
                      : 'text-[#52616a] hover:text-[#26343d]',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
            {preset === 'range' ? (
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex flex-col gap-0.5 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Desde
                  <input
                    type="date"
                    value={rangeFrom}
                    onChange={(e) => setRangeFrom(e.target.value)}
                    className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-1.5 font-mono text-xs text-[#26343d]"
                  />
                </label>
                <label className="flex flex-col gap-0.5 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Hasta
                  <input
                    type="date"
                    value={rangeTo}
                    onChange={(e) => setRangeTo(e.target.value)}
                    className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-1.5 font-mono text-xs text-[#26343d]"
                  />
                </label>
              </div>
            ) : null}
            {mode === 'prod' ? (
              <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-[#a4b4be]/30 bg-white/80 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                <input
                  type="checkbox"
                  checked={syncFromSportmonks}
                  onChange={(e) => setSyncFromSportmonks(e.target.checked)}
                  className="rounded border-[#a4b4be]/50 text-[#8B5CF6] focus:ring-[#8B5CF6]/40"
                />
                Sync SM
              </label>
            ) : null}
            {mode === 'prod' && syncFromSportmonks ? (
              <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-[#a4b4be]/30 bg-white/80 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                <input
                  type="checkbox"
                  checked={smSyncPendingOnly}
                  onChange={(e) => setSmSyncPendingOnly(e.target.checked)}
                  className="rounded border-[#a4b4be]/50 text-[#8B5CF6] focus:ring-[#8B5CF6]/40"
                />
                Solo pendientes
              </label>
            ) : null}
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-lg border border-[#8B5CF6]/35 bg-white px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-[#6d3bd7] transition-colors hover:bg-[#eef4fa] disabled:opacity-50"
            >
              <span className="font-mono text-[#8B5CF6]" aria-hidden>
                ↻
              </span>
              {loading
                ? 'Cargando…'
                : mode === 'prod' && syncFromSportmonks
                  ? 'Actualizar + SM'
                  : 'Actualizar'}
            </button>
          </div>
        </div>

        <p className="mt-4 font-mono text-[10px] text-[#6e7d86]">
          Rango API: {rangeKeys.from} … {rangeKeys.to}
          {preset === 'range' ? ' (rango manual)' : ` · preset ${preset}`}
          {mode === 'prod' && data?.summaryHumanEs ? (
            <span className="mt-1 block font-sans text-[11px] leading-relaxed text-[#52616a]">
              {data.summaryHumanEs}
            </span>
          ) : null}
          {mode === 'shadow' && shadowData?.summaryHumanEs ? (
            <span className="mt-1 block font-sans text-[11px] leading-relaxed text-[#52616a]">
              {shadowData.summaryHumanEs}
            </span>
          ) : null}
        </p>
        {mode === 'shadow' && shadowViewKind === 'daily_shadow' && !loading && (shadowData?.rowsTotal ?? 0) === 0 ? (
          <div className="mb-3 rounded-xl border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm text-amber-950">
            No hay corridas <span className="font-mono">daily_shadow</span> todavía.
          </div>
        ) : null}

        {loading && !data ? (
          <p className="mt-8 text-sm text-[#52616a]">Cargando métricas…</p>
        ) : null}

        {mode === 'shadow' ? (
          <ShadowMonitorPanel
            data={shadowData}
            loading={loading}
            page={monitorPage}
            totalPages={shadowTotalPages}
            onPrev={() => setMonitorPage((p) => Math.max(1, p - 1))}
            onNext={() => setMonitorPage((p) => Math.min(shadowTotalPages, p + 1))}
          />
        ) : null}

        {mode === 'prod' ? (
          <>
            <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-8">
          <div className="space-y-10 lg:col-span-8">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-serif text-2xl text-[#26343d]">Sistema</h2>
                <p className="flex items-center gap-1 text-[10px] uppercase tracking-[0.2em] text-[#52616a]">
                  <span aria-hidden>ⓘ</span>
                  Denominador excluye pend., void, N.E.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-[#a4b4be]/15 md:grid-cols-2 xl:grid-cols-4">
                <div className="flex aspect-[4/3] flex-col justify-between bg-white p-6 md:aspect-auto md:min-h-[11rem]">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#8B5CF6]">
                    Tasa de acierto
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-5xl font-light text-[#26343d] tabular-nums">
                      {tasaPct != null ? tasaPct.toFixed(1) : '—'}
                    </span>
                    <span className="font-mono text-2xl text-[#52616a]">%</span>
                  </div>
                  <div className="h-1 w-full bg-[#e5eff7]">
                    <div
                      className="h-full bg-[#8B5CF6]"
                      style={{
                        width: `${tasaPct != null ? Math.min(100, tasaPct) : 0}%`,
                      }}
                    />
                  </div>
                </div>
                <div className="flex flex-col justify-between bg-white p-6 md:min-h-[11rem]">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                    ROI (1 u · consenso)
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-5xl font-light tabular-nums text-[#26343d]">
                      {sysRoi?.roiPct != null ? sysRoi.roiPct.toFixed(1) : '—'}
                    </span>
                    <span className="font-mono text-2xl text-[#52616a]">%</span>
                  </div>
                  <p className="mt-2 text-[10px] leading-relaxed text-[#6e7d86]">
                    Net{' '}
                    <span className="font-mono text-[#435368]">
                      {sysRoi != null ? sysRoi.netUnits.toFixed(2) : '—'}
                    </span>{' '}
                    u ·{' '}
                    <span className="font-mono">{sysRoi?.picksCounted ?? 0}</span> picks con cuota
                    {sysRoi != null && sysRoi.picksMissingOdds > 0 ? (
                      <span className="block text-amber-800">
                        ({sysRoi.picksMissingOdds} SI/NO sin cuota en consenso)
                      </span>
                    ) : null}
                  </p>
                </div>
                <div className="flex aspect-[4/3] flex-col justify-between bg-white p-6 md:aspect-auto md:min-h-[11rem]">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                    Evaluados (A / F)
                  </span>
                  <div className="space-y-2">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-[#52616a]">Aciertos</span>
                      <span className="font-mono text-3xl text-[#26343d] tabular-nums">
                        {sys?.hits ?? '—'}
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-[#52616a]">Fallos</span>
                      <span className="font-mono text-3xl text-[#ea580c] tabular-nums">
                        {sys?.misses ?? '—'}
                      </span>
                    </div>
                  </div>
                </div>
                  <div className="grid grid-cols-2 gap-4 bg-white p-6 md:min-h-[11rem]">
                  <div>
                    <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                      Pendientes
                    </span>
                    <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                      {sys?.pending ?? '—'}
                    </span>
                  </div>
                  <div>
                    <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                      Void
                    </span>
                    <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                      {sys?.voidCount ?? '—'}
                    </span>
                  </div>
                  <div className="col-span-2 border-t border-[#e5eff7] pt-3">
                    <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.15em] text-[#52616a]">
                      No evaluable (N.E.)
                    </span>
                    <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                      {sys?.noEvaluable ?? '—'}
                    </span>
                  </div>
                </div>
              </div>
              <p className="text-[11px] leading-relaxed text-[#52616a]">
                En el periodo hay{' '}
                <span className="font-mono text-[#435368]">{sys?.totalPicks ?? '—'}</span> filas en
                bóveda;{' '}
                <span className="font-mono text-[#435368]">{sys?.evaluatedScored ?? '—'}</span>{' '}
                scored (hit+miss). El % usa solo esos scored.
              </p>
            </div>

            <div className="space-y-4">
              <h2 className="font-serif text-2xl text-[#26343d]">Tus picks</h2>
              {!userId ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50/90 px-6 py-4 text-sm text-amber-950">
                  Inicia sesión para ver la tasa sobre picks operados.
                </div>
              ) : tusShowEmpty ? (
                <div className="rounded-xl border border-[#a4b4be]/20 bg-[#eef4fa]/80 px-6 py-8 text-center text-sm text-[#52616a]">
                  No operaste ningún pick en este periodo; aquí aparecerá tu tasa cuando registres
                  operaciones en <span className="font-mono">bt2_picks</span> el mismo día operativo.
                </div>
              ) : yrs != null ? (
                <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-[#a4b4be]/15 md:grid-cols-2">
                  <div className="flex items-center justify-between bg-white p-8">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                        Tu tasa
                      </span>
                      <p className="mt-1 text-[10px] leading-snug text-[#6e7d86]">
                        Sólo sobre picks <strong className="text-[#52616a]">ya evaluados</strong>{' '}
                        (acierto/fallo oficial). Pendientes no entran en el %.
                      </p>
                      <div className="mt-1 flex items-baseline gap-1">
                        <span className="font-mono text-5xl font-light text-[#26343d] tabular-nums">
                          {yrs.hitRatePct != null ? yrs.hitRatePct.toFixed(1) : '—'}
                        </span>
                        <span className="font-mono text-xl text-[#52616a]">%</span>
                      </div>
                      <p className="mt-2 text-[10px] text-[#6e7d86]">
                        {yrs.hits} aciertos · {yrs.misses} fallos · {yrs.pending} pendientes ·{' '}
                        <span className="font-mono text-[#435368]">{yrs.evaluatedScored}</span> /
                        <span className="font-mono text-[#435368]">{yrs.totalPicks}</span> con
                        veredicto · {yrs.totalPicks} operados
                      </p>
                      {yoursHasPending ? (
                        <p className="mt-2 rounded-lg border border-amber-200/90 bg-amber-50/90 px-2 py-2 text-[10px] leading-snug text-amber-950">
                          Tenés picks operados sin resultado oficial aún: el{' '}
                          <strong>{yrs.hitRatePct != null ? yrs.hitRatePct.toFixed(1) : '—'} %</strong>{' '}
                          es <strong>{yrs.hits}</strong> de{' '}
                          <strong>{yrs.evaluatedScored}</strong> evaluados, no de{' '}
                          <strong>{yrs.totalPicks}</strong> operados.
                        </p>
                      ) : null}
                      <p className="mt-3 border-t border-[#e5eff7] pt-3 text-[10px] leading-relaxed text-[#52616a]">
                        ROI 1 u:{' '}
                        <span className="font-mono font-semibold text-[#26343d]">
                          {yrsRoi?.roiPct != null ? `${yrsRoi.roiPct.toFixed(1)} %` : '—'}
                        </span>
                        {' · Net '}
                        <span className="font-mono">{yrsRoi != null ? yrsRoi.netUnits.toFixed(2) : '—'}</span>
                        {' u'}
                        {yrsRoi != null && yrsRoi.picksMissingOdds > 0 ? (
                          <span className="block text-amber-900/90">
                            Sin cuota: {yrsRoi.picksMissingOdds} SI/NO
                          </span>
                        ) : null}
                      </p>
                    </div>
                    <div
                      className="flex h-16 w-16 items-center justify-center rounded-full border border-[#8B5CF6]/25 bg-[#eef4fa] text-[#8B5CF6]"
                      aria-hidden
                    >
                      <svg
                        className="h-7 w-7"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex items-center justify-between bg-white p-8">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                        Operados (total)
                      </span>
                      <span className="mt-1 block font-mono text-5xl font-light text-[#26343d] tabular-nums">
                        {yrs.totalPicks}
                      </span>
                    </div>
                    <div
                      className="flex h-16 w-16 items-center justify-center rounded-full border border-[#a4b4be]/25 bg-[#f8fafc] text-[#52616a]"
                      aria-hidden
                    >
                      <svg
                        className="h-8 w-8 opacity-70"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="1.25"
                      >
                        <circle cx="12" cy="12" r="9" />
                        <circle cx="12" cy="12" r="4" />
                      </svg>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-[#a4b4be]/20 bg-[#eef4fa]/80 px-6 py-6 text-sm text-[#52616a]">
                  Sin bloque «tus picks» (reintentá con sesión iniciada).
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-4">
            <div className="lg:sticky lg:top-4">
              {today ? (
                <div className="rounded-xl border border-[#a4b4be]/15 bg-[#eef4fa]/50 p-1">
                  <div className="rounded-lg border border-[#a4b4be]/10 bg-white p-6">
                    <div className="mb-8 flex items-start justify-between">
                      <div>
                        <h3 className="font-serif text-2xl font-bold text-[#26343d]">
                          {data &&
                          'focusOperatingDayKey' in data &&
                          data.focusOperatingDayKey !== data.todayOperatingDayKey
                            ? 'Ese día'
                            : 'Hoy'}
                        </h3>
                        <p className="text-[10px] uppercase tracking-[0.2em] text-[#52616a]">
                          {today.operatingDayKey} · resumen
                        </p>
                      </div>
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#8B5CF6]/10 text-[#8B5CF6]"
                        aria-hidden
                      >
                        <svg
                          className="h-5 w-5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        >
                          <path
                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </div>
                    </div>
                    <div className="mb-8 space-y-4">
                      <div className="flex items-center justify-between border-b border-[#e5eff7] pb-4">
                        <span className="text-sm font-medium text-[#26343d]">Total picks</span>
                        <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                          {today.totalPicks}
                        </span>
                      </div>
                      <div className="flex items-center justify-between border-b border-[#e5eff7] pb-4">
                        <span className="text-sm font-medium text-[#26343d]">Cerrados</span>
                        <span className="font-mono text-2xl text-[#26343d] tabular-nums">
                          {today.resolved}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[#8B5CF6]">Pendientes</span>
                        <span className="font-mono text-2xl text-[#8B5CF6] tabular-nums">
                          {today.pending}
                        </span>
                      </div>
                    </div>
                    <div className="border-l-2 border-[#8B5CF6] bg-[#eef4fa] p-4">
                      <p className="text-xs font-medium leading-relaxed text-[#435368]">
                        Quedan{' '}
                        <span className="font-mono font-bold text-[#26343d]">{today.pending}</span>{' '}
                        picks esperando resultado final.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-[#a4b4be]/15 bg-[#eef4fa]/60 p-6 text-sm text-[#52616a]">
                  Sin datos de «hoy».
                </div>
              )}
            </div>
          </div>
        </div>

        <section className="mt-12 space-y-4 border-t border-[#a4b4be]/15 pt-10">
          <div className="flex flex-col justify-between gap-4 border-b border-[#a4b4be]/15 pb-4 md:flex-row md:items-end">
            <div className="flex flex-wrap gap-6">
              <button
                type="button"
                onClick={() => setTableFilter('all')}
                className={[
                  'relative pb-3 text-[10px] font-bold uppercase tracking-widest transition-colors',
                  tableFilter === 'all'
                    ? 'text-[#26343d] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#8B5CF6]'
                    : 'text-[#52616a] hover:text-[#26343d]',
                ].join(' ')}
              >
                Todos los picks del sistema
              </button>
              <button
                type="button"
                onClick={() => setTableFilter('mine')}
                className={[
                  'relative pb-3 text-[10px] font-bold uppercase tracking-widest transition-colors',
                  tableFilter === 'mine'
                    ? 'text-[#26343d] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#8B5CF6]'
                    : 'text-[#52616a] hover:text-[#26343d]',
                ].join(' ')}
              >
                Solo los que tomé
              </button>
            </div>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={onlyScored}
                onChange={(e) => setOnlyScored(e.target.checked)}
                className="h-4 w-4 rounded border-[#a4b4be]/40 accent-[#8B5CF6]"
              />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#52616a]">
                Solo con resultado
              </span>
            </label>
          </div>

          <div className="flex flex-wrap items-end gap-3 rounded-xl border border-[#a4b4be]/15 bg-[#f8fafc]/80 p-4">
            <label className="flex min-w-[140px] flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Resultado
              <select
                value={outcomeFilter}
                onChange={(e) => setOutcomeFilter(e.target.value as MonitorOutcomeFilter)}
                className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 text-sm text-[#26343d]"
              >
                <option value="all">Todos</option>
                <option value="si">Sí</option>
                <option value="no">No</option>
                <option value="pendiente">Pendiente</option>
                <option value="void">Void</option>
                <option value="ne">N.E.</option>
              </select>
            </label>
            <label className="flex min-w-[160px] flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Mercado (contiene)
              <input
                value={marketFilter}
                onChange={(e) => setMarketFilter(e.target.value)}
                placeholder="p. ej. 1X2"
                className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 font-mono text-xs text-[#26343d]"
              />
            </label>
            <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Buscar equipo
              <input
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                placeholder="Local o visitante"
                className="rounded-lg border border-[#a4b4be]/35 bg-white px-2 py-2 text-sm text-[#26343d]"
              />
            </label>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#a4b4be]/15 bg-white">
            <table className="w-full border-separate border-spacing-0 text-left">
              <thead>
                <tr className="bg-[#eef4fa]">
                  <th
                    scope="col"
                    className="w-12 border-b border-[#a4b4be]/20 p-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]"
                  >
                    <span className="sr-only">Expandir razón DSR</span>
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Día
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Evento
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Mercado
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Pronóstico
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Resultado
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Cuota*
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    +/-1 u
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-center text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    Tu criterio
                  </th>
                  <th className="border-b border-[#a4b4be]/20 p-4 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#52616a]">
                    ¿Cumplió?
                  </th>
                </tr>
              </thead>
              <tbody className="font-mono text-sm text-[#26343d]">
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="p-8 text-center text-[#52616a]">
                      {loading ? 'Cargando…' : 'No hay filas con los filtros actuales.'}
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((r) => {
                    const dsrOpen = dsrExpandedPickId === r.dailyPickId
                    const panelId = `monitor-dsr-panel-${r.dailyPickId}`
                    const triggerId = `monitor-dsr-trigger-${r.dailyPickId}`
                    return (
                      <Fragment key={r.dailyPickId}>
                        <tr className={dsrOpen ? 'bg-[#f6fafe]' : 'hover:bg-[#f6fafe]'}>
                          <td className="border-b border-[#e5eff7] p-2 align-middle">
                            <button
                              type="button"
                              id={triggerId}
                              aria-expanded={dsrOpen}
                              aria-controls={panelId}
                              onClick={() =>
                                setDsrExpandedPickId((cur) =>
                                  cur === r.dailyPickId ? null : r.dailyPickId,
                                )
                              }
                              className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#8B5CF6]/25 bg-[#eef4fa]/80 text-[#6d3bd7] transition-colors hover:bg-[#e5eff7]"
                              title={dsrOpen ? 'Ocultar razón DSR' : 'Ver razón DSR'}
                            >
                              <svg
                                className={`h-4 w-4 transition-transform ${dsrOpen ? 'rotate-180' : ''}`}
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth="2"
                                aria-hidden
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M19 9l-7 7-7-7"
                                />
                              </svg>
                            </button>
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-[#52616a]">{r.dayKey}</td>
                          <td className="border-b border-[#e5eff7] p-4 font-medium text-[#26343d]">
                            {r.eventLabel}
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-[#52616a]">
                            {r.marketLabel}
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-[#26343d]">
                            {r.selectionLabel}
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-right tabular-nums text-[#26343d]">
                            {r.scoreText}
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-right tabular-nums text-[#52616a]">
                            {r.decimalOdds != null ? r.decimalOdds.toFixed(2) : '—'}
                          </td>
                          <td
                            className={[
                              'border-b border-[#e5eff7] p-4 text-right tabular-nums',
                              r.flatStakeReturnUnits != null && r.flatStakeReturnUnits >= 0
                                ? 'text-emerald-800'
                                : r.flatStakeReturnUnits != null
                                  ? 'text-orange-900'
                                  : 'text-[#52616a]',
                            ].join(' ')}
                          >
                            {r.flatStakeReturnUnits != null
                              ? r.flatStakeReturnUnits >= 0
                                ? `+${r.flatStakeReturnUnits.toFixed(2)}`
                                : r.flatStakeReturnUnits.toFixed(2)
                              : '—'}
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-center">
                            <OperatorClaimPill claim={r.userResultClaim} />
                          </td>
                          <td className="border-b border-[#e5eff7] p-4 text-right">
                            <span
                              className={[
                                'inline-block border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest',
                                outcomeClass(r.outcome),
                              ].join(' ')}
                            >
                              {outcomeLabel(r.outcome)}
                            </span>
                          </td>
                        </tr>
                        {dsrOpen ? (
                          <tr
                            id={panelId}
                            role="region"
                            aria-labelledby={triggerId}
                            className="bg-[#f8fafc]"
                          >
                            <td
                              colSpan={10}
                              className="border-b border-[#e5eff7] px-4 pb-5 pt-0"
                            >
                              <div className="rounded-b-xl rounded-t-none border border-t-0 border-[#e5eff7] bg-white px-4 py-4 shadow-inner">
                                <p className="mb-3 font-sans text-[10px] font-bold uppercase tracking-[0.2em] text-[#8B5CF6]">
                                  Razón DSR
                                </p>
                                <DsrCollapsePanelBody
                                  narrativeEs={r.dsrNarrativeEs}
                                  confidenceLabel={r.dsrConfidenceLabel}
                                  source={r.dsrSource}
                                />
                              </div>
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    )
                  })
                )}
              </tbody>
            </table>
            <p className="mt-2 px-2 text-[10px] leading-relaxed text-[#6e7d86]">
              * Cuota: prioridad{' '}
              <span className="font-mono">reference_decimal_odds</span>; si falta, mediana CDM sobre
              filas del evento (mercado/selección canónicos). Si no hay snapshot de cuotas en BD para
              ese evento → «—». Razón DSR: texto materializado en{' '}
              <span className="font-mono">bt2_daily_picks.dsr_narrative_es</span> al generar la bóveda.
              «Tu criterio» es la marca guardada en ledger (
              <span className="font-mono">PATCH …/user-result-claim</span>
              ); no borra pendientes hasta que evalúe el job oficial CDM.
            </p>
            <div className="flex flex-col gap-3 border-t border-[#e5eff7] px-2 py-4 text-sm text-[#52616a] md:flex-row md:items-center md:justify-between">
              <p>
                Página{' '}
                <span className="font-mono text-[#26343d]">{monitorPage}</span> /{' '}
                <span className="font-mono text-[#26343d]">{monitorTotalPages}</span>
                {rowsTotalFromApi != null ? (
                  <>
                    {' '}
                    ·{' '}
                    <span className="font-mono text-[#26343d]">{rowsTotalFromApi}</span> filas en total
                  </>
                ) : null}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={monitorPage <= 1 || loading}
                  onClick={() => setMonitorPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[#26343d] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  disabled={monitorPage >= monitorTotalPages || loading}
                  onClick={() => setMonitorPage((p) => Math.min(monitorTotalPages, p + 1))}
                  className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[#26343d] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </div>
            </section>
          </>
        ) : null}

        <footer className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-[#a4b4be]/15 pt-10 pb-4 text-[10px] text-[#52616a] md:flex-row">
          <div className="flex items-center gap-2">
            <span className="font-black uppercase tracking-widest">BetTracker 2.0</span>
            <span className="h-1 w-1 rounded-full bg-[#8B5CF6]" aria-hidden />
            <span className="font-bold uppercase tracking-tighter">Monitor interno</span>
          </div>
          <div className="flex flex-wrap justify-center gap-6">
            <button
              type="button"
              onClick={() => setDefsOpen(true)}
              className="font-bold uppercase tracking-widest underline decoration-[#8B5CF6]/30 underline-offset-4 hover:text-[#8B5CF6]"
            >
              Definiciones
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}
