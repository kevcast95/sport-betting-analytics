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

function apiUrl(path: string): string {
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
