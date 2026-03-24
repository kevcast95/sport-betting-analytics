import { useQuery } from '@tanstack/react-query'
import { fetchJson } from '@/lib/api'
import type { UserOut } from '@/types/api'

async function fetchUsersEnsuringDefaults(): Promise<UserOut[]> {
  let users = await fetchJson<UserOut[]>('/users')
  if (users.length === 0) {
    users = await fetchJson<UserOut[]>('/users/bootstrap', { method: 'POST' })
  }
  return users
}

export function useUsersQuery() {
  return useQuery({
    queryKey: ['users'],
    queryFn: fetchUsersEnsuringDefaults,
  })
}
