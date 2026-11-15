/**
 * Loads one paginated API list. Search, ordering, and filters reset to page 1.
 * The hook reads the envelope, so pages receive rows and a total count.
 */
import { useEffect, useState } from 'react';
import client, { errorMessage, unwrap } from '../api/client';

export function usePaged(path, extra = {}) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [ordering, setOrdering] = useState('');
  const [filters, setFilters] = useState(extra);
  const [tick, setTick] = useState(0);
  const [state, setState] = useState({ rows: [], count: 0, loading: true, error: '' });
  const filterKey = JSON.stringify(filters);

  useEffect(() => {
    setPage(1);
  }, [search, ordering, filterKey]);

  useEffect(() => {
    let cancelled = false;
    if (!path) {
      setState({ rows: [], count: 0, loading: false, error: '' });
      return undefined;
    }
    setState((current) => ({ ...current, loading: true, error: '' }));
    const query = new URLSearchParams();
    query.set('page', String(page));
    query.set('page_size', '10');
    if (search) query.set('search', search);
    if (ordering) query.set('ordering', ordering);
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== '' && value !== undefined && value !== null) query.set(key, value);
    });
    const joiner = path.includes('?') ? '&' : '?';
    client.get(`${path}${joiner}${query.toString()}`)
      .then((response) => {
        if (cancelled) return;
        const data = unwrap(response) || {};
        const rows = Array.isArray(data) ? data : data.results || [];
        setState({ rows, count: data.count ?? rows.length, loading: false, error: '' });
      })
      .catch((error) => {
        if (!cancelled) setState({ rows: [], count: 0, loading: false, error: errorMessage(error) });
      });
    return () => {
      cancelled = true;
    };
  }, [path, page, search, ordering, filterKey, tick]);

  return {
    ...state,
    page,
    setPage,
    search,
    setSearch,
    ordering,
    setOrdering,
    filters,
    setFilters,
    reload: () => setTick((value) => value + 1),
    pageSize: 10,
  };
}
