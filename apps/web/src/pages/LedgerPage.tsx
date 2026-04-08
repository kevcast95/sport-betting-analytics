import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ViewTourModal } from '@/components/tours/ViewTourModal'
import { getTourScript } from '@/components/tours/tourScripts'
import { useTourStore } from '@/store/useTourStore'
import {
  IconChevronLeft,
  IconChevronRight,
  IconExpandMore,
  IconSearch,
} from '@/components/bt2StitchIcons'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import { LedgerTable } from '@/components/ledger/LedgerTable'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { protocolWinRate } from '@/lib/ledgerAnalytics'
import type { LedgerRow } from '@/store/useTradeStore'
import { useTradeStore } from '@/store/useTradeStore'
import { useUserStore } from '@/store/useUserStore'

const PAGE = 10

function disciplineFactorFromDp(dp: number): {
  factor: number
  label: string
  barPct: number
} {
  const factor = Math.min(10, Math.round((dp / 150) * 10) / 10)
  const barPct = Math.min(100, Math.max(0, (factor / 10) * 100))
  const label =
    factor >= 8
      ? 'Elite'
      : factor >= 6
        ? 'Avanzado'
        : factor >= 4
          ? 'Sólido'
          : factor >= 2
            ? 'En desarrollo'
            : 'Novato'
  return { factor, label, barPct }
}

const LEDGER_TOUR = getTourScript('ledger')!

