import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createCourse, createSubject, listCourses, listSubjects } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { Panel } from "../../components/Panel";
import { SelectField } from "../../components/SelectField";
import { TextField } from "../../components/TextField";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { emptyToNull, reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const courseSchema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  subject_id: z.string().min(1, "Choose a subject"),
  name: z.string().min(2, "Enter a name").max(200),
  level: z.string().min(1, "Enter a level").max(64),
  duration_weeks: z.coerce.number().int().min(1).max(104),
  description: z.string().max(4000).optional(),
});

const subjectSchema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  code: z
    .string()
    .min(2)
    .max(32)
    .regex(/^[A-Za-z0-9][A-Za-z0-9_-]+$/, "Use letters, numbers, _ or -"),
  name: z.string().min(2, "Enter a name").max(200),
});

export function CoursesPage() {
  const paging = usePagination({ sort: "name" });
  const [creating, setCreating] = useState(false);
  const [addingSubject, setAddingSubject] = useState(false);
  const canCreate = usePermission("courses:create");
  const canCreateSubject = usePermission("subjects:create");
  const courses = useQuery({
    queryKey: ["courses", paging.page, paging.sort],
    queryFn: () =>
      listCourses({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });
  const subjects = useQuery({
    queryKey: ["subjects"],
    queryFn: () => listSubjects({ page_size: 100, sort: "name" }),
  });

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Academics"
        title="Courses"
        description="A course belongs to one subject and one campus. Batches are the groups that actually meet."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New course</Button> : null}
      />
      <DataTable
        columns={[
          {
            key: "name",
            header: "Course",
            sortKey: "name",
            render: (row) => <RecordLink to={`/courses/${row.id}`}>{row.name}</RecordLink>,
          },
          { key: "subject_name", header: "Subject" },
          { key: "level", header: "Level", sortKey: "level" },
          { key: "duration_weeks", header: "Weeks" },
          {
            key: "status",
            header: "Status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
        ]}
        rows={courses.data?.items ?? []}
        loading={courses.isLoading}
        error={courses.isError ? errorMessage(courses.error) : null}
        onRetry={() => courses.refetch()}
        emptyTitle="No courses"
        emptyBody="Add a subject, then a course that uses it."
        page={paging.page}
        pageSize={paging.pageSize}
        total={courses.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      <Panel
        title="Subjects"
        actions={
          canCreateSubject ? (
            <Button variant="secondary" onClick={() => setAddingSubject(true)}>
              New subject
            </Button>
          ) : null
        }
      >
        <ul className="grid gap-2 sm:grid-cols-2">
          {(subjects.data?.items ?? []).map((subject) => (
            <li key={subject.id} className="rounded-xl border border-line px-3 py-2 text-sm">
              <span className="font-medium">{subject.code}</span> · {subject.name}
            </li>
          ))}
        </ul>
      </Panel>
      {creating ? (
        <CourseForm subjects={subjects.data?.items ?? []} onClose={() => setCreating(false)} />
      ) : null}
      {addingSubject ? <SubjectForm onClose={() => setAddingSubject(false)} /> : null}
    </div>
  );
}

function CourseForm({ subjects, onClose }) {
  const campuses = useCampusOptions();
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(courseSchema),
    defaultValues: { branch_id: campuses.defaultId, duration_weeks: 16, description: "" },
  });
  const mutation = useMutation({
    mutationFn: createCourse,
    onSuccess: () => {
      push({ tone: "success", message: "Course created." });
      queryClient.invalidateQueries({ queryKey: ["courses"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New course" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            subject_id: Number(values.subject_id),
            name: values.name,
            level: values.level,
            duration_weeks: values.duration_weeks,
            description: emptyToNull(values.description),
          }),
        )}
      >
        <CampusSelect
          register={register}
          error={errors.branch_id?.message}
          items={campuses.items}
        />
        <SelectField label="Subject" error={errors.subject_id?.message} {...register("subject_id")}>
          <option value="">Choose a subject</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </SelectField>
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField label="Level" error={errors.level?.message} {...register("level")} />
        <TextField
          label="Duration in weeks"
          type="number"
          error={errors.duration_weeks?.message}
          {...register("duration_weeks")}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save course
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SubjectForm({ onClose }) {
  const campuses = useCampusOptions();
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(subjectSchema),
    defaultValues: { branch_id: campuses.defaultId },
  });
  const mutation = useMutation({
    mutationFn: createSubject,
    onSuccess: () => {
      push({ tone: "success", message: "Subject created." });
      queryClient.invalidateQueries({ queryKey: ["subjects"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New subject" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            code: values.code,
            name: values.name,
          }),
        )}
      >
        <CampusSelect
          register={register}
          error={errors.branch_id?.message}
          items={campuses.items}
        />
        <TextField label="Code" error={errors.code?.message} {...register("code")} />
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save subject
          </Button>
        </div>
      </form>
    </Modal>
  );
}
