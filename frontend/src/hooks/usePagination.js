import { useState } from "react";

export function usePagination(initial = {}) {
  const [state, setState] = useState({
    page: 1,
    pageSize: 20,
    sort: "full_name",
    q: "",
    ...initial,
  });
  return {
    ...state,
    setPage: (page) => setState((current) => ({ ...current, page })),
    setSort: (sort) => setState((current) => ({ ...current, sort, page: 1 })),
    setQuery: (q) => setState((current) => ({ ...current, q, page: 1 })),
  };
}
