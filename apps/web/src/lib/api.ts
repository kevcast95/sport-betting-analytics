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
