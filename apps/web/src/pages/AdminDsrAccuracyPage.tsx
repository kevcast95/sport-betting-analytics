import { useCallback, useEffect, useState } from 'react'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import { fetchBt2AdminDsrDay } from '@/lib/api'
import type { Bt2AdminDsrDayOut } from '@/lib/bt2Types'
import {
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

export default function AdminDsrAccuracyPage() {
  const [operatingDayKey, setOperatingDayKey] = useState(defaultOperatingDayKey)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Bt2AdminDsrDayOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Tasa de acierto (modelo)"
              value={
                s.hitRatePct != null ? `${s.hitRatePct.toFixed(1)}%` : '—'
              }
              hint="Sobre aciertos + fallos con resultado modelo."
            />
            <KpiCard
              label="Eventos en snapshot"
              value={String(s.distinctEventsInVault)}
              hint="Distintos en bóveda del día."
            />
            <KpiCard
              label="Liquidados (modelo)"
              value={String(s.picksSettledWithModel)}
            />
            <KpiCard label="Aciertos (hit)" value={String(s.modelHits)} />
            <KpiCard label="Fallos (miss)" value={String(s.modelMisses)} />
            <KpiCard label="Void" value={String(s.modelVoids)} />
            <KpiCard label="N/D" value={String(s.modelNa)} />
          </div>

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

          <footer className="border-t border-[#a4b4be]/15 pt-6">
            <p className="text-xs leading-relaxed text-[#52616a]">
              {s.summaryHumanEs}
            </p>
            <p className="mt-3 text-[10px] text-[#6e7d86]">
              Datos agregados en servidor; sin exportación CSV en esta versión.
              Uso interno del protocolo BT2.
            </p>
          </footer>
        </>
      ) : loading ? (
        <p className="text-center text-sm text-[#52616a]">Cargando métricas…</p>
      ) : null}
    </div>
  )
}
