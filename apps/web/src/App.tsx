import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import BacktestsPage from '@/pages/BacktestsPage'
import DashboardPage from '@/pages/DashboardPage'
import PickDetailPage from '@/pages/PickDetailPage'
import RunPicksPage from '@/pages/RunPicksPage'
import RunsPage from '@/pages/RunsPage'

function navClass(isActive: boolean) {
  return [
    'rounded-md px-3 py-2 text-sm transition-colors',
    isActive
      ? 'bg-neutral-100 font-medium text-app-fg'
      : 'text-app-muted hover:bg-neutral-50 hover:text-app-fg',
  ].join(' ')
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-dvh bg-app-bg text-app-fg">
        <aside className="sticky top-0 flex h-dvh w-52 shrink-0 flex-col border-r border-app-line bg-app-card px-3 py-6 md:w-56">
          <div className="mb-8 px-2 text-xs font-semibold uppercase tracking-wide text-app-muted">
            Menú
          </div>
          <nav className="flex flex-col gap-0.5">
            <NavLink to="/" end className={({ isActive }) => navClass(isActive)}>
              Dashboard
            </NavLink>
            <NavLink
              to="/runs"
              className={({ isActive }) => navClass(isActive)}
            >
              Picks por run
            </NavLink>
            <NavLink
              to="/backtests"
              className={({ isActive }) => navClass(isActive)}
            >
              Backtests
            </NavLink>
          </nav>
        </aside>
        <div className="min-w-0 flex-1 overflow-y-auto">
          <main className="mx-auto max-w-5xl px-4 py-8 md:px-8">
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
    </BrowserRouter>
  )
}