export default function LedgerPage() {
  const ledger = useTradeStore((s) => s.ledger)
  const disciplinePoints = useUserStore((s) => s.disciplinePoints)
  const [protocol, setProtocol] = useState<string>('TODOS')
  const [idQuery, setIdQuery] = useState('')
  const [page, setPage] = useState(0)
  const [detail, setDetail] = useState<LedgerRow | null>(null)

  const hasSeenTour = useTourStore((s) => s.seenTourKeys.includes('ledger'))
  const markTourSeen = useTourStore((s) => s.markTourSeen)
  const resetTour = useTourStore((s) => s.resetTour)
  const [tourOpen, setTourOpen] = useState(false)

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  useEffect(() => {
    if (!hasSeenTour) {
      const t = setTimeout(() => setTourOpen(true), 500)
      return () => clearTimeout(t)
    }
  }, [hasSeenTour])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    [],
  )

  const protocols = useMemo(() => {
    const u = new Set<string>()
    for (const r of ledger) {
      const m = r.marketClass ?? ''
      if (m) u.add(m)
    }
    return ['TODOS', ...[...u].sort()]
  }, [ledger])

  const filtered = useMemo(() => {
    let rows = [...ledger].sort(
      (a, b) => new Date(b.settledAt).getTime() - new Date(a.settledAt).getTime(),
    )
    if (protocol !== 'TODOS') {
      rows = rows.filter((r) => (r.marketClass ?? '') === protocol)
    }
    const q = idQuery.trim().toLowerCase()
    if (q) {
      rows = rows.filter((r) => r.pickId.toLowerCase().includes(q))
    }
    return rows
  }, [ledger, protocol, idQuery])

  const eff = useMemo(
    () => (protocol === 'TODOS' ? 0 : protocolWinRate(ledger, protocol)),
    [ledger, protocol],
  )

  const totalDpFiltered = useMemo(
    () => filtered.reduce((s, r) => s + (r.earnedDp ?? 0), 0),
    [filtered],
  )

  const pageRows = useMemo(() => {
    const start = page * PAGE
    return filtered.slice(start, start + PAGE)
  }, [filtered, page])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE))

  useEffect(() => {
    if (page > 0 && page >= totalPages) {
      setPage(Math.max(0, totalPages - 1))
    }
  }, [page, totalPages])

  const { factor, label: factorLabel, barPct } = disciplineFactorFromDp(
    disciplinePoints,
  )

  const segmentIdleCopy =
    'Selecciona una clase de mercado arriba para ver la tasa de acierto sobre las liquidaciones filtradas. Los DP miden consistencia de proceso, no el acierto puntual.'

  const startShown = filtered.length === 0 ? 0 : page * PAGE + 1
  const endShown =
    filtered.length === 0 ? 0 : Math.min((page + 1) * PAGE, filtered.length)

  const paginationSlot =
    filtered.length > 0 ? (
      <>
        <p className="text-xs font-medium text-[#52616a]">
          Mostrando {startShown}-{endShown} de {filtered.length}{' '}
          {filtered.length === 1 ? 'análisis' : 'análisis'}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 0}
            className="rounded-lg border border-[#a4b4be]/15 bg-white p-2 transition-colors hover:bg-[#f6fafe] disabled:opacity-50"
            aria-label="Página anterior"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            <IconChevronLeft className="text-[#26343d]" />
          </button>
          <button
            type="button"
            disabled={page >= totalPages - 1}
            className="rounded-lg border border-[#a4b4be]/15 bg-white p-2 transition-colors hover:bg-[#f6fafe] disabled:opacity-50"
            aria-label="Página siguiente"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
          >
            <IconChevronRight className="text-[#26343d]" />
          </button>
        </div>
      </>
    ) : null

  return (
    <div className="mx-auto w-full max-w-7xl space-y-10" aria-label="Libro mayor estratégico">
      <BunkerViewHeader
        title="Libro mayor estratégico"
        subtitle="Registro cronológico de ejecución disciplinada."
        onHelpClick={() => {
          resetTour('ledger')
          setTourOpen(true)
        }}
        rightActions={
          <div className="flex w-full max-w-md flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1 sm:min-w-[12rem]">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#6e7d86]">
                <IconSearch className="h-4 w-4" />
              </span>
              <input
                type="search"
                value={idQuery}
                onChange={(e) => {
                  setIdQuery(e.target.value)
                  setPage(0)
                }}
                placeholder="Buscar por ID…"
                className="w-full rounded-xl border-none bg-[#ddeaf3] py-2.5 pl-10 pr-4 text-sm font-medium text-[#26343d] transition-all placeholder:text-[#52616a]/70 focus:bg-white focus:ring-1 focus:ring-[#6d3bd7]"
                style={monoStyle}
              />
            </div>
            <div className="relative sm:w-48">
              <label htmlFor="ledger-market-class" className="sr-only">
                Clase de mercado
              </label>
              <select
                id="ledger-market-class"
                value={protocol}
                onChange={(e) => {
                  setProtocol(e.target.value)
                  setPage(0)
                }}
                className="h-full w-full appearance-none rounded-xl border-none bg-[#ddeaf3] py-2.5 pl-4 pr-10 text-sm font-medium text-[#26343d] transition-all focus:bg-white focus:ring-1 focus:ring-[#6d3bd7]"
              >
                {protocols.map((p) => (
                  <option key={p} value={p}>
                    {p === 'TODOS' ? 'Todas las clases' : p}
                  </option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#6e7d86]">
                <IconExpandMore />
              </span>
            </div>
          </div>
        }
      />

      <LedgerTable
        rows={pageRows}
        monoStyle={monoStyle}
        onViewDetails={setDetail}
        pagination={paginationSlot}
      />

      <section className="grid grid-cols-1 gap-8 md:grid-cols-3">
        <div className="flex items-center gap-8 rounded-xl bg-[#eef4fa] p-8 md:col-span-2">
          <div
            className="aspect-video w-1/3 min-w-[120px] shrink-0 overflow-hidden rounded-lg border border-[#a4b4be]/15 bg-gradient-to-br from-[#e9ddff]/80 via-[#ddeaf3] to-[#d5e5ef]"
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <h4 className="mb-2 text-xs font-bold uppercase tracking-widest text-[#52616a]">
              Tasa de acierto en el segmento
            </h4>
            <p className="text-sm leading-relaxed text-[#26343d]">
              {protocol !== 'TODOS' ? (
                <>
                  En la clase{' '}
                  <span
                    className="font-mono font-bold text-[#6d3bd7]"
                    style={monoStyle}
                  >
                    {protocol}
                  </span>
                  ,{' '}
                  <span
                    className="font-mono font-bold text-[#6d3bd7]"
                    style={monoStyle}
                  >
                    {eff.toFixed(1)}%
                  </span>{' '}
                  de las liquidaciones filtradas fueron positivas. DP acumulado
                  en esta vista:{' '}
                  <span className="font-mono font-semibold" style={monoStyle}>
                    {totalDpFiltered}
                  </span>
                  .
                </>
              ) : (
                segmentIdleCopy
              )}
            </p>
          </div>
        </div>
        <div className="flex flex-col justify-center rounded-xl border border-[#a4b4be]/15 bg-gradient-to-br from-white to-[#eef4fa] p-8">
          <span className="mb-4 text-[10px] font-bold uppercase tracking-widest text-[#6e7d86]">
            Factor total de disciplina
          </span>
          <div className="flex items-baseline gap-2">
            <span
              className="text-5xl font-black tracking-tight text-[#26343d]"
              style={monoStyle}
            >
              {factor.toFixed(1)}
            </span>
            <span className="text-sm font-bold uppercase text-[#6d3bd7]">
              {factorLabel}
            </span>
          </div>
          <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-[#ddeaf3]">
            <div
              className="h-full rounded-full bg-[#6d3bd7]"
              style={{ width: `${barPct}%` }}
            />
          </div>
          <p className="mt-3 text-xs text-[#52616a]">
            Basado en{' '}
            <span className="font-mono font-semibold" style={monoStyle}>
              {(disciplinePoints ?? 0).toLocaleString('es-CO')}
            </span>{' '}
            DP en perfil.
          </p>
        </div>
      </section>

      {detail ? (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center bg-[#0a0f12]/45 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ledger-detail-title"
        >
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-[#a4b4be]/30 bg-[#f6fafe] p-6 shadow-xl">
            <h2
              id="ledger-detail-title"
              className="text-lg font-bold text-[#26343d]"
            >
              Reflexión · {detail.pickId}
            </h2>
            <p className="mt-2 text-xs text-[#52616a]" style={monoStyle}>
              {new Date(detail.settledAt).toLocaleString('es-CO')}
            </p>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[#26343d]">
              {detail.reflection}
            </p>
            <button
              type="button"
              className="mt-6 rounded-lg border border-[#a4b4be]/40 px-4 py-2 text-sm font-semibold"
              onClick={() => setDetail(null)}
            >
              Cerrar
            </button>
          </div>
        </div>
      ) : null}

      {/* US-FE-021 (T-055): tour contextual */}
      <ViewTourModal
        open={tourOpen}
        title={LEDGER_TOUR.title}
        steps={LEDGER_TOUR.steps}
        onComplete={() => { setTourOpen(false); markTourSeen('ledger') }}
      />
    </div>
  )
}
