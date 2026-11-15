import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createInvoice, listFeePlans, listInvoices, listStudents } from "../../api/resources";
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
import { formatDate } from "../../utils/format";
import { reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  student_id: z.string().min(1, "Choose a student"),
  fee_plan_id: z.string().optional(),
  due_date: z.string().min(1, "Choose a due date"),
  description: z.string().max(200).optional(),
  amount: z.string().optional(),
});

export function InvoicesPage() {
  const paging = usePagination({ sort: "-created_at" });
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("invoices:create");
  const query = useQuery({
    queryKey: ["invoices", paging.page, paging.sort],
    queryFn: () =>
      listInvoices({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });
  return (
    <div>
      <PageHeader
        eyebrow="Finance"
        title="Invoices"
        description="The balance is the total minus completed payments. Cancelling keeps the invoice and needs a reason."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New invoice</Button> : null}
      />
      <DataTable
        columns={[
          {
            key: "invoice_no",
            header: "Invoice",
            sortKey: "invoice_no",
            render: (row) => <RecordLink to={`/invoices/${row.id}`}>{row.invoice_no}</RecordLink>,
          },
          { key: "student_name", header: "Student" },
          { key: "total", header: "Total" },
          { key: "balance", header: "Balance" },
          {
            key: "due_date",
            header: "Due",
            sortKey: "due_date",
            render: (row) => formatDate(row.due_date),
          },
          {
            key: "status",
            header: "Status",
            sortKey: "status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No invoices"
        emptyBody="Issue an invoice from a fee plan or a one-off charge."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <InvoiceForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function InvoiceForm({ onClose }) {
  const students = useQuery({
    queryKey: ["students", "options"],
    queryFn: () => listStudents({ page_size: 100, sort: "admission_no" }),
  });
  const plans = useQuery({
    queryKey: ["fee-plans", "options"],
    queryFn: () => listFeePlans({ page_size: 100, sort: "name" }),
  });
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { fee_plan_id: "", description: "", amount: "" },
  });
  const mutation = useMutation({
    mutationFn: createInvoice,
    onSuccess: () => {
      push({ tone: "success", message: "Invoice issued." });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New invoice" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) => {
          const lines =
            values.description && values.amount
              ? [{ description: values.description, amount: values.amount }]
              : [];
          mutation.mutate({
            student_id: Number(values.student_id),
            fee_plan_id: values.fee_plan_id ? Number(values.fee_plan_id) : null,
            due_date: values.due_date,
            lines,
          });
        })}
      >
        <SelectField label="Student" error={errors.student_id?.message} {...register("student_id")}>
          <option value="">Choose a student</option>
          {(students.data?.items ?? []).map((student) => (
            <option key={student.id} value={student.id}>
              {student.admission_no} · {student.full_name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Fee plan" {...register("fee_plan_id")}>
          <option value="">No plan</option>
          {(plans.data?.items ?? []).map((plan) => (
            <option key={plan.id} value={plan.id}>
              {plan.name} · {plan.amount}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Due"
          type="date"
          error={errors.due_date?.message}
          {...register("due_date")}
        />
        <TextField label="Extra charge" {...register("description")} />
        <TextField label="Extra amount" {...register("amount")} />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Issue invoice
          </Button>
        </div>
      </form>
    </Modal>
  );
}
