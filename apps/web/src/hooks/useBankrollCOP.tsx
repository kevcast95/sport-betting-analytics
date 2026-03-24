import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { fetchJson } from '@/lib/api'
import type { UserOut } from '@/types/api'

/**
 * Bankroll en COP persistido en el servidor por usuario (`users.bankroll_cop`).
 */
export function useBankrollCOP(userId: number | null) {
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['user', userId],
    enabled: userId != null,
    queryFn: () => fetchJson<UserOut>(`/users/${userId}`),
  })

  const m = useMutation({
    mutationFn: async (v: number | null) => {
      if (userId == null) return
      await fetchJson<UserOut>(`/users/${userId}/bankroll`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bankroll_cop: v }),
      })
    },
    onSuccess: () => {
      if (userId == null) return
      void qc.invalidateQueries({ queryKey: ['user', userId] })
      void qc.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const br = q.data?.bankroll_cop
  const bankrollCOP =
    userId == null
      ? null
      : br != null && typeof br === 'number' && Number.isFinite(br)
        ? br
        : null

  const setBankrollCOP = useCallback(
    (v: number | null) => {
      if (userId == null) return
      m.mutate(v)
    },
    [userId, m],
  )

  return {
    bankrollCOP,
    setBankrollCOP,
    isBankrollLoading: userId != null && q.isPending,
    isBankrollSaving: m.isPending,
  }
}
