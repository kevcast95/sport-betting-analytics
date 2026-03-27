import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { fetchJson } from '@/lib/api'
import { useTrackingUser } from '@/hooks/useTrackingUser'
import { useUsersQuery } from '@/hooks/useUsersQuery'
import type { UserOut } from '@/types/api'

/**
 * Cuenta activa para tracking (picks tomados, cierres, combinadas).
 * Vive en la parte superior del sidebar, no en el contenido del dashboard ni del tablero.
 */
export function SidebarUserSection() {
  const { userId, setUserId } = useTrackingUser()
  const qc = useQueryClient()
  const usersQ = useUsersQuery()
  const users = useMemo(() => usersQ.data ?? [], [usersQ.data])

  useEffect(() => {
    if (users.length === 0) return
    if (userId == null) {
      setUserId(users[0].user_id)
      return
    }
    if (!users.some((u) => u.user_id === userId)) {
      setUserId(users[0].user_id)
    }
  }, [users, userId, setUserId])

  const bootstrapM = useMutation({
    mutationFn: () => fetchJson<UserOut[]>('/users/bootstrap', { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['users'] })
    },
  })

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-900/80">
        Cuenta
      </p>
      <label className="block text-[10px] text-app-muted">
        <span className="sr-only">Usuario</span>
        <select
          className="mt-0.5 w-full rounded-md border border-app-line bg-white px-2 py-2 text-xs text-app-fg shadow-sm"
          value={userId != null ? String(userId) : ''}
          onChange={(e) => {
            const v = e.target.value
            setUserId(v === '' ? null : Number(v))
          }}
          disabled={usersQ.isLoading || users.length === 0}
        >
          {users.length === 0 ? (
            <option value="">
              {usersQ.isLoading ? 'Cargando…' : 'Sin usuarios'}
            </option>
          ) : (
            users.map((u) => (
              <option key={u.user_id} value={String(u.user_id)}>
                {u.display_name} ({u.slug})
              </option>
            ))
          )}
        </select>
      </label>
      <button
        type="button"
        className="w-full rounded-md border border-app-line bg-white px-2 py-2 text-[11px] text-app-fg shadow-sm disabled:opacity-40"
        disabled={bootstrapM.isPending}
        onClick={() => bootstrapM.mutate()}
      >
        Crear usuarios prueba
      </button>
      {usersQ.isError && (
        <p className="text-[10px] leading-snug text-app-danger whitespace-pre-wrap">
          {(usersQ.error as Error).message}
        </p>
      )}
    </div>
  )
}
