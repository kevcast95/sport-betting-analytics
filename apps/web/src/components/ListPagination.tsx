import { LIST_PAGE_SIZE_OPTIONS, type ListPageSize } from '@/hooks/useListPageSize'

type Props = {
  page: number
  pageSize: ListPageSize
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (size: ListPageSize) => void
  /** prefijo para id accesible del select */
  idPrefix?: string
  className?: string
}

export function ListPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  idPrefix = 'pag',
  className = '',
}: Props) {
  const totalPages = total <= 0 ? 0 : Math.ceil(total / pageSize)
  const safePage =
    totalPages <= 0 ? 0 : Math.min(Math.max(0, page), totalPages - 1)
  const from = total <= 0 ? 0 : safePage * pageSize + 1
  const to = Math.min(total, safePage * pageSize + pageSize)

  if (total <= 0) {
    return null
  }

  return (
    <div
      className={`flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between ${className}`}
    >
      <p className="text-[11px] text-app-muted">
        <span className="font-mono tabular-nums text-app-fg">{from}</span>
        {'–'}
        <span className="font-mono tabular-nums text-app-fg">{to}</span>
        {' de '}
        <span className="font-mono tabular-nums text-app-fg">{total}</span>
        {totalPages > 1 ? (
          <>
            {' · página '}
            <span className="font-mono tabular-nums text-app-fg">
              {safePage + 1}
            </span>
            {' / '}
            <span className="font-mono tabular-nums text-app-fg">{totalPages}</span>
          </>
        ) : null}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {onPageSizeChange ? (
          <label className="flex items-center gap-1.5 text-[11px] text-app-muted">
            Por página
            <select
              id={`${idPrefix}-size`}
              className="rounded-md border border-app-line bg-white px-2 py-1 text-xs text-app-fg shadow-sm"
              value={pageSize}
              onChange={(e) =>
                onPageSizeChange(Number(e.target.value) as ListPageSize)
              }
            >
              {LIST_PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {totalPages > 1 ? (
          <div className="flex gap-1">
            <button
              type="button"
              className="rounded-md border border-app-line bg-white px-2 py-1 text-xs text-app-fg shadow-sm disabled:opacity-40"
              disabled={safePage <= 0}
              onClick={() => onPageChange(safePage - 1)}
            >
              Anterior
            </button>
            <button
              type="button"
              className="rounded-md border border-app-line bg-white px-2 py-1 text-xs text-app-fg shadow-sm disabled:opacity-40"
              disabled={safePage >= totalPages - 1}
              onClick={() => onPageChange(safePage + 1)}
            >
              Siguiente
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
