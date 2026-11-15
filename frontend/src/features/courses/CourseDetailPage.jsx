import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { getCourse, listBatches, updateCourse } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { PageHeader } from "../../components/PageHeader";
import { Panel } from "../../components/Panel";
import { SelectField } from "../../components/SelectField";
import { Spinner } from "../../components/Spinner";
import { TextArea } from "../../components/TextArea";
import { TextField } from "../../components/TextField";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { emptyToNull, reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  name: z.string().min(2).max(200),
  level: z.string().min(1).max(64),
  duration_weeks: z.coerce.number().int().min(1).max(104),
  status: z.enum(["active", "inactive"]),
  description: z.string().max(4000),
});

export function CourseDetailPage() {
  const { courseId } = useParams();
  const canUpdate = usePermission("courses:update");
  const course = useQuery({ queryKey: ["courses", courseId], queryFn: () => getCourse(courseId) });
  const batches = useQuery({
    queryKey: ["batches", "course", courseId],
    queryFn: () => listBatches({ page_size: 100, sort: "name" }),
  });
  if (course.isLoading) return <Spinner label="Loading course" />;
  if (course.isError) {
    return <ErrorState body={errorMessage(course.error)} onRetry={() => course.refetch()} />;
  }
  const record = course.data;
  const related = (batches.data?.items ?? []).filter((batch) => batch.course_id === record.id);
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={record.subject_name}
        title={record.name}
        description={`${record.level} · ${record.duration_weeks} weeks`}
        actions={<Badge tone={statusTone(record.status)}>{record.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/courses">
          Back to courses
        </Link>
      </p>
      <Editor course={record} canUpdate={canUpdate} />
      <Panel title="Batches">
        <ul className="space-y-2 text-sm">
          {related.length === 0 ? <li>No batches use this course yet.</li> : null}
          {related.map((batch) => (
            <li key={batch.id}>
              <RecordLink to={`/batches/${batch.id}`}>{batch.name}</RecordLink>
              <span className="text-ink-500">
                {" "}
                · {batch.active_count}/{batch.capacity} · {batch.status}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function Editor({ course, canUpdate }) {
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });
  useEffect(() => {
    reset({
      name: course.name,
      level: course.level,
      duration_weeks: course.duration_weeks,
      status: course.status,
      description: course.description || "",
    });
  }, [course, reset]);
  const mutation = useMutation({
    mutationFn: (payload) => updateCourse(course.id, payload),
    onSuccess: () => {
      push({ tone: "success", message: "Course updated." });
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Panel title="Details">
      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({ ...values, description: emptyToNull(values.description) }),
        )}
      >
        <TextField
          label="Name"
          disabled={!canUpdate}
          error={errors.name?.message}
          {...register("name")}
        />
        <TextField
          label="Level"
          disabled={!canUpdate}
          error={errors.level?.message}
          {...register("level")}
        />
        <TextField
          label="Weeks"
          type="number"
          disabled={!canUpdate}
          error={errors.duration_weeks?.message}
          {...register("duration_weeks")}
        />
        <SelectField label="Status" disabled={!canUpdate} {...register("status")}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </SelectField>
        <div className="sm:col-span-2">
          <TextArea label="Description" disabled={!canUpdate} {...register("description")} />
        </div>
        {canUpdate ? (
          <div className="sm:col-span-2 flex justify-end">
            <Button type="submit" disabled={mutation.isPending}>
              Save course
            </Button>
          </div>
        ) : null}
      </form>
    </Panel>
  );
}
