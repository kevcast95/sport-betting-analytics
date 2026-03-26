import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'altea:listPageSize'

export const LIST_PAGE_SIZE_OPTIONS = [5, 10, 20, 50] as const

export type ListPageSize = (typeof LIST_PAGE_SIZE_OPTIONS)[number]

function coerceSize(raw: string | null): ListPageSize {
  const n = Number.parseInt(raw ?? '', 10)
  if (LIST_PAGE_SIZE_OPTIONS.includes(n as ListPageSize)) {
    return n as ListPageSize
  }
  return 10
}

/**
 * Tamaño de página para listas (picks, eventos, dashboard reciente).
 * Persistido en localStorage para respetar la preferencia del usuario.
 */
export function useListPageSize(): {
  pageSize: ListPageSize
  setPageSize: (n: ListPageSize) => void
} {
  const [pageSize, setPageSizeState] = useState<ListPageSize>(() => {
    if (typeof window === 'undefined') return 10
    return coerceSize(window.localStorage.getItem(STORAGE_KEY))
  })

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(pageSize))
  }, [pageSize])

  const setPageSize = useCallback((n: ListPageSize) => {
    setPageSizeState(n)
  }, [])

  return { pageSize, setPageSize }
}
