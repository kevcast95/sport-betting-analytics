import { describe, expect, it } from 'vitest'
import {
  BT2_ENCRYPTED_WRAP_VERSION,
  createBt2EncryptedLocalStorage,
} from './bt2EncryptedStorage'

describe('createBt2EncryptedLocalStorage', () => {
  it('roundtrip: el texto persistido se recupera igual', () => {
    const storage = createBt2EncryptedLocalStorage()
    const payload =
      '{"state":{"isAuthenticated":true,"hasAcceptedContract":false},"version":0}'
    storage.setItem('t_roundtrip', payload)
    const raw = localStorage.getItem('t_roundtrip')
    expect(raw).toBeTruthy()
    const parsed = JSON.parse(raw!) as { v: number; d: string }
    expect(parsed.v).toBe(BT2_ENCRYPTED_WRAP_VERSION)
    expect(typeof parsed.d).toBe('string')
    expect(storage.getItem('t_roundtrip')).toBe(payload)
  })

  it('lee blobs legados Zustand sin envoltorio cifrado', () => {
    const storage = createBt2EncryptedLocalStorage()
    const legacy = '{"state":{"foo":1},"version":0}'
    localStorage.setItem('t_legacy', legacy)
    expect(storage.getItem('t_legacy')).toBe(legacy)
  })

  it('getItem devuelve null si el JSON no es reconocible', () => {
    const storage = createBt2EncryptedLocalStorage()
    localStorage.setItem('t_bad', '{"hello":"world"}')
    expect(storage.getItem('t_bad')).toBeNull()
  })

  it('removeItem elimina la clave', () => {
    const storage = createBt2EncryptedLocalStorage()
    storage.setItem('t_rm', '{}')
    expect(localStorage.getItem('t_rm')).toBeTruthy()
    storage.removeItem('t_rm')
    expect(localStorage.getItem('t_rm')).toBeNull()
  })
})
