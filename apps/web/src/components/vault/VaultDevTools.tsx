/**
 * Solo `import.meta.env.DEV`: atajos para probar bóveda / DSR sin curl.
 * El reset completo requiere BT2_DEV_OPERATING_DAY_RESET=1 en el API (.env raíz).
 */
import { useState } from 'react'
import { bt2FetchJson, getStoredJwt } from '@/lib/api'
import { useSessionStore } from '@/store/useSessionStore'
import { useVaultStore } from '@/store/useVaultStore'

type DevResetOut = {
  operatingDayKey?: string
  dailyPicksDeleted?: number
  serverSessionClosed?: boolean
  smFixturesRefreshed?: number
  smRefreshLog?: string[]
  messageEs?: string
}

function invalidateVaultClientCache() {
  useVaultStore.setState({
    apiPicks: [],
    picksLoadStatus: 'idle',
    picksMessage: null,
    vaultSnapshotOperatingDayKey: null,
    vaultPoolMeta: null,
    vaultDaySnapshotMeta: null,
    sessionOpenStatus: 'idle',
  })
}

export function VaultDevTools() {
  const [busy, setBusy] = useState(false)
  const [lastMsg, setLastMsg] = useState<string | null>(null)

  const onResetDay = async () => {
    if (!getStoredJwt()) {
      setLastMsg('Iniciá sesión BT2 primero.')
      return
    }
    setBusy(true)
    setLastMsg(null)
    try {
      const out = await bt2FetchJson<DevResetOut>(
        '/bt2/dev/reset-operating-day-for-tests',
        { method: 'POST' },
      )
      invalidateVaultClientCache()
      await useSessionStore.getState().hydrateFromApi()
      await useVaultStore.getState().loadApiPicks()
      const log =
        out.smRefreshLog && out.smRefreshLog.length > 0
          ? ` · SM: ${out.smRefreshLog.slice(0, 6).join(' | ')}`
          : ''
      setLastMsg(
        out.messageEs ??
          `Reset OK · día ${out.operatingDayKey ?? '—'} · raw SM ${out.smFixturesRefreshed ?? 0} · picks borrados: ${out.dailyPicksDeleted ?? '—'}${log}`,
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('404')) {
        setLastMsg(
          '404: activá BT2_DEV_OPERATING_DAY_RESET=1 en el .env del API y reiniciá uvicorn.',
        )
      } else {
        setLastMsg(msg)
      }
    } finally {
      setBusy(false)
    }
  }

  const onCloseSessionOnly = async () => {
    if (!getStoredJwt()) {
      setLastMsg('Iniciá sesión BT2 primero.')
      return
    }
    setBusy(true)
    setLastMsg(null)
    try {
      try {
        await bt2FetchJson('/bt2/session/close', { method: 'POST' })
        setLastMsg(
          'Sesión operativa cerrada en servidor. El snapshot de bóveda sigue en BD hasta que uses reset dev o admin regenerate.',
        )
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        if (msg.includes('404')) {
          setLastMsg('No había sesión abierta para hoy (404).')
        } else {
          throw e
        }
      }
      invalidateVaultClientCache()
      await useSessionStore.getState().hydrateFromApi()
      await useVaultStore.getState().loadApiPicks()
    } catch (e) {
      setLastMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="rounded-xl border border-amber-200/80 bg-amber-50/90 px-4 py-3 text-sm text-amber-950"
      aria-label="Herramientas de desarrollo — bóveda"
    >
      <p className="text-[10px] font-bold uppercase tracking-widest text-amber-900/80">
        Solo desarrollo
      </p>
      <p className="mt-1 text-xs leading-relaxed text-amber-900/90">
        <span className="font-mono">Reset día</span> hace el flujo completo de prueba: primero
        vuelve a pedir a SportMonks cada fixture del pool valor del día (includes actuales) y
        hace UPSERT en <span className="font-mono">raw_sportmonks_fixtures</span>; después borra
        snapshot de bóveda, desbloqueos y metadata, y cierra la sesión operativa. Luego esta
        pantalla vuelve a abrir sesión y cargar picks (nuevo <span className="font-mono">ds_input</span>{' '}
        + DSR). Requiere <span className="font-mono">BT2_DEV_OPERATING_DAY_RESET=1</span> y clave SM
        en el API. «Solo cerrar sesión» no refresca raw ni borra snapshot.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void onResetDay()}
          className="rounded-lg border border-amber-800/30 bg-amber-900 px-3 py-1.5 text-xs font-bold text-amber-50 disabled:opacity-50"
        >
          {busy ? '…' : 'Reset día (snapshot + sesión)'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onCloseSessionOnly()}
          className="rounded-lg border border-amber-800/40 bg-white px-3 py-1.5 text-xs font-semibold text-amber-950 disabled:opacity-50"
        >
          Solo cerrar sesión servidor
        </button>
      </div>
      {lastMsg ? (
        <p className="mt-2 font-mono text-[11px] leading-snug text-amber-950/90">{lastMsg}</p>
      ) : null}
    </div>
  )
}
