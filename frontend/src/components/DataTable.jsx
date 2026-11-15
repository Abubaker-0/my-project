/**
 * Sortable table with loading, error, and empty states.
 * Sorting toggles the API `ordering` field rather than reordering in the browser.
 */
import { useTranslation } from 'react-i18next';
import { EmptyState, Loader, Pagination } from './ui';

export function DataTable({
  columns, rows, loading, error, page, pageSize, count, onPage, ordering, onSort,
}) {
  const { t } = useTranslation();
  if (loading) return <Loader label={t('common.loading')} />;
  if (error) return <div className="error-state">{error}</div>;
  if (!rows.length) return <EmptyState title={t('common.empty')} text="" />;
  return (
    <>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} onClick={() => column.sort && onSort?.(ordering === column.sort ? `-${column.sort}` : column.sort)}>
                  {column.label}{ordering === column.sort ? ' ↑' : ordering === `-${column.sort}` ? ' ↓' : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id || JSON.stringify(row)}>
                {columns.map((column) => <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination
        page={page}
        pageSize={pageSize}
        count={count}
        onPage={onPage}
        labelPage={t('common.page')}
        labelOf={t('common.of')}
        labelRows={t('common.rows')}
      />
    </>
  );
}
