import { motion } from 'framer-motion'
import type { DashboardPerformanceBlock } from '@/types/api'

type Split = DashboardPerformanceBlock['totals']

function StackedRow({
  label,
  sub,
  data,
}: {
  label: string
  sub: string
  data: Split
}) {
  const { wins, losses, pending } = data
  const sum = wins + losses + pending
  if (sum === 0) {
    return (
      <div className="grid gap-2 sm:grid-cols-[minmax(0,10rem)_1fr] sm:items-center">
        <div>
          <p className="text-[11px] font-semibold text-app-fg">{label}</p>
          <p className="text-[10px] leading-snug text-app-muted">{sub}</p>
          <p className="mt-0.5 font-mono text-[10px] tabular-nums text-app-muted">
            n = 0
          </p>
        </div>
        <div className="flex h-8 items-center rounded-md border border-dashed border-app-line bg-neutral-50 px-2 text-[10px] text-app-muted">
          Sin picks en esta categoría
        </div>
      </div>
    )
  }
  const safe = sum
  const pw = (wins / safe) * 100
  const pl = (losses / safe) * 100
  const pp = (pending / safe) * 100

  return (
    <div className="grid gap-2 sm:grid-cols-[minmax(0,10rem)_1fr] sm:items-center">
      <div>
        <p className="text-[11px] font-semibold text-app-fg">{label}</p>
        <p className="text-[10px] leading-snug text-app-muted">{sub}</p>
        <p className="mt-0.5 font-mono text-[10px] tabular-nums text-app-muted">
          n = {sum}
        </p>
      </div>
      <div>
        <div className="flex h-8 w-full overflow-hidden rounded-md border border-app-line bg-neutral-100">
          {wins > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pw}%` }}
              transition={{ type: 'spring', stiffness: 120, damping: 18 }}
              className="flex min-w-0 items-center justify-center bg-emerald-500/90"
              title={`Ganadas: ${wins}`}
            >
              {pw >= 12 && (
                <span className="px-1 text-[10px] font-semibold text-white tabular-nums">
                  {wins}
                </span>
              )}
            </motion.div>
          )}
          {losses > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pl}%` }}
              transition={{ type: 'spring', stiffness: 120, damping: 18 }}
              className="flex min-w-0 items-center justify-center bg-red-500/90"
              title={`Perdidas: ${losses}`}
            >
              {pl >= 12 && (
                <span className="px-1 text-[10px] font-semibold text-white tabular-nums">
                  {losses}
                </span>
              )}
            </motion.div>
          )}
          {pending > 0 && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pp}%` }}
              transition={{ type: 'spring', stiffness: 120, damping: 18 }}
              className="flex min-w-0 items-center justify-center bg-amber-400/95"
              title={`Pendientes: ${pending}`}
            >
              {pp >= 12 && (
                <span className="px-1 text-[10px] font-semibold text-amber-950 tabular-nums">
                  {pending}
                </span>
              )}
            </motion.div>
          )}
        </div>
        {(pw < 12 && wins > 0) ||
        (pl < 12 && losses > 0) ||
        (pp < 12 && pending > 0) ? (
          <p className="mt-1 text-[10px] text-app-muted">
            {wins > 0 && (
              <span className="mr-2 text-emerald-800">G {wins}</span>
            )}
            {losses > 0 && <span className="mr-2 text-red-800">P {losses}</span>}
            {pending > 0 && <span className="text-amber-900">Pen. {pending}</span>}
          </p>
        ) : null}
      </div>
    </div>
  )
}

export function DashboardPerformanceChart({
  performance,
  hasUser,
}: {
  performance: DashboardPerformanceBlock
  hasUser: boolean
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3 text-[10px] text-app-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-emerald-500" />
          Ganadas
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-red-500" />
          Perdidas
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-amber-400" />
          Pendientes
        </span>
      </div>
      <StackedRow
        label="Todos los picks"
        sub="Modelo del día (resultado efectivo)."
        data={performance.totals}
      />
      <StackedRow
        label="Tomados"
        sub={
          hasUser
            ? 'Picks que marcaste como tomados.'
            : 'Elige usuario para ver este desglose (ahora 0).'
        }
        data={performance.taken}
      />
      <StackedRow
        label="No tomados"
        sub={
          hasUser
            ? 'Resto del día sin marcar «tomado».'
            : 'Sin usuario: coincide con el total del día.'
        }
        data={performance.not_taken}
      />
    </div>
  )
}
