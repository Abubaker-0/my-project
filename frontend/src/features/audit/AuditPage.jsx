import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listAuditLogs } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { PageHeader } from "../../components/PageHeader";
import { TextField } from "../../components/TextField";
import { useDebounce } from "../../hooks/useDebounce";
import { usePagination } from "../../hooks/usePagination";
import { errorMessage } from "../../utils/errors";
import { formatDateTime } from "../../utils/format";

export function AuditPage() {
  const paging = usePagination({ sort: "-created_at" });
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const debouncedAction = useDebounce(action);
  const debouncedEntity = useDebounce(entity);
  const query = useQuery({
    queryKey: ["audit", paging.page, paging.sort, debouncedAction, debouncedEntity],
    queryFn: () =>
      listAuditLogs({
        page: paging.page,
        page_size: paging.pageSize,
        sort: paging.sort,
        action: debouncedAction,
        entity: debouncedEntity,
      }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Audit log"
        description="Sign-ins, account changes, and permission edits. Branch staff see only their campus."
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <TextField
          label="Action"
          value={action}
          placeholder="login"
          onChange={(event) => {
            setAction(event.target.value);
            paging.setPage(1);
          }}
        />
        <TextField
          label="Entity"
          value={entity}
          placeholder="user"
          onChange={(event) => {
            setEntity(event.target.value);
            paging.setPage(1);
          }}
        />
      </div>
      <DataTable
        columns={[
          {
            key: "created_at",
            header: "When",
            sortKey: "created_at",
            render: (row) => formatDateTime(row.created_at),
          },
          { key: "action", header: "Action", sortKey: "action" },
          {
            key: "entity",
            header: "Entity",
            sortKey: "entity",
            render: (row) => `${row.entity}${row.entity_id ? ` #${row.entity_id}` : ""}`,
          },
          { key: "user_id", header: "Actor", render: (row) => row.user_id ?? "—" },
          { key: "ip", header: "Address", render: (row) => row.ip || "—" },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No audit records"
        emptyBody="Actions such as sign-in and permission changes will appear here."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total ?? 0}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
    </div>
  );
}
