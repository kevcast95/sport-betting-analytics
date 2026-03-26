import { useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'

export type QuickOutcomeVars = {
  pickId: number
  dailyRunId: number
  taken: boolean
  outcome: 'win' | 'loss' | 'pending'
}

/**
 * PUT /users/.../picks/.../taken solo para fijar cierre manual (gané / perdí / pendiente),
 * manteniendo el flag «tomé» y el stake que ya existan en servidor.
 */
export function usePickOutcomeQuickMutation(userId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (vars: QuickOutcomeVars) => {
      if (userId == null) throw new Error('user')
      return fetchJson(`/users/${userId}/picks/${vars.pickId}/taken`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taken: vars.taken,
          user_outcome: vars.outcome,
        }),
      })
    },
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ['board', vars.dailyRunId, userId] })
      void qc.invalidateQueries({ queryKey: ['pick', vars.pickId] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
      if (userId != null) {
        void qc.invalidateQueries({ queryKey: ['user', userId] })
      }
    },
  })
}
