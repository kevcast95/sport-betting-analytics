import { useEffect, useRef, useState } from 'react'
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useMatch,
  useSearchParams,
} from 'react-router-dom'
import { DashboardChrome } from '@/components/DashboardChrome'
import BacktestsPage from '@/pages/BacktestsPage'
import ApiReadinessPage from '@/pages/ApiReadinessPage'
import AuthPage from '@/pages/AuthPage'
import DashboardPage from '@/pages/DashboardPage'
import PickDetailPage from '@/pages/PickDetailPage'
import RunEventsPage from '@/pages/RunEventsPage'
import RunPicksPage from '@/pages/RunPicksPage'
import RunsPage from '@/pages/RunsPage'
import SystemSettingsPage from '@/pages/SystemSettingsPage'
import {
  UiSportsVisibilityProvider,
  useUiSportsVisibility,
} from '@/contexts/UiSportsVisibilityContext'
import { SportUrlSync } from '@/components/SportUrlSync'
import { firstVisibleSport } from '@/lib/uiSportsVisibility'
import { fetchJson } from '@/lib/api'
import type { EffectivenessReportStatusOut } from '@/types/api'

function navClass(isActive: boolean) {
  return [
    'rounded-md px-3 py-2 text-sm transition-colors border-l-2',
    isActive
      ? 'border-violet-600 bg-violet-100/90 font-semibold text-violet-950'
      : 'border-transparent text-app-muted hover:border-violet-200 hover:bg-violet-50/60 hover:text-app-fg',
  ].join(' ')
}

function AppLayout() {
  const { visible: sportsVisible } = useUiSportsVisibility()
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

  const isV2Route = useMatch({ path: '/v2/*' }) != null

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  useEffect(() => {
    if (isV2Route) return
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
          new Notification('betTracker + · Reporte de efectividad', { body: msg })
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
  }, [isV2Route])

  const closeMenu = () => setMenuOpen(false)
  const isDashboardHome = useMatch({ path: '/', end: true })
  const [navSearch] = useSearchParams()
  const runsSportParam = navSearch.get('sport') === 'tennis' ? 'tennis' : 'football'
  const runsSportEffective = sportsVisible[runsSportParam]
    ? runsSportParam
    : firstVisibleSport(sportsVisible)
  const runsListHref =
    runsSportEffective === 'tennis' ? '/runs?sport=tennis' : '/runs'

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-app-bg text-app-fg">
      {!isV2Route && (
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
          betTracker +
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
      )}

      {!isV2Route && menuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/35 md:hidden"
          aria-label="Cerrar menú"
          onClick={closeMenu}
        />
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row">
        {!isV2Route && (
          <aside
            className={[
              'fixed inset-y-0 left-0 z-50 flex w-[min(18rem,88vw)] flex-col overflow-y-auto border-r border-app-line bg-app-card shadow-xl transition-transform duration-200 ease-out md:static md:z-0 md:h-full md:w-56 md:max-w-none md:shrink-0 md:shadow-none',
              menuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
            ].join(' ')}
          >
          <div className="flex items-center justify-between border-b border-app-line px-3 py-3 md:pt-4">
            <div className="px-2 text-xs font-semibold uppercase tracking-wide text-violet-900/80">
              betTracker +
            </div>
            <button
              type="button"
              className="rounded-md border border-app-line px-2 py-1 text-xs text-app-muted md:hidden"
              onClick={closeMenu}
            >
              Cerrar
            </button>
          </div>
          <div className="flex flex-1 flex-col px-3 pb-6">
            <nav className="flex flex-col gap-0.5 pt-3">
              <NavLink
                to="/"
                end
                className={({ isActive }) => navClass(isActive)}
                onClick={closeMenu}
              >
                Dashboard
              </NavLink>
              <NavLink
                to={runsListHref}
                title="Opcional: buscar un run por ID o fecha en tabla"
                className={({ isActive }) => navClass(isActive)}
                onClick={closeMenu}
              >
                Historial de runs
              </NavLink>
            </nav>
            <nav className="mt-auto border-t border-app-line pt-4">
              <NavLink
                to="/system-settings"
                className={({ isActive }) => navClass(isActive)}
                onClick={closeMenu}
              >
                Configuración
              </NavLink>
            </nav>
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
          </div>
          </aside>
        )}

        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {isDashboardHome && <DashboardChrome />}
          <main
            className={[
              'mx-auto min-h-0 flex-1 overflow-y-auto overscroll-contain',
              isV2Route
                ? 'max-w-none p-0 overflow-hidden bg-[#f6fafe]'
                : 'w-full max-w-5xl px-3 py-4 sm:px-4 md:px-8 md:py-8',
            ].join(' ')}
          >
            {!isV2Route && reportNotice && (
              <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-app-line bg-app-card px-3 py-2 text-xs text-app-fg">
                <span>{reportNotice}</span>
                <div className="flex items-center gap-2">
                  <Link
                    to="/api-readiness"
                    className="rounded border border-app-line px-2 py-1 text-[11px] text-app-muted hover:text-app-fg"
                  >
                    Ver reporte
                  </Link>
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
              <Route path="/v2" element={<Navigate to="/v2/session" replace />} />
              <Route path="/v2/session" element={<AuthPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/runs/:dailyRunId/picks" element={<RunPicksPage />} />
              <Route path="/runs/:dailyRunId/events" element={<RunEventsPage />} />
              <Route path="/picks/:pickId" element={<PickDetailPage />} />
              <Route path="/backtests" element={<BacktestsPage />} />
              <Route path="/api-readiness" element={<ApiReadinessPage />} />
              <Route path="/system-settings" element={<SystemSettingsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  )
}

function AppWithSportsProvider() {
  return (
    <>
      <SportUrlSync />
      <AppLayout />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <UiSportsVisibilityProvider>
        <AppWithSportsProvider />
      </UiSportsVisibilityProvider>
    </BrowserRouter>
  )
}
