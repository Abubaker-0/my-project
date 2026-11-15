import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { Spinner } from "./Spinner";

export function DataTable({
  columns,
  rows,
  loading,
  error,
  onRetry,
  emptyTitle,
  emptyBody,
  page,
  pageSize,
  total,
  onPage,
  sort,
  onSort,
}) {
  const pageCount = Math.max(1, Math.ceil((total || 0) / pageSize));
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-card shadow-card">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-paper text-xs uppercase tracking-wide text-ink-500">
            <tr>
              {columns.map((column) => {
                const active = sort === column.sortKey || sort === `-${column.sortKey}`;
                const next = sort === column.sortKey ? `-${column.sortKey}` : column.sortKey;
                return (
                  <th key={column.key} scope="col" className="px-4 py-3 font-medium">
                    {column.sortKey && onSort ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1"
                        onClick={() => onSort(next)}
                      >
                        {column.header}
                        {active ? (
                          <span aria-hidden="true">{sort.startsWith("-") ? "↓" : "↑"}</span>
                        ) : null}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-10" colSpan={columns.length}>
                  <Spinner label="Loading records" />
                </td>
              </tr>
            ) : null}
            {!loading && error ? (
              <tr>
                <td colSpan={columns.length}>
                  <ErrorState body={error} onRetry={onRetry} />
                </td>
              </tr>
            ) : null}
            {!loading && !error && rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length}>
                  <EmptyState title={emptyTitle} body={emptyBody} />
                </td>
              </tr>
            ) : null}
            {!loading && !error
              ? rows.map((row) => (
                  <tr key={row.id} className="border-t border-line">
                    {columns.map((column) => (
                      <td key={column.key} className="px-4 py-3 align-middle">
                        {column.render ? column.render(row) : row[column.key]}
                      </td>
                    ))}
                  </tr>
                ))
              : null}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-ink-700">
        <p>
          {total || 0} record{total === 1 ? "" : "s"}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-lg border border-line px-3 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
          >
            Previous
          </button>
          <span>
            {page} / {pageCount}
          </span>
          <button
            type="button"
            className="rounded-lg border border-line px-3 py-1 disabled:opacity-40"
            disabled={page >= pageCount}
            onClick={() => onPage(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
