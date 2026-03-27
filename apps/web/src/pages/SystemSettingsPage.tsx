import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ViewContextBar } from '@/components/ViewContextBar'
import { useRevertRecentPickOutcomesMutation } from '@/hooks/useRevertRecentPickOutcomesMutation'
import { useTrackingUser } from '@/hooks/useTrackingUser'

export default function SystemSettingsPage() {
  const { userId } = useTrackingUser()
  const [revertMinutes, setRevertMinutes] = useState<number>(90)
  const revertRecentOutcomesM = useRevertRecentPickOutcomesMutation(userId)

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
    </div>
  )
}

