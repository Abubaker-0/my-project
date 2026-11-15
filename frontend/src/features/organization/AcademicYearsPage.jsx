import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createAcademicYear, listAcademicYears } from "../../api/resources";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { TextField } from "../../components/TextField";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  name: z.string().min(2, "Enter a name").max(100),
  start_date: z.string().min(1, "Choose a start date"),
  end_date: z.string().min(1, "Choose an end date"),
  is_current: z.boolean(),
});

export function AcademicYearsPage() {
  const paging = usePagination({ sort: "name" });
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("academic_years:create");
  const query = useQuery({
    queryKey: ["academic-years", paging.page, paging.sort],
    queryFn: () =>
      listAcademicYears({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Calendar"
        title="Academic years"
        description="One year can be current for a campus. Terms have to sit inside that year."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New year</Button> : null}
      />
      <DataTable
        columns={[
          {
            key: "name",
            header: "Year",
            sortKey: "name",
            render: (row) => <RecordLink to={`/academic-years/${row.id}`}>{row.name}</RecordLink>,
          },
          {
            key: "start_date",
            header: "Starts",
            sortKey: "start_date",
            render: (row) => formatDate(row.start_date),
          },
          { key: "end_date", header: "Ends", render: (row) => formatDate(row.end_date) },
          {
            key: "is_current",
            header: "Current",
            render: (row) => (row.is_current ? <Badge tone="good">Current</Badge> : "—"),
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No academic years"
        emptyBody="Add the year before you open terms and batches."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <YearForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function YearForm({ onClose }) {
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
    defaultValues: { branch_id: campuses.defaultId, is_current: false },
  });
  const mutation = useMutation({
    mutationFn: createAcademicYear,
    onSuccess: () => {
      push({ tone: "success", message: "Academic year created." });
      queryClient.invalidateQueries({ queryKey: ["academic-years"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New academic year" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            name: values.name,
            start_date: values.start_date,
            end_date: values.end_date,
            is_current: values.is_current,
          }),
        )}
      >
        <CampusSelect
          register={register}
          error={errors.branch_id?.message}
          items={campuses.items}
        />
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField
          label="Starts"
          type="date"
          error={errors.start_date?.message}
          {...register("start_date")}
        />
        <TextField
          label="Ends"
          type="date"
          error={errors.end_date?.message}
          {...register("end_date")}
        />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register("is_current")} />
          Mark as the current year
        </label>
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save year
          </Button>
        </div>
      </form>
    </Modal>
  );
}
