import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  createBatch,
  getAcademicYear,
  listAcademicYears,
  listBatches,
  listCourses,
  listRooms,
} from "../../api/resources";
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
import { formatDate, seatSummary } from "../../utils/format";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  course_id: z.string().min(1, "Choose a course"),
  year_id: z.string().min(1, "Choose a year"),
  term_id: z.string().min(1, "Choose a term"),
  room_id: z.string().optional(),
  name: z.string().min(2, "Enter a name").max(200),
  start_date: z.string().min(1, "Choose a start date"),
  end_date: z.string().min(1, "Choose an end date"),
  capacity: z.coerce.number().int().min(1).max(10000),
});

export function BatchesPage() {
  const paging = usePagination({ sort: "name" });
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("batches:create");
  const query = useQuery({
    queryKey: ["batches", paging.page, paging.sort],
    queryFn: () =>
      listBatches({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Academics"
        title="Batches"
        description="A batch holds a fixed number of seats. Extra students wait in order and move up when a seat opens."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New batch</Button> : null}
      />
      <DataTable
        columns={[
          {
            key: "name",
            header: "Batch",
            sortKey: "name",
            render: (row) => <RecordLink to={`/batches/${row.id}`}>{row.name}</RecordLink>,
          },
          { key: "course_name", header: "Course" },
          { key: "term_name", header: "Term" },
          { key: "room_name", header: "Room", render: (row) => row.room_name || "—" },
          {
            key: "seats",
            header: "Seats",
            render: (row) => seatSummary(row.active_count, row.capacity, row.waitlist_count),
          },
          {
            key: "status",
            header: "Status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
          {
            key: "start_date",
            header: "Starts",
            sortKey: "start_date",
            render: (row) => formatDate(row.start_date),
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No batches"
        emptyBody="Create a batch after a course, a term, and a room exist."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <BatchForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function BatchForm({ onClose }) {
  const campuses = useCampusOptions();
  const courses = useQuery({
    queryKey: ["courses", "options"],
    queryFn: () => listCourses({ page_size: 100, sort: "name" }),
  });
  const years = useQuery({
    queryKey: ["academic-years", "options"],
    queryFn: () => listAcademicYears({ page_size: 100, sort: "name" }),
  });
  const rooms = useQuery({
    queryKey: ["rooms", "options"],
    queryFn: () => listRooms({ page_size: 100, sort: "name" }),
  });
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { branch_id: campuses.defaultId, room_id: "", capacity: 12 },
  });
  const yearId = watch("year_id");
  const year = useQuery({
    queryKey: ["academic-years", yearId],
    queryFn: () => getAcademicYear(yearId),
    enabled: Boolean(yearId),
  });
  const mutation = useMutation({
    mutationFn: createBatch,
    onSuccess: () => {
      push({ tone: "success", message: "Batch created." });
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });

  return (
    <Modal title="New batch" onClose={onClose}>
      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            course_id: Number(values.course_id),
            term_id: Number(values.term_id),
            room_id: values.room_id ? Number(values.room_id) : null,
            name: values.name,
            start_date: values.start_date,
            end_date: values.end_date,
            capacity: values.capacity,
            status: "planned",
          }),
        )}
      >
        <div className="sm:col-span-2">
          <CampusSelect
            register={register}
            error={errors.branch_id?.message}
            items={campuses.items}
          />
        </div>
        <SelectField label="Course" error={errors.course_id?.message} {...register("course_id")}>
          <option value="">Choose a course</option>
          {(courses.data?.items ?? []).map((course) => (
            <option key={course.id} value={course.id}>
              {course.name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Year" error={errors.year_id?.message} {...register("year_id")}>
          <option value="">Choose a year</option>
          {(years.data?.items ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Term" error={errors.term_id?.message} {...register("term_id")}>
          <option value="">Choose a term</option>
          {(year.data?.terms ?? []).map((term) => (
            <option key={term.id} value={term.id}>
              {term.name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Room" {...register("room_id")}>
          <option value="">No room yet</option>
          {(rooms.data?.items ?? []).map((room) => (
            <option key={room.id} value={room.id}>
              {room.name}
            </option>
          ))}
        </SelectField>
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField
          label="Capacity"
          type="number"
          error={errors.capacity?.message}
          {...register("capacity")}
        />
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
        <div className="sm:col-span-2 flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save batch
          </Button>
        </div>
      </form>
    </Modal>
  );
}
