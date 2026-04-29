import type {
  Bt2AdminDsrDayOut,
  Bt2AdminDsrRangeOut,
  Bt2AdminBacktestReplayOut,
  Bt2AdminBacktestWindowSmRefreshOut,
  Bt2AdminF2PoolMetricsOut,
  Bt2AdminFase1OperationalSummaryOut,
  Bt2AdminMonitorResultadosOut,
  Bt2AdminMonitorShadowOut,
  Bt2AdminRefreshCdmFromSmOut,
  Bt2AdminVaultPickDistributionOut,
  Bt2AdminVaultRegenerateSnapshotOut,
  Bt2DpInsufficientPremiumDetail,
  Bt2PickOut,
  Bt2PickRegisterBody,
  Bt2VaultPickCommitmentBody,
  Bt2VaultPickCommitmentOut,
  Bt2VaultPremiumUnlockBody,
  Bt2VaultPremiumUnlockOut,
  Bt2VaultPicksPageOut,
  Bt2VaultStandardUnlockBody,
  Bt2VaultStandardUnlockOut,
} from '@/lib/bt2Types'

// ─── JWT helpers ─────────────────────────────────────────────────────────────

const JWT_KEY = 'bt2_jwt'

export function getStoredJwt(): string | null {
  try {
    return localStorage.getItem(JWT_KEY)
  } catch {
    return null
  }
}

export function setStoredJwt(token: string): void {
  try {
    localStorage.setItem(JWT_KEY, token)
  } catch { /* noop */ }
}

export function clearStoredJwt(): void {
  try {
    localStorage.removeItem(JWT_KEY)
  } catch { /* noop */ }
}

// ─── Core fetch ───────────────────────────────────────────────────────────────

export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')
  if (base) return `${base}${p}`
  return `/api${p}`
}

function defaultHeaders(): HeadersInit {
  const h: Record<string, string> = { Accept: 'application/json' }
  const key = import.meta.env.VITE_WEB_API_KEY
  if (key) h['X-Local-Api-Key'] = key
  return h
}

export async function fetchJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = apiUrl(path)
  const headers = new Headers(defaultHeaders())
  if (init?.headers) {
    const extra = new Headers(init.headers)
    extra.forEach((v, k) => headers.set(k, v))
  }
  let res: Response
  try {
    res = await fetch(url, { ...init, headers })
  } catch (e) {
    const hint =
      import.meta.env.VITE_API_BASE_URL &&
      import.meta.env.VITE_API_BASE_URL.length > 0
        ? ' Tienes VITE_API_BASE_URL: el navegador llama directo al puerto 8000 (CORS/red). Comenta esa variable en apps/web/.env para usar el proxy /api de Vite (mismo origen).'
        : ' ¿Está corriendo uvicorn en 127.0.0.1:8000?'
    if (e instanceof TypeError) {
      throw new Error(`Sin conexión al API (${url}).${hint}`)
    }
    throw e
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text.slice(0, 200)}` : ''}`)
  }
  return res.json() as Promise<T>
}

// ─── Authenticated fetch (Sprint 04 US-FE-026) ────────────────────────────────

/**
 * Wrapper de `fetchJson` que añade `Authorization: Bearer <jwt>` automáticamente.
 * Lanza error con prefijo "401 " para que las capas superiores puedan detectar
 * sesión expirada y disparar el flujo de re-login.
 */
export async function bt2FetchJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const token = getStoredJwt()
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  const mergedHeaders: Record<string, string> = {
    ...authHeader,
    ...(init?.headers ? Object.fromEntries(new Headers(init.headers).entries()) : {}),
  }

  try {
    return await fetchJson<T>(path, { ...init, headers: mergedHeaders })
  } catch (e) {
    const err = e as Error
    if (err.message.startsWith('401 ')) {
      clearStoredJwt()
    }
    throw err
  }
}

export type Bt2UserResultClaim = 'pending' | 'won' | 'lost' | 'void'

