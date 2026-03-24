import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import BacktestsPage from '@/pages/BacktestsPage'
import DashboardPage from '@/pages/DashboardPage'
import PickDetailPage from '@/pages/PickDetailPage'
import RunPicksPage from '@/pages/RunPicksPage'
import RunsPage from '@/pages/RunsPage'
import { fetchJson } from '@/lib/api'
import { useBankrollCOP } from '@/hooks/useBankrollCOP'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import type { EffectivenessReportStatusOut } from '@/types/api'

function navClass(isActive: boolean) {
  return [
    'rounded-md px-3 py-2 text-sm transition-colors border-l-2',
    isActive
      ? 'border-violet-600 bg-violet-100/90 font-semibold text-violet-950'
      : 'border-transparent text-app-muted hover:border-violet-200 hover:bg-violet-50/60 hover:text-app-fg',
  ].join(' ')
}

function BankrollSidebar() {
  const { userId } = useTrackingUser()
  const { bankrollCOP, setBankrollCOP } = useBankrollCOP(userId)
  const [draft, setDraft] = useState(() =>
    bankrollCOP != null ? String(Math.round(bankrollCOP)) : '',
  )

  useEffect(() => {
    setDraft(bankrollCOP != null ? String(Math.round(bankrollCOP)) : '')
  }, [bankrollCOP])

  return (
    <div className="mt-6 border-t border-app-line px-2 pt-5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
        Bankroll (COP)
      </p>
      {userId == null ? (
        <p className="mt-2 text-[10px] leading-relaxed text-app-muted">
          Elige un usuario en el dashboard o en un run; el bankroll se guarda
          en el servidor por usuario.
        </p>
      ) : (
        <>
          <p className="mt-1 text-[10px] leading-relaxed text-app-muted">
            Usuario <span className="font-mono">{userId}</span> · se guarda en el
            servidor con tu cuenta local.
          </p>
          <input
            type="text"
            inputMode="numeric"
            placeholder="Ej. 500000"
            className="mt-2 w-full rounded-md border border-violet-200 bg-white px-2 py-2 font-mono text-xs text-app-fg tabular-nums shadow-sm"
            value={draft}
            onChange={(e) => setDraft(e.target.value.replace(/[^\d]/g, ''))}
            onBlur={() => {
              const raw = draft.trim()
              if (raw === '') {
                setBankrollCOP(null)
                return
              }
              const n = Number.parseInt(raw, 10)
              if (!Number.isNaN(n) && n >= 0) setBankrollCOP(n)
            }}
          />
          {bankrollCOP != null && bankrollCOP > 0 && (
            <p className="mt-1.5 font-mono text-[10px] tabular-nums text-violet-800">
              {new Intl.NumberFormat('es-CO', {
                style: 'currency',
                currency: 'COP',
                maximumFractionDigits: 0,
              }).format(bankrollCOP)}
            </p>
          )}
        </>
      )}
    </div>
  )
}

