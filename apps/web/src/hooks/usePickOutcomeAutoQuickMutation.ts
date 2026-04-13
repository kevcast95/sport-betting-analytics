import { useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'

export type QuickAutoVars = {
  pickId: number
  dailyRunId: number
  taken: boolean
}

/**
 * PUT /users/.../picks/.../taken con `user_outcome_auto=true`:
 * - fija el cierre manual en `null`
 * - el UI vuelve a usar el resultado del sistema (pick_results)
 */
export function usePickOutcomeAutoQuickMutation(userId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (vars: QuickAutoVars) => {
      if (userId == null) throw new Error('user')
      return fetchJson(`/users/${userId}/picks/${vars.pickId}/taken`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taken: vars.taken,
          user_outcome_auto: true,
        }),
      })
    },
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ['board', vars.dailyRunId] })
      void qc.invalidateQueries({ queryKey: ['pick', vars.pickId] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

