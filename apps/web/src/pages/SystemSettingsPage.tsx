import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ViewContextBar } from '@/components/ViewContextBar'
import { fetchJson } from '@/lib/api'
import { useRevertRecentPickOutcomesMutation } from '@/hooks/useRevertRecentPickOutcomesMutation'
import { useTrackingUser } from '@/hooks/useTrackingUser'

function pipelineRunningMessage(
  step: 'ingest' | 'select' | 'window',
  sport: 'football' | 'tennis',
  runDate: string,
  slot: 'morning' | 'afternoon',
): string {
  const sp = sport === 'tennis' ? 'tenis' : 'fútbol'
  switch (step) {
    case 'ingest':
      return `Ingestando eventos desde SofaScore (${sp}, ${runDate}). Espera a que termine el proceso…`
    case 'select':
      return `Recalculando candidatos y escribiendo JSON de salida (${sp}, ${runDate}). Esto puede tardar 1–2 minutos…`
    case 'window':
      return `Ejecutando ventana ${slot === 'morning' ? 'mañana' : 'tarde'}: scraping, batches y DeepSeek (${sp}, ${runDate}). Suele tardar varios minutos; no cierres la pestaña.`
    default:
      return 'Ejecutando…'
  }
}

export default function SystemSettingsPage() {
  const { userId } = useTrackingUser()
  const [revertMinutes, setRevertMinutes] = useState<number>(90)
  const revertRecentOutcomesM = useRevertRecentPickOutcomesMutation(userId)
  const todayLocal = new Date().toISOString().slice(0, 10)
  const [step, setStep] = useState<'ingest' | 'select' | 'window'>('ingest')
  const [sport, setSport] = useState<'football' | 'tennis'>('tennis')
  const [runDate, setRunDate] = useState<string>(todayLocal)
  const [slot, setSlot] = useState<'morning' | 'afternoon'>('morning')
  const [limitIngest, setLimitIngest] = useState<number>(220)
  const [limitSelect, setLimitSelect] = useState<number>(200)
  const [isReplayRunning, setIsReplayRunning] = useState(false)
  const [replayBusyHint, setReplayBusyHint] = useState<string | null>(null)
  const [replayError, setReplayError] = useState<string | null>(null)
  const [replayResult, setReplayResult] = useState<{
    ok: boolean
    step: 'ingest' | 'select' | 'window'
    sport: 'football' | 'tennis'
    run_date: string
    slot?: 'morning' | 'afternoon' | null
    daily_run_id?: number | null
    subprocess_exit_code: number
    stdout_excerpt?: string | null
    stderr_excerpt?: string | null
    message?: string | null
  } | null>(null)

  async function runReplayStep() {
    setIsReplayRunning(true)
    setReplayError(null)
    setReplayResult(null)
    setReplayBusyHint(pipelineRunningMessage(step, sport, runDate, slot))
    try {
      const body: Record<string, unknown> = {
        step,
        sport,
        run_date: runDate,
      }
      if (step === 'ingest') body.limit_ingest = limitIngest
      if (step === 'select') body.limit_select = limitSelect
      if (step === 'window') body.slot = slot
      const res = await fetchJson<typeof replayResult>('/ops/pipeline/replay', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setReplayResult(res)
    } catch (err) {
      setReplayError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsReplayRunning(false)
      setReplayBusyHint(null)
    }
  }

  return (
    <div className="space-y-6">
      <ViewContextBar
        crumbs={[
          { label: 'Inicio', to: '/' },
          { label: 'Configuración del sistema' },
        ]}
      />

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-app-fg md:text-3xl">
          Configuración del sistema
        </h1>
        <p className="mt-1 text-sm text-app-muted">
          Acciones operativas sensibles y controles manuales.
        </p>
      </div>

      <section className="rounded-xl border border-app-line bg-app-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-violet-900/80">
          Operación
        </p>
        <p className="mt-2 text-sm text-app-muted">
          Revertir cierres manuales recientes y volver al resultado automático del sistema.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-[12rem,1fr] sm:items-end">
          <label className="block text-xs text-app-muted">
            Ventana
            <select
              value={String(revertMinutes)}
              onChange={(e) => setRevertMinutes(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
              disabled={revertRecentOutcomesM.isPending}
            >
              <option value="30">30 min</option>
              <option value="60">60 min</option>
              <option value="90">90 min</option>
              <option value="120">120 min</option>
            </select>
          </label>

          <button
            type="button"
            className="rounded-md border border-app-line bg-white px-3 py-2 text-sm text-app-fg shadow-sm disabled:opacity-40"
            disabled={revertRecentOutcomesM.isPending || userId == null}
            onClick={() => revertRecentOutcomesM.mutate(revertMinutes)}
            title="Limpia user_outcome reciente y vuelve a pick_results."
          >
            Revertir últimos {revertMinutes} min → Auto
          </button>
        </div>

        {userId == null && (
          <p className="mt-3 text-xs text-app-muted">
            No hay usuario configurado en esta sesión. Esta acción requiere usuario.
          </p>
        )}

        {revertRecentOutcomesM.isError && (
          <p className="mt-3 text-xs text-app-danger whitespace-pre-wrap">
            {(revertRecentOutcomesM.error as Error).message}
          </p>
        )}
      </section>

      <section className="rounded-xl border border-app-line bg-app-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-violet-900/80">
          Rendimiento y validación
        </p>
        <p className="mt-2 text-sm text-app-muted">
          Herramientas de análisis del sistema para calidad y estabilidad.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to="/backtests"
            className="rounded-md border border-app-line bg-white px-3 py-2 text-sm text-app-fg shadow-sm hover:bg-violet-50/60"
          >
            Backtests
          </Link>
          <Link
            to="/api-readiness"
            className="rounded-md border border-app-line bg-white px-3 py-2 text-sm text-app-fg shadow-sm hover:bg-violet-50/60"
          >
            API Readiness
          </Link>
        </div>
      </section>

      <section className="rounded-xl border border-app-line bg-app-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-violet-900/80">
          Pruebas de pipeline
        </p>
        <p className="mt-2 text-sm text-app-muted">
          Re-dispara ingest, select o DS por ventana sin salir del panel.
        </p>
        <p className="mt-1 text-[11px] text-app-muted">
          El servidor ejecuta el comando completo y devuelve un resumen al finalizar (no hay streaming línea a
          línea como en terminal). Mientras corre verás el indicador de progreso abajo.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block text-xs text-app-muted">
            Paso
            <select
              value={step}
              onChange={(e) => setStep(e.target.value as 'ingest' | 'select' | 'window')}
              className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
              disabled={isReplayRunning}
            >
              <option value="ingest">Ingesta</option>
              <option value="select">Actualizar candidates</option>
              <option value="window">Correr DS por ventana</option>
            </select>
          </label>
          <label className="block text-xs text-app-muted">
            Deporte
            <select
              value={sport}
              onChange={(e) => setSport(e.target.value as 'football' | 'tennis')}
              className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
              disabled={isReplayRunning}
            >
              <option value="tennis">Tennis</option>
              <option value="football">Fútbol</option>
            </select>
          </label>
          <label className="block text-xs text-app-muted">
            Fecha run
            <input
              type="date"
              value={runDate}
              onChange={(e) => setRunDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
              disabled={isReplayRunning}
            />
          </label>
          {step === 'window' ? (
            <label className="block text-xs text-app-muted">
              Ventana
              <select
                value={slot}
                onChange={(e) => setSlot(e.target.value as 'morning' | 'afternoon')}
                className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
                disabled={isReplayRunning}
              >
                <option value="morning">Mañana</option>
                <option value="afternoon">Tarde</option>
              </select>
            </label>
          ) : step === 'ingest' ? (
            <label className="block text-xs text-app-muted">
              Límite ingest
              <input
                type="number"
                min={1}
                max={500}
                value={limitIngest}
                onChange={(e) => setLimitIngest(Number(e.target.value))}
                className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
                disabled={isReplayRunning}
              />
            </label>
          ) : (
            <label className="block text-xs text-app-muted">
              Límite select
              <input
                type="number"
                min={1}
                max={1000}
                value={limitSelect}
                onChange={(e) => setLimitSelect(Number(e.target.value))}
                className="mt-1 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
                disabled={isReplayRunning}
              />
            </label>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={runReplayStep}
            disabled={isReplayRunning}
            className="inline-flex items-center gap-2 rounded-md border border-app-line bg-white px-3 py-2 text-sm text-app-fg shadow-sm disabled:opacity-40"
          >
            {isReplayRunning && (
              <span
                className="inline-block size-3.5 shrink-0 animate-spin rounded-full border-2 border-app-line border-t-violet-700"
                aria-hidden
              />
            )}
            {isReplayRunning ? 'Ejecutando…' : 'Ejecutar paso'}
          </button>
          <p className="text-xs text-app-muted">
            Orden recomendado: ingest → select → window (morning / afternoon).
          </p>
        </div>

        {isReplayRunning && replayBusyHint && (
          <div
            className="mt-3 flex gap-3 rounded-md border border-violet-200 bg-violet-50/50 px-3 py-2 text-xs text-app-fg"
            role="status"
            aria-live="polite"
          >
            <span
              className="mt-0.5 inline-block size-4 shrink-0 animate-spin rounded-full border-2 border-violet-200 border-t-violet-800"
              aria-hidden
            />
            <p className="leading-snug">{replayBusyHint}</p>
          </div>
        )}

        {replayError && (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50/60 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-red-900">Error</p>
            <p className="mt-1 text-xs text-red-800 whitespace-pre-wrap">{replayError}</p>
          </div>
        )}

        {replayResult && (
          <div
            className={`mt-3 rounded-md border bg-white p-3 text-xs text-app-fg ${
              replayResult.ok ? 'border-emerald-200' : 'border-red-200 bg-red-50/40'
            }`}
          >
            <p className="font-medium">
              {replayResult.ok ? 'Completado' : 'Falló el paso'} · {replayResult.message ?? 'Sin mensaje'}
            </p>
            {!replayResult.ok && (
              <p className="mt-1 text-[11px] text-red-800">
                Revisa stderr/stdout abajo. Si el API respondió 404, suele faltar un daily_run para esa fecha:
                ejecuta ingest primero.
              </p>
            )}
            <p className="mt-1 text-app-muted">
              run_id: {replayResult.daily_run_id ?? '—'} · exit_code: {replayResult.subprocess_exit_code}
            </p>
            {replayResult.stderr_excerpt && (
              <details className="mt-2">
                <summary className="cursor-pointer text-app-muted">Ver stderr</summary>
                <pre className="mt-1 max-h-64 overflow-auto rounded border border-app-line bg-app-card p-2 text-[11px]">
                  {replayResult.stderr_excerpt}
                </pre>
              </details>
            )}
            {replayResult.stdout_excerpt && (
              <details className="mt-2">
                <summary className="cursor-pointer text-app-muted">Ver stdout</summary>
                <pre className="mt-1 max-h-64 overflow-auto rounded border border-app-line bg-app-card p-2 text-[11px]">
                  {replayResult.stdout_excerpt}
                </pre>
              </details>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

