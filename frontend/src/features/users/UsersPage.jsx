import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { deleteUser, listUsers } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { PageHeader } from "../../components/PageHeader";
import { TextField } from "../../components/TextField";
import { useDebounce } from "../../hooks/useDebounce";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDateTime } from "../../utils/format";
import { UserForm } from "./UserForm";

export function UsersPage() {
  const paging = usePagination({ sort: "full_name" });
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search);
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("users:create");
  const canDelete = usePermission("users:delete");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["users", paging.page, paging.pageSize, paging.sort, debounced],
    queryFn: () =>
      listUsers({
        page: paging.page,
        page_size: paging.pageSize,
        sort: paging.sort,
        q: debounced,
      }),
  });
  const remove = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      push({ tone: "success", message: "Account deactivated." });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Users"
        description="Accounts that can sign in. Deleting an account keeps the row and revokes its sessions."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New user</Button> : null}
      />
      <div className="mb-4 max-w-sm">
        <TextField
          label="Search"
          value={search}
          placeholder="Name, email, or phone"
          onChange={(event) => {
            setSearch(event.target.value);
            paging.setPage(1);
          }}
        />
      </div>
      <DataTable
        columns={[
          { key: "full_name", header: "Name", sortKey: "full_name" },
          { key: "email", header: "Email", sortKey: "email" },
          {
            key: "status",
            header: "Status",
            sortKey: "status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
          {
            key: "roles",
            header: "Roles",
            render: (row) => row.roles.map((role) => role.role_label).join(", ") || "—",
          },
          {
            key: "last_login_at",
            header: "Last sign-in",
            sortKey: "last_login_at",
            render: (row) => formatDateTime(row.last_login_at),
          },
          {
            key: "actions",
            header: "",
            render: (row) =>
              canDelete ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (
                      window.confirm(
                        `Deactivate ${row.full_name}? They will not be able to sign in.`,
                      )
                    ) {
                      remove.mutate(row.id);
                    }
                  }}
                  disabled={remove.isPending}
                >
                  Deactivate
                </Button>
              ) : null,
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No accounts match"
        emptyBody="Try another search, or create the first account for this branch."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total ?? 0}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <UserForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}
