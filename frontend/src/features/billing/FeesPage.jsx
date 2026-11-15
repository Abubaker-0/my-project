import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createFeePlan, listFeePlans } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { SelectField } from "../../components/SelectField";
import { TextField } from "../../components/TextField";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { reportError } from "../records/form";

const schema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  name: z.string().min(2, "Enter a name").max(200),
  amount: z.string().regex(/^\d+(\.\d{1,2})?$/, "Enter an amount like 150.00"),
  billing_period: z.enum(["once", "monthly", "term"]),
});

export function FeesPage() {
  const paging = usePagination({ sort: "name" });
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("fees:create");
  const query = useQuery({
    queryKey: ["fee-plans", paging.page, paging.sort],
    queryFn: () =>
      listFeePlans({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });
  return (
    <div>
      <PageHeader
        eyebrow="Finance"
        title="Fee plans"
        description="A plan is a reusable charge. Invoices copy the amount at the moment they are issued."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New fee plan</Button> : null}
      />
      <DataTable
        columns={[
          { key: "name", header: "Name", sortKey: "name" },
          { key: "amount", header: "Amount", sortKey: "amount" },
          { key: "billing_period", header: "Period" },
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
        emptyTitle="No fee plans"
        emptyBody="Add monthly tuition or a one-time charge."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <PlanForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function PlanForm({ onClose }) {
  const campuses = useCampusOptions();
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { branch_id: campuses.defaultId, billing_period: "monthly", amount: "150.00" },
  });
  const mutation = useMutation({
    mutationFn: createFeePlan,
    onSuccess: () => {
      push({ tone: "success", message: "Fee plan created." });
      queryClient.invalidateQueries({ queryKey: ["fee-plans"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New fee plan" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            name: values.name,
            amount: values.amount,
            billing_period: values.billing_period,
          }),
        )}
      >
        <CampusSelect
          register={register}
          error={errors.branch_id?.message}
          items={campuses.items}
        />
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField label="Amount" error={errors.amount?.message} {...register("amount")} />
        <SelectField label="Period" {...register("billing_period")}>
          <option value="monthly">Monthly</option>
          <option value="term">Term</option>
          <option value="once">Once</option>
        </SelectField>
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save plan
          </Button>
        </div>
      </form>
    </Modal>
  );
}
