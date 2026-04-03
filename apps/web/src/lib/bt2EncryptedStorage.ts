import type { StateStorage } from 'zustand/middleware'

/**
 * Capa de ofuscación para localStorage (POC US-FE-001).
 * XOR por bytes con clave derivada del origen; no sustituye secretos en servidor.
 * Se usa como backend de `createJSONStorage(() => createBt2EncryptedLocalStorage())`.
 */
function keyBytes(): Uint8Array {
  const base = 'bt2-v2-localstate-v1'
  const salt =
    typeof window !== 'undefined' ? window.location.origin : 'ssr'
  return new TextEncoder().encode(`${base}|${salt}`)
}

function xorBytes(data: Uint8Array, key: Uint8Array): Uint8Array {
  const out = new Uint8Array(data.length)
  for (let i = 0; i < data.length; i++) {
    out[i] = data[i] ^ key[i % key.length]
  }
  return out
}

function u8ToB64(u8: Uint8Array): string {
  let s = ''
  u8.forEach((b) => {
    s += String.fromCharCode(b)
  })
  return btoa(s)
}

function b64ToU8(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

const WRAP_VERSION = 1

function isLegacyZustandBlob(raw: string): boolean {
  try {
    const o = JSON.parse(raw) as Record<string, unknown>
    return o != null && typeof o === 'object' && 'state' in o && !('d' in o)
  } catch {
    return false
  }
}

/**
 * `StateStorage` compatible con `createJSONStorage`: getItem/setItem operan sobre el JSON
 * que persiste Zustand (`{ state, version }` serializado a string).
 */
export function createBt2EncryptedLocalStorage(): StateStorage {
  return {
    getItem(name) {
      if (typeof window === 'undefined') return null
      const raw = localStorage.getItem(name)
      if (raw == null) return null
      try {
        const o = JSON.parse(raw) as { v?: number; d?: string }
        if (o?.v === WRAP_VERSION && typeof o.d === 'string') {
          const clear = xorBytes(b64ToU8(o.d), keyBytes())
          return new TextDecoder().decode(clear)
        }
      } catch {
        /* legado o corrupto */
      }
      if (isLegacyZustandBlob(raw)) {
        return raw
      }
      return null
    },
    setItem(name, value) {
      if (typeof window === 'undefined') return
      const enc = xorBytes(new TextEncoder().encode(value), keyBytes())
      localStorage.setItem(
        name,
        JSON.stringify({ v: WRAP_VERSION, d: u8ToB64(enc) }),
      )
    },
    removeItem(name) {
      if (typeof window !== 'undefined') localStorage.removeItem(name)
    },
  }
}