/** POST — revierte liquidación formal; pick vuelve a `open` (bankroll + DP). */
export async function bt2PostReopenPickSettlement(pickId: number): Promise<Bt2PickOut> {
  return bt2FetchJson<Bt2PickOut>(`/bt2/picks/${pickId}/reopen-settlement`, {
    method: 'POST',
  })
}

/** PATCH — criterio declarativo del operador (p. ej. consulta externa); no sustituye liquidación formal. */
export async function bt2PatchUserResultClaim(
  pickId: number,
  claim: Bt2UserResultClaim | null,
): Promise<Bt2PickOut> {
  return bt2FetchJson<Bt2PickOut>(`/bt2/picks/${pickId}/user-result-claim`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim }),
  })
}

/**
 * POST /bt2/vault/regenerate-slate — recomponer snapshot en servidor (ops/admin).
 * La **Bóveda** no usa esto: un solo GET trae el pool del día y «Regenerar cartelera» solo baraja en cliente.
 */
export async function bt2PostVaultRegenerateSlate(): Promise<Bt2VaultPicksPageOut> {
  return bt2FetchJson<Bt2VaultPicksPageOut>('/bt2/vault/regenerate-slate', { method: 'POST' })
}

// ─── Sprint 05 — POST /bt2/picks (402 detail estructurado, D-05-005) ───────────

export function parseBt2DpInsufficientPremiumDetail(
  detail: unknown,
): Bt2DpInsufficientPremiumDetail | null {
  if (!detail || typeof detail !== 'object') return null
  const o = detail as Record<string, unknown>
  if (o.code !== 'dp_insufficient_for_premium_unlock') return null
  return {
    code: 'dp_insufficient_for_premium_unlock',
    message: String(o.message ?? ''),
    requiredDp: Number(o.requiredDp ?? 50),
    currentDp: Number(o.currentDp ?? 0),
  }
}

export type Bt2PostPickRegisterResult =
  | { ok: true; data: Bt2PickOut }
  | {
      ok: false
      status: number
      bodyText: string
      /** Solo si status === 402 y el cuerpo coincide con D-05-005 */
      premiumInsufficient: Bt2DpInsufficientPremiumDetail | null
      message: string
      /** 422 con `detail.code` (p. ej. pick_event_kickoff_elapsed — Sprint 05.2). */
      errorCode?: string
    }

/**
 * POST /bt2/picks con manejo explícito de 402 (saldo insuficiente desbloqueo premium).
 * No usar bt2FetchJson aquí: necesitamos el cuerpo JSON en errores.
 */
export async function bt2PostPickRegister(
  body: Bt2PickRegisterBody,
): Promise<Bt2PostPickRegisterResult> {
  const token = getStoredJwt()
  const url = apiUrl('/bt2/picks')
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const key = import.meta.env.VITE_WEB_API_KEY
  if (key) headers['X-Local-Api-Key'] = key

  let res: Response
  try {
    res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })
  } catch (e) {
    const hint =
      import.meta.env.VITE_API_BASE_URL &&
      import.meta.env.VITE_API_BASE_URL.length > 0
        ? ' Revisa CORS / VITE_API_BASE_URL.'
        : ' ¿Está corriendo uvicorn en 127.0.0.1:8000?'
    if (e instanceof TypeError) {
      return {
        ok: false,
        status: 0,
        bodyText: '',
        premiumInsufficient: null,
        message: `Sin conexión al API.${hint}`,
      }
    }
    throw e
  }

  const text = await res.text()
  let json: unknown
  try {
    json = text ? JSON.parse(text) : null
  } catch {
    json = null
  }

  if (res.ok && json && typeof json === 'object') {
    return { ok: true, data: json as Bt2PickOut }
  }

  if (res.status === 401) {
    clearStoredJwt()
  }

  let premiumInsufficient: Bt2DpInsufficientPremiumDetail | null = null
  let message = text ? text.slice(0, 280) : `${res.status} ${res.statusText}`
  let errorCode: string | undefined
  if (res.status === 402 && json && typeof json === 'object') {
    const raw = (json as { detail?: unknown }).detail
    premiumInsufficient = parseBt2DpInsufficientPremiumDetail(raw)
    if (premiumInsufficient?.message) message = premiumInsufficient.message
  }
  if (res.status === 422 && json && typeof json === 'object') {
    const raw = (json as { detail?: unknown }).detail
    if (raw && typeof raw === 'object' && raw !== null && 'code' in raw) {
      const o = raw as { code?: string; message?: string }
      if (typeof o.code === 'string') errorCode = o.code
      if (typeof o.message === 'string' && o.message) message = o.message
    } else if (typeof raw === 'string') {
      message = raw.slice(0, 280)
    }
  }

  return {
    ok: false,
    status: res.status,
    bodyText: text,
    premiumInsufficient,
    message,
    errorCode,
  }
}

