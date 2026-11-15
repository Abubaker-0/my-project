import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createStudent, listStudents } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { SelectField } from "../../components/SelectField";
import { TextField } from "../../components/TextField";
import { useDebounce } from "../../hooks/useDebounce";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { emptyToNull, reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z
  .object({
    branch_id: z.string().min(1, "Choose a campus"),
    first_name: z.string().min(1, "Enter a first name").max(100),
    last_name: z.string().min(1, "Enter a last name").max(100),
    gender: z.enum(["female", "male", "other", "unspecified"]),
    grade_level: z.string().max(64).optional(),
    school_name: z.string().max(200).optional(),
    guardian_name: z.string().max(200).optional(),
    relationship: z.string().max(64).optional(),
    phone: z.string().max(32).optional(),
    email: z.union([z.literal(""), z.string().email("Enter a valid email")]),
  })
  .superRefine((value, context) => {
    if (value.guardian_name && value.relationship.trim().length < 2) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["relationship"],
        message: "Enter how this person is related",
      });
    }
  });

export function StudentsPage() {
  const paging = usePagination({ sort: "admission_no", pageSize: 50 });
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search);
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("students:create");
  const query = useQuery({
    queryKey: ["students", paging.page, paging.pageSize, paging.sort, debounced],
    queryFn: () =>
      listStudents({
        page: paging.page,
        page_size: paging.pageSize,
        sort: paging.sort,
        q: debounced,
      }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Admissions"
        title="Students"
        description="Each admission number is issued by the campus and stays with the student."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New student</Button> : null}
      />
      <div className="mb-4 max-w-sm">
        <TextField
          label="Search"
          value={search}
          placeholder="Name, admission number, or grade"
          onChange={(event) => {
            setSearch(event.target.value);
            paging.setPage(1);
          }}
        />
      </div>
      <DataTable
        columns={[
          {
            key: "admission_no",
            header: "Admission",
            sortKey: "admission_no",
            render: (row) => <RecordLink to={`/students/${row.id}`}>{row.admission_no}</RecordLink>,
          },
          { key: "full_name", header: "Name" },
          { key: "grade_level", header: "Grade", render: (row) => row.grade_level || "—" },
          { key: "school_name", header: "School", render: (row) => row.school_name || "—" },
          {
            key: "status",
            header: "Status",
            sortKey: "status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
          {
            key: "admission_date",
            header: "Admitted",
            sortKey: "admission_date",
            render: (row) => formatDate(row.admission_date),
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No students yet"
        emptyBody="Admit a student or convert an inquiry to start the register."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <StudentForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function StudentForm({ onClose }) {
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
    defaultValues: {
      branch_id: campuses.defaultId,
      gender: "unspecified",
      email: "",
      grade_level: "",
      school_name: "",
      guardian_name: "",
      relationship: "Parent",
      phone: "",
    },
  });
  const mutation = useMutation({
    mutationFn: createStudent,
    onSuccess: () => {
      push({ tone: "success", message: "Student admitted." });
      queryClient.invalidateQueries({ queryKey: ["students"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });

  function onSubmit(values) {
    mutation.mutate({
      branch_id: Number(values.branch_id),
      first_name: values.first_name,
      last_name: values.last_name,
      gender: values.gender,
      grade_level: emptyToNull(values.grade_level),
      school_name: emptyToNull(values.school_name),
      guardian: values.guardian_name
        ? {
            full_name: values.guardian_name,
            relationship: values.relationship,
            phone: emptyToNull(values.phone),
            email: emptyToNull(values.email),
            is_primary: true,
          }
        : null,
    });
  }

  return (
    <Modal title="New student" onClose={onClose}>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={handleSubmit(onSubmit)}>
        <div className="sm:col-span-2">
          <CampusSelect
            register={register}
            error={errors.branch_id?.message}
            items={campuses.items}
          />
        </div>
        <TextField
          label="First name"
          error={errors.first_name?.message}
          {...register("first_name")}
        />
        <TextField label="Last name" error={errors.last_name?.message} {...register("last_name")} />
        <SelectField label="Gender" error={errors.gender?.message} {...register("gender")}>
          <option value="unspecified">Unspecified</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="other">Other</option>
        </SelectField>
        <TextField label="Grade" error={errors.grade_level?.message} {...register("grade_level")} />
        <div className="sm:col-span-2">
          <TextField
            label="School"
            error={errors.school_name?.message}
            {...register("school_name")}
          />
        </div>
        <TextField
          label="Primary guardian"
          error={errors.guardian_name?.message}
          {...register("guardian_name")}
        />
        <TextField
          label="Relationship"
          error={errors.relationship?.message}
          {...register("relationship")}
        />
        <TextField label="Guardian phone" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Guardian email" error={errors.email?.message} {...register("email")} />
        <div className="sm:col-span-2 flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Admit student
          </Button>
        </div>
      </form>
    </Modal>
  );
}
