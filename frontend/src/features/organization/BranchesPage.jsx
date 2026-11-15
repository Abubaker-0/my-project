import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createBranch, listBranches } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { TextArea } from "../../components/TextArea";
import { TextField } from "../../components/TextField";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { emptyToNull, reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  code: z
    .string()
    .min(2)
    .max(32)
    .regex(/^[A-Za-z0-9][A-Za-z0-9-]+$/, "Use letters, numbers, and hyphens"),
  name: z.string().min(2, "Enter a name").max(200),
  phone: z.string().max(32).optional(),
  email: z.union([z.literal(""), z.string().email("Enter a valid email")]),
  address: z.string().max(2000).optional(),
});

export function BranchesPage() {
  const paging = usePagination({ sort: "name" });
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("branches:create");
  const query = useQuery({
    queryKey: ["branches", paging.page, paging.sort],
    queryFn: () =>
      listBranches({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Organization"
        title="Branches"
        description="Each campus keeps its own students, courses, and admission numbers."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New branch</Button> : null}
      />
      <DataTable
        columns={[
          {
            key: "name",
            header: "Name",
            sortKey: "name",
            render: (row) => <RecordLink to={`/branches/${row.id}`}>{row.name}</RecordLink>,
          },
          { key: "code", header: "Code", sortKey: "code" },
          { key: "phone", header: "Phone", render: (row) => row.phone || "—" },
          {
            key: "status",
            header: "Status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No branches"
        emptyBody="Create the first campus before admitting students."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <BranchForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function BranchForm({ onClose }) {
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { email: "", phone: "", address: "" },
  });
  const mutation = useMutation({
    mutationFn: createBranch,
    onSuccess: () => {
      push({ tone: "success", message: "Branch created." });
      queryClient.invalidateQueries({ queryKey: ["branches"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New branch" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            code: values.code,
            name: values.name,
            phone: emptyToNull(values.phone),
            email: emptyToNull(values.email),
            address: emptyToNull(values.address),
          }),
        )}
      >
        <TextField label="Code" error={errors.code?.message} {...register("code")} />
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField label="Phone" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Email" error={errors.email?.message} {...register("email")} />
        <TextArea label="Address" error={errors.address?.message} {...register("address")} />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save branch
          </Button>
        </div>
      </form>
    </Modal>
  );
}