export type Bt2PostVaultPremiumUnlockResult =
  | { ok: true; data: Bt2VaultPremiumUnlockOut }
  | {
      ok: false
      status: number
      premiumInsufficient: Bt2DpInsufficientPremiumDetail | null
      message: string
    }

/**
 * POST /bt2/vault/premium-unlock (US-BE-029 / Sprint 05.1).
 * Cobra DP sin crear bt2_picks; maneja 402 con detalle estructurado.
 */
export async function bt2PostVaultPremiumUnlock(
  body: Bt2VaultPremiumUnlockBody,
): Promise<Bt2PostVaultPremiumUnlockResult> {
  const token = getStoredJwt()
  const url = apiUrl('/bt2/vault/premium-unlock')
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const key = import.meta.env.VITE_WEB_API_KEY
  if (key) headers['X-Local-Api-Key'] = key

  let res: Response
  try {
    res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })
  } catch (e) {
    const hint =
      import.meta.env.VITE_API_BASE_URL &&
      import.meta.env.VITE_API_BASE_URL.length > 0
        ? ' Revisa CORS / VITE_API_BASE_URL.'
        : ' ¿Está corriendo uvicorn en 127.0.0.1:8000?'
    if (e instanceof TypeError) {
      return {
        ok: false,
        status: 0,
        premiumInsufficient: null,
        message: `Sin conexión al API.${hint}`,
      }
    }
    throw e
  }

  const text = await res.text()
  let json: unknown
  try {
    json = text ? JSON.parse(text) : null
  } catch {
    json = null
  }

  if (res.ok && json && typeof json === 'object') {
    return { ok: true, data: json as Bt2VaultPremiumUnlockOut }
  }

  if (res.status === 401) {
    clearStoredJwt()
  }

  let premiumInsufficient: Bt2DpInsufficientPremiumDetail | null = null
  let message = text ? text.slice(0, 280) : `${res.status} ${res.statusText}`
  if (res.status === 402 && json && typeof json === 'object') {
    const raw = (json as { detail?: unknown }).detail
    premiumInsufficient = parseBt2DpInsufficientPremiumDetail(raw)
    if (premiumInsufficient?.message) message = premiumInsufficient.message
  }

  return {
    ok: false,
    status: res.status,
    premiumInsufficient,
    message,
  }
}

export type Bt2PostVaultStandardUnlockResult =
  | { ok: true; data: Bt2VaultStandardUnlockOut }
  | { ok: false; status: number; message: string }

/** Extrae `detail` legible del JSON que adjunta fetchJson en el Error (422/401). */
function parseBt2FetchErrorPayload(fullMessage: string): string {
  const sep = ': '
  const idx = fullMessage.indexOf(sep)
  if (idx === -1) return fullMessage.slice(0, 420)
  const maybeJson = fullMessage.slice(idx + sep.length).trim()
  try {
    const j = JSON.parse(maybeJson) as { detail?: unknown }
    const d = j.detail
    if (typeof d === 'string') return d.slice(0, 420)
    if (Array.isArray(d) && d.length > 0) {
      const row = d[0] as { msg?: string }
      if (row.msg) return row.msg.slice(0, 420)
    }
    if (d && typeof d === 'object' && d !== null && 'message' in d) {
      return String((d as { message: unknown }).message).slice(0, 420)
    }
  } catch {
    /* cuerpo no JSON */
  }
  return fullMessage.slice(0, 420)
}

