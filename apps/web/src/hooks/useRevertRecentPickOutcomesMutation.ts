import { useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'

export function useRevertRecentPickOutcomesMutation(userId: number | null) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (minutes: number) => {
      if (userId == null) throw new Error('user')
      return fetchJson(
        `/users/${userId}/picks/revert-recent-outcomes?minutes=${minutes}`,
        { method: 'POST' },
      )
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['board'] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
      void qc.invalidateQueries({ queryKey: ['picks'] })
    },
  })
}

