import { useCallback, useState } from 'react'
import { BunkerViewHeader } from '@/components/layout/BunkerViewHeader'
import { postBt2AdminVaultRegenerateSnapshot } from '@/lib/api'
import type { Bt2AdminVaultRegenerateSnapshotOut } from '@/lib/bt2Types'

function defaultOperatingDayKey(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * US-FE-059 / T-219 — admin CDM + refresh snapshot.
 * Lista paginada T-214: hasta que exista `GET /bt2/admin/...` publicado, se muestra aviso explícito.
 * Refresh: `POST /bt2/admin/vault/regenerate-daily-snapshot` (misma clave admin que otras vistas).
 */
export default function AdminCdmAuditPage() {
  const [operatingDayKey, setOperatingDayKey] = useState(defaultOperatingDayKey)
  const [userId, setUserId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Bt2AdminVaultRegenerateSnapshotOut | null>(
    null,
  )

  const onRegenerate = useCallback(async () => {
    const uid = userId.trim()
    if (!uid) {
      setError('Indica el UUID de usuario BT2 (mismo que en JWT / bt2_users.id).')
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const out = await postBt2AdminVaultRegenerateSnapshot(uid, operatingDayKey)
      setResult(out)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('Falta VITE_BT2_ADMIN_API_KEY')) {
        setError(
          'Configura VITE_BT2_ADMIN_API_KEY en apps/web/.env (mismo valor que BT2_ADMIN_API_KEY en el servidor).',
        )
      } else {
        setError(msg.length > 260 ? `${msg.slice(0, 260)}…` : msg)
      }
    } finally {
      setBusy(false)
    }
  }, [userId, operatingDayKey])

  return (
    <div className="w-full space-y-8" aria-label="Auditoría CDM administración">
      <BunkerViewHeader
        title="Auditoría CDM y snapshot"
        subtitle="Solo uso interno · misma clave X-BT2-Admin-Key que Precisión DSR"
      />

      <div className="rounded-xl border border-[#a4b4be]/15 bg-white/90 p-6">
        <h2 className="text-sm font-bold tracking-tight text-[#26343d]">
          Regenerar snapshot de bóveda
        </h2>
        <p className="mt-2 text-xs leading-relaxed text-[#52616a]">
          Borra filas de bóveda del usuario y día indicados y vuelve a ejecutar el
          pipeline del servidor (equivalente operativo a forzar un snapshot fresco tras
          ingesta). No sustituye el job programado ni valida ingesta rota como día sano
          (D-06-033).
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Usuario (UUID BT2)
            </span>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2 font-mono text-xs text-[#26343d]"
              autoComplete="off"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#52616a]">
              Día operativo
            </span>
            <input
              type="date"
              value={operatingDayKey}
              onChange={(e) => setOperatingDayKey(e.target.value)}
              className="rounded-lg border border-[#a4b4be]/35 bg-white px-3 py-2 font-mono text-xs text-[#26343d]"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onRegenerate()}
          className="mt-4 rounded-lg bg-[#26343d] px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
        >
          {busy ? 'Regenerando…' : 'Regenerar snapshot'}
        </button>
        {error ? (
          <p className="mt-4 text-sm text-[#9b1c1c]" role="alert">
            {error}
          </p>
        ) : null}
        {result ? (
          <div className="mt-4 rounded-lg border border-[#d1fae5] bg-[#ecfdf5]/80 p-4 text-sm text-[#065f46]">
            <p className="font-mono text-xs leading-relaxed text-[#26343d]">
              Insertadas (esta corrida): {result.picksInsertedThisRun} · Total tras
              regenerar: {result.picksTotalAfter}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[#52616a]">
              {result.messageEs}
            </p>
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-[#fde68a] bg-[#fffbeb] p-6">
        <h2 className="text-sm font-bold tracking-tight text-[#92400e]">
          Lista de auditoría CDM (US-BE-046 / T-214)
        </h2>
        <p className="mt-2 text-xs leading-relaxed text-[#78350f]">
          En esta rama el endpoint admin acordado para motivos operativos por evento
          (p. ej. <span className="font-mono">sin_ingesta</span>,{' '}
          <span className="font-mono">en_snapshot</span> — D-06-040) aún no está
          publicado en OpenAPI. Cuando BE exponga el contrato, esta vista consumirá la
          lista paginada sin inventar forma de JSON.
        </p>
        <p className="mt-3 text-[10px] leading-snug text-[#92400e]">
          Referencia de producto:{' '}
          <code className="font-mono">docs/bettracker2/notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md</code>
        </p>
      </div>
    </div>
  )
}