/** POST /bt2/vault/standard-unlock — liberar ítem estándar sin DP (topes en servidor). */
export async function bt2PostVaultStandardUnlock(
  body: Bt2VaultStandardUnlockBody,
): Promise<Bt2PostVaultStandardUnlockResult> {
  try {
    const data = await bt2FetchJson<Bt2VaultStandardUnlockOut>(
      '/bt2/vault/standard-unlock',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vaultPickId: body.vaultPickId }),
      },
    )
    return { ok: true, data }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    const m = msg.match(/^(\d{3})\s/)
    const status = m ? parseInt(m[1], 10) : 0
    return { ok: false, status, message: parseBt2FetchErrorPayload(msg) }
  }
}

/** POST /bt2/vault/pick-commitment — tomó / no tomó (tras liberar). */
export async function bt2PostVaultPickCommitment(
  body: Bt2VaultPickCommitmentBody,
): Promise<Bt2VaultPickCommitmentOut> {
  return bt2FetchJson<Bt2VaultPickCommitmentOut>('/bt2/vault/pick-commitment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vaultPickId: body.vaultPickId,
      commitment: body.commitment,
    }),
  })
}

/**
 * GET /bt2/admin/analytics/dsr-day (US-BE-028).
 * Requiere `VITE_BT2_ADMIN_API_KEY` alineada con `BT2_ADMIN_API_KEY` del API.
 */
