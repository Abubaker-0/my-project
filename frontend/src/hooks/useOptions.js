/** Loads a short list for a dropdown. Failures become an empty list. */
import { useEffect, useState } from 'react';
import client, { unwrap } from '../api/client';

export function useOptions(path) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    if (!path) return undefined;
    let cancelled = false;
    const joiner = path.includes('?') ? '&' : '?';
    client.get(`${path}${joiner}page_size=100`)
      .then((response) => {
        if (cancelled) return;
        const data = unwrap(response) || [];
        setRows(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        if (!cancelled) setRows([]);
      });
    return () => {
      cancelled = true;
    };
  }, [path]);
  return rows;
}