function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [reportNotice, setReportNotice] = useState<string | null>(null)
  const [notificationPermission, setNotificationPermission] = useState<
    NotificationPermission | 'unsupported'
  >(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return 'unsupported'
    }
    return Notification.permission
  })
  const latestReportSeenRef = useRef<string | null>(null)

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const st = await fetchJson<EffectivenessReportStatusOut>(
          '/reports/effectiveness/latest-status',
        )
        if (!st.available || !st.generated_at_utc) return
        const lastSeen = latestReportSeenRef.current
        if (lastSeen == null) {
          latestReportSeenRef.current = st.generated_at_utc
          return
        }
        if (lastSeen === st.generated_at_utc) return
        latestReportSeenRef.current = st.generated_at_utc
        const msg = `Reporte listo (${st.range_start ?? '?'} → ${st.range_end ?? '?'})`
        if (!cancelled) setReportNotice(msg)
        if (
          typeof window !== 'undefined' &&
          'Notification' in window &&
          Notification.permission === 'granted'
        ) {
          new Notification('ALTEA · Reporte de efectividad', { body: msg })
        }
      } catch {
        // Silencioso: no interrumpir UI si el API está reiniciando.
      }
    }

    void poll()
    const id = window.setInterval(() => void poll(), 60_000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="flex min-h-dvh flex-col bg-app-bg text-app-fg">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between gap-2 border-b border-app-line bg-app-card/95 px-3 py-3 backdrop-blur-sm md:hidden">
        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-app-line bg-white text-app-fg shadow-sm"
          aria-expanded={menuOpen}
          aria-label="Abrir menú"
          onClick={() => setMenuOpen(true)}
        >
          <span className="flex flex-col gap-1">
            <span className="block h-0.5 w-5 rounded-full bg-app-fg" />
            <span className="block h-0.5 w-5 rounded-full bg-app-fg" />
            <span className="block h-0.5 w-5 rounded-full bg-app-fg" />
          </span>
        </button>
        <span className="truncate text-sm font-semibold text-violet-900">
          Panel
        </span>
        {notificationPermission === 'default' ? (
          <button
            type="button"
            className="rounded border border-app-line px-2 py-1 text-[11px] text-app-muted"
            onClick={async () => {
              if (!('Notification' in window)) return
              const p = await Notification.requestPermission()
              setNotificationPermission(p)
            }}
          >
            Push
          </button>
        ) : (
          <span className="w-10 shrink-0" aria-hidden />
        )}
      </header>

      {menuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/35 md:hidden"
          aria-label="Cerrar menú"
          onClick={closeMenu}
        />
      )}

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside
          className={[
            'fixed inset-y-0 left-0 z-50 flex w-[min(18rem,88vw)] flex-col overflow-y-auto border-r border-app-line bg-app-card shadow-xl transition-transform duration-200 ease-out md:static md:z-0 md:w-56 md:max-w-none md:shadow-none',
            menuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
          ].join(' ')}
        >
          <div className="flex items-center justify-between px-3 py-4 md:py-6">
            <div className="px-2 text-xs font-semibold uppercase tracking-wide text-violet-900/80">
              Menú
            </div>
            <button
              type="button"
              className="rounded-md border border-app-line px-2 py-1 text-xs text-app-muted md:hidden"
              onClick={closeMenu}
            >
              Cerrar
            </button>
          </div>
          <nav className="flex flex-col gap-0.5 px-3">
            <NavLink
              to="/"
              end
              className={({ isActive }) => navClass(isActive)}
              onClick={closeMenu}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/runs"
              className={({ isActive }) => navClass(isActive)}
              onClick={closeMenu}
            >
              Picks por run
            </NavLink>
            <NavLink
              to="/backtests"
              className={({ isActive }) => navClass(isActive)}
              onClick={closeMenu}
            >
              Backtests
            </NavLink>
          </nav>
          <div className="px-3 pb-6">
            {notificationPermission === 'default' && (
              <div className="mb-3 rounded-md border border-app-line bg-app-card px-2 py-2">
                <p className="text-[10px] text-app-muted">
                  Alertas web
                </p>
                <button
                  type="button"
                  className="mt-1 w-full rounded border border-app-line px-2 py-1 text-[11px] text-app-fg hover:bg-violet-50/40"
                  onClick={async () => {
                    if (!('Notification' in window)) return
                    const p = await Notification.requestPermission()
                    setNotificationPermission(p)
                  }}
                >
                  Activar push notification
                </button>
              </div>
            )}
            <BankrollSidebar />
          </div>
        </aside>

        <div className="min-w-0 flex-1 md:overflow-y-auto">
          <main className="mx-auto max-w-5xl px-3 py-4 sm:px-4 md:px-8 md:py-8">
            {reportNotice && (
              <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-app-line bg-app-card px-3 py-2 text-xs text-app-fg">
                <span>{reportNotice}</span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="rounded border border-app-line px-2 py-1 text-[11px] text-app-muted hover:text-app-fg"
                    onClick={() => setReportNotice(null)}
                  >
                    Cerrar
                  </button>
                </div>
              </div>
            )}
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/runs/:dailyRunId/picks" element={<RunPicksPage />} />
              <Route path="/picks/:pickId" element={<PickDetailPage />} />
              <Route path="/backtests" element={<BacktestsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