export async function fetchBt2AdminDsrDay(
  operatingDayKey: string,
): Promise<Bt2AdminDsrDayOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams({ operatingDayKey })
  return fetchJson<Bt2AdminDsrDayOut>(
    `/bt2/admin/analytics/dsr-day?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * GET /bt2/admin/analytics/dsr-range — KPIs por día + totales (histórico).
 */
export async function fetchBt2AdminDsrRange(
  fromOperatingDayKey: string,
  toOperatingDayKey: string,
): Promise<Bt2AdminDsrRangeOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams({
    fromOperatingDayKey: fromOperatingDayKey.trim(),
    toOperatingDayKey: toOperatingDayKey.trim(),
  })
  return fetchJson<Bt2AdminDsrRangeOut>(
    `/bt2/admin/analytics/dsr-range?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * GET /bt2/admin/analytics/vault-pick-distribution (US-BE-035 / T-183).
 * Agregados por etiqueta de confianza, fuente y buckets de score CDM — distintos semánticamente.
 */
export async function fetchBt2AdminVaultPickDistribution(
  operatingDayKey: string,
): Promise<Bt2AdminVaultPickDistributionOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams({ operatingDayKey })
  return fetchJson<Bt2AdminVaultPickDistributionOut>(
    `/bt2/admin/analytics/vault-pick-distribution?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * POST /bt2/admin/vault/regenerate-daily-snapshot — borra y regenera snapshot bóveda (usuario + día).
 * Header `X-BT2-Admin-Key` = `BT2_ADMIN_API_KEY`. No usa JWT de usuario.
 */
/**
 * GET /bt2/admin/analytics/fase1-operational-summary (US-BE-052 / US-FE-061).
 * Verdad oficial CDM + elegibilidad pool + buckets mercado/confianza.
 */
/**
 * GET /bt2/admin/analytics/monitor-resultados — bóveda vs evaluación oficial.
 */
export async function fetchBt2AdminMonitorResultados(
  operatingDayKeyFrom: string,
  operatingDayKeyTo: string,
  options?: {
    monitorUserId?: string | null
    /** Refresca marcadores desde SportMonks y re-evalúa pendientes (cuota API). */
    syncFromSportmonks?: boolean
    /**
     * Con syncFromSportmonks: si true (default), solo GET SM para eventos con pick pending_result.
     * Pon false para el modo anterior (todos los eventos con pick hasta el límite).
     */
    smSyncPendingOnly?: boolean
    smSyncEventLimit?: number
    rowsOffset?: number
    rowsLimit?: number
    outcomeFilter?: string
    marketSubstring?: string
    search?: string
  },
): Promise<Bt2AdminMonitorResultadosOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams()
  qs.set('operatingDayKeyFrom', operatingDayKeyFrom.trim())
  qs.set('operatingDayKeyTo', operatingDayKeyTo.trim())
  const uid = options?.monitorUserId?.trim()
  if (uid) qs.set('monitorUserId', uid)
  if (options?.syncFromSportmonks) qs.set('syncFromSportmonks', 'true')
  if (options?.smSyncPendingOnly === false) {
    qs.set('smSyncPendingOnly', 'false')
  }
  if (options?.smSyncEventLimit != null) {
    qs.set('smSyncEventLimit', String(options.smSyncEventLimit))
  }
  if (options?.rowsOffset != null) qs.set('rowsOffset', String(options.rowsOffset))
  if (options?.rowsLimit != null) qs.set('rowsLimit', String(options.rowsLimit))
  const of = options?.outcomeFilter?.trim()
  if (of && of !== 'all') qs.set('outcomeFilter', of)
  const mk = options?.marketSubstring?.trim()
  if (mk) qs.set('marketSubstring', mk)
  const sq = options?.search?.trim()
  if (sq) qs.set('search', sq)
  return fetchJson<Bt2AdminMonitorResultadosOut>(
    `/bt2/admin/analytics/monitor-resultados?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * GET /bt2/admin/analytics/monitor-resultados-shadow — lane shadow subset5.
 */
export async function fetchBt2AdminMonitorResultadosShadow(
  operatingDayKeyFrom: string,
  operatingDayKeyTo: string,
  options?: {
    rowsOffset?: number
    rowsLimit?: number
    marketSubstring?: string
    search?: string
    classificationFilter?: string
    runKind?: string
    runKey?: string
    groupByRun?: boolean
  },
): Promise<Bt2AdminMonitorShadowOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams()
  qs.set('operatingDayKeyFrom', operatingDayKeyFrom.trim())
  qs.set('operatingDayKeyTo', operatingDayKeyTo.trim())
  if (options?.rowsOffset != null) qs.set('rowsOffset', String(options.rowsOffset))
  if (options?.rowsLimit != null) qs.set('rowsLimit', String(options.rowsLimit))
  const mk = options?.marketSubstring?.trim()
  if (mk) qs.set('marketSubstring', mk)
  const sq = options?.search?.trim()
  if (sq) qs.set('search', sq)
  const cf = options?.classificationFilter?.trim()
  if (cf && cf !== 'all') qs.set('classificationFilter', cf)
  const rk = options?.runKey?.trim()
  if (rk) qs.set('runKey', rk)
  const rkind = options?.runKind?.trim()
  if (rkind) qs.set('runKind', rkind)
  if (options?.groupByRun) qs.set('groupByRun', 'true')
  return fetchJson<Bt2AdminMonitorShadowOut>(
    `/bt2/admin/analytics/monitor-resultados-shadow?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * GET /bt2/admin/analytics/backtest-replay — replay ciego del pipeline DSR sobre Postgres.
 */
export async function fetchBt2AdminBacktestReplay(
  operatingDayKeyFrom: string,
  operatingDayKeyTo: string,
  options?: { maxEventsPerDay?: number },
): Promise<Bt2AdminBacktestReplayOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams()
  qs.set('operatingDayKeyFrom', operatingDayKeyFrom.trim())
  qs.set('operatingDayKeyTo', operatingDayKeyTo.trim())
  if (options?.maxEventsPerDay != null) {
    qs.set('maxEventsPerDay', String(options.maxEventsPerDay))
  }
  return fetchJson<Bt2AdminBacktestReplayOut>(
    `/bt2/admin/analytics/backtest-replay?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * POST /bt2/admin/operations/refresh-cdm-sm-for-backtest-window — SM → CDM solo para el pool
 * candidato del backtest (independiente del GET replay).
 */
export async function postBt2AdminRefreshCdmSmForBacktestWindow(
  operatingDayKeyFrom: string,
  operatingDayKeyTo: string,
  options?: { maxEventsPerDay?: number; onlyPendingCdm?: boolean },
): Promise<Bt2AdminBacktestWindowSmRefreshOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams({
    operatingDayKeyFrom: operatingDayKeyFrom.trim(),
    operatingDayKeyTo: operatingDayKeyTo.trim(),
  })
  if (options?.maxEventsPerDay != null) {
    qs.set('maxEventsPerDay', String(options.maxEventsPerDay))
  }
  if (options?.onlyPendingCdm === false) {
    qs.set('onlyPendingCdm', 'false')
  }
  return fetchJson<Bt2AdminBacktestWindowSmRefreshOut>(
    `/bt2/admin/operations/refresh-cdm-sm-for-backtest-window?${qs.toString()}`,
    { method: 'POST', headers: { 'X-BT2-Admin-Key': key } },
  )
}

export async function fetchBt2AdminFase1OperationalSummary(
  operatingDayKey: string,
  options?: { accumulated?: boolean },
): Promise<Bt2AdminFase1OperationalSummaryOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams()
  if (options?.accumulated) {
    qs.set('accumulated', 'true')
  } else {
    qs.set('operatingDayKey', operatingDayKey.trim())
  }
  return fetchJson<Bt2AdminFase1OperationalSummaryOut>(
    `/bt2/admin/analytics/fase1-operational-summary?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * GET /bt2/admin/analytics/f2-pool-eligibility-metrics (T-263).
 * Un día (`operatingDayKey`) o ventana rolling (`days`, default 30) si no se pasa día.
 */
export async function fetchBt2AdminF2PoolEligibilityMetrics(options: {
  operatingDayKey?: string
  days?: number
}): Promise<Bt2AdminF2PoolMetricsOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams()
  if (options.operatingDayKey?.trim()) {
    qs.set('operatingDayKey', options.operatingDayKey.trim())
  }
  if (options.days != null) {
    qs.set('days', String(options.days))
  }
  return fetchJson<Bt2AdminF2PoolMetricsOut>(
    `/bt2/admin/analytics/f2-pool-eligibility-metrics?${qs.toString()}`,
    { headers: { 'X-BT2-Admin-Key': key } },
  )
}

/**
 * POST /bt2/admin/operations/refresh-cdm-from-sm-for-operating-day — SM vivo → raw → CDM + eval oficial.
 */
export async function postBt2AdminRefreshCdmFromSm(
  operatingDayKey: string,
  options?: {
    limit?: number
    runOfficialEvaluation?: boolean
    onlyPendingOfficialEvaluation?: boolean
  },
): Promise<Bt2AdminRefreshCdmFromSmOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams({ operatingDayKey: operatingDayKey.trim() })
  if (options?.limit != null) qs.set('limit', String(options.limit))
  if (options?.runOfficialEvaluation === false) qs.set('runOfficialEvaluation', 'false')
  if (options?.onlyPendingOfficialEvaluation === false) {
    qs.set('onlyPendingOfficialEvaluation', 'false')
  }
  return fetchJson<Bt2AdminRefreshCdmFromSmOut>(
    `/bt2/admin/operations/refresh-cdm-from-sm-for-operating-day?${qs.toString()}`,
    { method: 'POST', headers: { 'X-BT2-Admin-Key': key } },
  )
}

export async function postBt2AdminVaultRegenerateSnapshot(
  userId: string,
  operatingDayKey: string,
): Promise<Bt2AdminVaultRegenerateSnapshotOut> {
  const key = (import.meta.env.VITE_BT2_ADMIN_API_KEY ?? '').trim()
  if (!key) {
    throw new Error(
      'Falta VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
    )
  }
  const qs = new URLSearchParams({
    userId: userId.trim(),
    operatingDayKey: operatingDayKey.trim(),
  })
  return fetchJson<Bt2AdminVaultRegenerateSnapshotOut>(
    `/bt2/admin/vault/regenerate-daily-snapshot?${qs.toString()}`,
    {
      method: 'POST',
      headers: { 'X-BT2-Admin-Key': key },
    },
  )
}
