import { useCallback, useEffect, useState } from 'react'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import {
  fetchBt2AdminDsrDay,
  fetchBt2AdminVaultPickDistribution,
} from '@/lib/api'
import type {
  Bt2AdminDsrDayOut,
  Bt2AdminVaultPickDistributionOut,
} from '@/lib/bt2Types'
import {
  dsrConfidenceLabelEs,
  dsrSourceDescriptionAdminEs,
  modelPredictionResultEs,
  pickStatusLabelEs,
} from '@/lib/bt2ProtocolLabels'

function defaultOperatingDayKey(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function KpiCard(props: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-[#a4b4be]/15 bg-white/90 p-5">
      <p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
        {props.label}
      </p>
      <div>
        <p className="font-mono text-2xl font-semibold tabular-nums text-[#26343d]">
          {props.value}
        </p>
        {props.hint ? (
          <p className="mt-1 text-[10px] text-[#52616a]/85">{props.hint}</p>
        ) : null}
      </div>
    </div>
  )
}

function formatScoreBucketLabel(bucket: number): string {
  if (bucket === -1) return 'Sin score (NULL)'
  return String(bucket)
}

export default function AdminDsrAccuracyPage() {
  const [operatingDayKey, setOperatingDayKey] = useState(defaultOperatingDayKey)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [distError, setDistError] = useState<string | null>(null)
  const [data, setData] = useState<Bt2AdminDsrDayOut | null>(null)
  const [distData, setDistData] =
    useState<Bt2AdminVaultPickDistributionOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setDistError(null)
    try {
      const out = await fetchBt2AdminDsrDay(operatingDayKey)
      setData(out)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('Falta VITE_BT2_ADMIN_API_KEY')) {
        setError(
          'Configura VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
        )
      } else if (msg.startsWith('503') || msg.includes('503')) {
        setError(
          'Analytics admin no disponible: define BT2_ADMIN_API_KEY en el entorno del API.',
        )
      } else if (msg.startsWith('401') || msg.includes('401')) {
        setError('Clave admin rechazada; revisa VITE_BT2_ADMIN_API_KEY.')
      } else {
        setError(msg.length > 220 ? `${msg.slice(0, 220)}…` : msg)
      }
      setData(null)
    }
    try {
      const d = await fetchBt2AdminVaultPickDistribution(operatingDayKey)
      setDistData(d)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setDistData(null)
      if (msg.includes('Falta VITE_BT2_ADMIN_API_KEY')) {
        setDistError(
          'Misma clave admin que la sección superior: revisa VITE_BT2_ADMIN_API_KEY.',
        )
      } else {
        setDistError(msg.length > 180 ? `${msg.slice(0, 180)}…` : msg)
      }
    } finally {
      setLoading(false)
    }
  }, [operatingDayKey])

  useEffect(() => {
    void load()
  }, [load])

  const s = data?.summary

  return (
    <div className="w-full space-y-8" aria-label="Precisión DSR administración">
      <BunkerViewHeader
        title="Precisión del modelo (DSR)"
        subtitle="Solo uso interno · día operativo seleccionado"
        rightActions={
          <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center">
            <label className="flex flex-col gap-1 text-right">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                Día operativo
              </span>
              <input
                type="date"
                value={operatingDayKey}
                onChange={(e) => setOperatingDayKey(e.target.value)}
                className="rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-1.5 font-mono text-xs text-[#26343d]"
              />
            </label>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="rounded-lg border border-[#8B5CF6]/35 bg-[#e9ddff]/40 px-4 py-2 text-xs font-bold uppercase tracking-wide text-[#6d3bd7] disabled:opacity-50"
            >
              {loading ? 'Cargando…' : 'Actualizar'}
            </button>
          </div>
        }
      />

      <section
        aria-label="Leyenda"
        className="rounded-xl border border-[#a4b4be]/15 bg-[#f6fafe]/80 px-4 py-3 text-xs leading-relaxed text-[#52616a]"
      >
        <p className="font-semibold text-[#26343d]">Cómo leer esta pantalla</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>
            <strong className="font-semibold text-[#374151]">Liquidación vs modelo</strong>{' '}
            (tabla y KPI de aciertos): contraste entre resultado del pick liquidado y la
            predicción del modelo guardada — no es la etiqueta de confianza DSR ni el score
            de completitud CDM. Tampoco debe leerse como promesa de +EV ni de maximizar
            retorno: la premisa de producto del DSR es lectura fundamentada en datos del
            input (D-06-027).
          </li>
          <li>
            <strong className="font-semibold text-[#374151]">Distribución del snapshot</strong>{' '}
            (conteos por etiqueta, fuente y buckets): describe las filas diarias de bóveda
            generadas ese día; cada bloque mide algo distinto (US-BE-035 / D-06-026 §5).
          </li>
        </ul>
      </section>

      {error ? (
        <div
          className="rounded-xl border border-[#fee2e2] bg-[#fff1f2] px-4 py-3 text-sm text-[#9b1c1c]"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {!error && !loading && s && s.picksSettledWithModel === 0 ? (
        <p className="rounded-xl border border-[#a4b4be]/20 bg-[#eef4fa]/60 px-4 py-6 text-center text-sm text-[#52616a]">
          No hay picks liquidados con medición de modelo para este día operativo.
        </p>
      ) : null}

      {s ? (
        <>
          <section aria-label="KPI liquidación vs modelo">
            <h3 className="mb-3 text-sm font-semibold tracking-tight text-[#26343d]">
              Liquidación y contraste con predicción del modelo
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                label="Tasa de acierto (liquidación vs modelo)"
                value={
                  s.hitRatePct != null ? `${s.hitRatePct.toFixed(1)}%` : '—'
                }
                hint="Solo hits+misses con resultado de modelo; no es confianza DSR ni % acierto de producto a 30d."
              />
              <KpiCard
                label="Eventos distintos (snapshot bóveda)"
                value={String(s.distinctEventsInVault)}
                hint="Eventos únicos en filas diarias de bóveda ese día."
              />
              <KpiCard
                label="Picks liquidados (con modelo)"
                value={String(s.picksSettledWithModel)}
              />
              <KpiCard label="Aciertos (hit)" value={String(s.modelHits)} />
              <KpiCard label="Fallos (miss)" value={String(s.modelMisses)} />
              <KpiCard label="Void" value={String(s.modelVoids)} />
              <KpiCard label="N/D" value={String(s.modelNa)} />
            </div>
          </section>

          <section className="overflow-hidden rounded-xl border border-[#a4b4be]/15 bg-white">
            <div className="border-b border-[#a4b4be]/10 px-6 py-4">
              <h3 className="text-sm font-semibold tracking-tight text-[#26343d]">
                Auditoría por pick
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-left">
                <thead>
                  <tr className="bg-[#eef4fa]">
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      Pick
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      Usuario
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      Evento
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      Estado pick
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      vs modelo
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      Mercado mod.
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                      Selección mod.
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e5eff7]">
                  {(data?.auditRows ?? []).length === 0 ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-4 py-10 text-center text-sm text-[#52616a]"
                      >
                        Sin filas de auditoría para este día.
                      </td>
                    </tr>
                  ) : (
                    (data?.auditRows ?? []).map((r) => (
                      <tr
                        key={`${r.pickId}-${r.userId}`}
                        className="hover:bg-[#f6fafe]/80"
                      >
                        <td className="px-4 py-3 font-mono text-xs text-[#26343d]">
                          {r.pickId}
                        </td>
                        <td
                          className="max-w-[8rem] truncate px-4 py-3 font-mono text-[10px] text-[#52616a]"
                          title={r.userId}
                        >
                          {r.userId}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-[#26343d]">
                          {r.eventId}
                        </td>
                        <td className="px-4 py-3 text-xs text-[#26343d]">
                          {pickStatusLabelEs(r.status)}
                        </td>
                        <td className="px-4 py-3 text-xs font-semibold text-[#435368]">
                          {modelPredictionResultEs(r.modelPredictionResult)}
                        </td>
                        <td className="px-4 py-3 font-mono text-[10px] text-[#52616a]">
                          {r.modelMarketCanonical ?? '—'}
                        </td>
                        <td className="px-4 py-3 font-mono text-[10px] text-[#52616a]">
                          {r.modelSelectionCanonical ?? '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <footer className="border-t border-[#a4b4be]/15 pt-4">
            <p className="text-xs leading-relaxed text-[#52616a]">
              {s.summaryHumanEs}
            </p>
          </footer>
        </>
      ) : loading ? (
        <p className="text-center text-sm text-[#52616a]">Cargando métricas…</p>
      ) : null}

      <section
        aria-label="Distribución snapshot bóveda"
        className="space-y-4 border-t border-[#a4b4be]/20 pt-8"
      >
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-[#26343d]">
            Distribución del snapshot de bóveda (filas diarias)
          </h3>
          <p className="mt-2 text-xs leading-relaxed text-[#52616a]">
            Tres bloques separados:{' '}
            <span className="font-medium text-[#374151]">
              etiqueta de confianza simbólica
            </span>
            ,{' '}
            <span className="font-medium text-[#374151]">fuente de la señal</span> y{' '}
            <span className="font-medium text-[#374151]">
              heurística de completitud CDM (score)
            </span>
            . No deben fusionarse en un solo KPI.
          </p>
        </div>

        {distError ? (
          <div
            className="rounded-xl border border-[#fee2e2] bg-[#fff1f2] px-4 py-3 text-sm text-[#9b1c1c]"
            role="alert"
          >
            {distError}
          </div>
        ) : null}

        {distData && !distError ? (
          <>
            <p className="font-mono text-[10px] text-[#6e7d86]">
              Total filas diarias:{' '}
              <span className="tabular-nums text-[#26343d]">
                {distData.totalDailyPickRows}
              </span>
            </p>

            <div className="grid gap-6 lg:grid-cols-3">
              <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-4">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Por etiqueta de confianza (simbólica)
                </h4>
                <p className="mt-1 text-[10px] leading-snug text-[#6e7d86]">
                  Conteo por <code className="font-mono">dsr_confidence_label</code>; no
                  implica tasa de acierto real.
                </p>
                <ul className="mt-3 space-y-2 font-mono text-xs text-[#26343d]">
                  {distData.byDsrConfidenceLabel.length === 0 ? (
                    <li className="text-[#52616a]">Sin filas.</li>
                  ) : (
                    distData.byDsrConfidenceLabel.map((row) => (
                      <li
                        key={row.key || 'empty'}
                        className="flex justify-between gap-2 border-b border-[#eef4fa] pb-2"
                      >
                        <span>
                          {row.key
                            ? dsrConfidenceLabelEs(row.key)
                            : '—'}{' '}
                          <span className="text-[10px] text-[#6e7d86]">
                            ({row.key || 'vacío'})
                          </span>
                        </span>
                        <span className="tabular-nums font-semibold">{row.count}</span>
                      </li>
                    ))
                  )}
                </ul>
              </div>

              <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-4">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Por fuente de señal
                </h4>
                <p className="mt-1 text-[10px] leading-snug text-[#6e7d86]">
                  Conteo por <code className="font-mono">dsr_source</code> (p. ej. API vs
                  reglas).
                </p>
                <ul className="mt-3 space-y-2 text-xs text-[#26343d]">
                  {distData.byDsrSource.length === 0 ? (
                    <li className="text-[#52616a]">Sin filas.</li>
                  ) : (
                    distData.byDsrSource.map((row) => (
                      <li
                        key={row.key || 'empty'}
                        className="border-b border-[#eef4fa] pb-2"
                      >
                        <div className="flex justify-between gap-2 font-mono">
                          <span>{row.key || '—'}</span>
                          <span className="tabular-nums font-semibold">{row.count}</span>
                        </div>
                        <p className="mt-1 text-[10px] text-[#6e7d86]">
                          {dsrSourceDescriptionAdminEs(row.key)}
                        </p>
                      </li>
                    ))
                  )}
                </ul>
              </div>

              <div className="rounded-xl border border-[#a4b4be]/15 bg-white p-4">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
                  Por score de completitud CDM
                </h4>
                <p className="mt-1 text-[10px] leading-snug text-[#6e7d86]">
                  Buckets de <code className="font-mono">data_completeness_score</code>;{' '}
                  <span className="font-mono">-1</span> = valor NULL en servidor.
                </p>
                <ul className="mt-3 space-y-2 font-mono text-xs text-[#26343d]">
                  {distData.scoreBuckets.length === 0 ? (
                    <li className="text-[#52616a]">Sin filas.</li>
                  ) : (
                    distData.scoreBuckets.map((row) => (
                      <li
                        key={row.scoreBucket}
                        className="flex justify-between gap-2 border-b border-[#eef4fa] pb-2"
                      >
                        <span>{formatScoreBucketLabel(row.scoreBucket)}</span>
                        <span className="tabular-nums font-semibold">{row.count}</span>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>

            {distData.summaryHumanEs ? (
              <p className="text-xs leading-relaxed text-[#52616a]">
                {distData.summaryHumanEs}
              </p>
            ) : null}
          </>
        ) : !distError && !loading ? (
          <p className="text-sm text-[#52616a]">
            No hay datos de distribución (revisa la clave admin o el endpoint).
          </p>
        ) : null}
      </section>

      {s || distData ? (
        <p className="text-[10px] text-[#6e7d86]">
          Datos agregados en servidor; sin exportación CSV en esta versión. Uso interno del
          protocolo BT2.
        </p>
      ) : null}
    </div>
  )
}
