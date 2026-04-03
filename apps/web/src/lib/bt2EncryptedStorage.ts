import type { StateStorage } from 'zustand/middleware'

export const BT2_ENCRYPTED_WRAP_VERSION = 1 as const

export type Bt2EncryptedEnvelope = {
  v: typeof BT2_ENCRYPTED_WRAP_VERSION
  d: string
}

/** Formato legado: JSON que `createJSONStorage` guardaba en bruto en localStorage */
export type ZustandPersistJsonBlob = {
  state: unknown
  version?: number
}

function isEncryptedEnvelope(value: unknown): value is Bt2EncryptedEnvelope {
  if (value == null || typeof value !== 'object') return false
  const o = value as Record<string, unknown>
  return (
    o.v === BT2_ENCRYPTED_WRAP_VERSION &&
    typeof o.d === 'string' &&
    !('state' in o)
  )
}

function isLegacyZustandJson(value: unknown): value is ZustandPersistJsonBlob {
  if (value == null || typeof value !== 'object') return false
  const o = value as Record<string, unknown>
  return 'state' in o && !('d' in o)
}

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

function parseStoredRaw(raw: string): unknown {
  return JSON.parse(raw) as unknown
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
        const parsed = parseStoredRaw(raw)
        if (isEncryptedEnvelope(parsed)) {
          const clear = xorBytes(b64ToU8(parsed.d), keyBytes())
          return new TextDecoder().decode(clear)
        }
      } catch {
        /* JSON inválido o corrupto */
      }
      try {
        const parsed = parseStoredRaw(raw)
        if (isLegacyZustandJson(parsed)) {
          return raw
        }
      } catch {
        /* vacío */
      }
      return null
    },
    setItem(name, value) {
      if (typeof window === 'undefined') return
      const enc = xorBytes(new TextEncoder().encode(value), keyBytes())
      const payload: Bt2EncryptedEnvelope = {
        v: BT2_ENCRYPTED_WRAP_VERSION,
        d: u8ToB64(enc),
      }
      localStorage.setItem(name, JSON.stringify(payload))
    },
    removeItem(name) {
      if (typeof window !== 'undefined') localStorage.removeItem(name)
    },
  }
}
