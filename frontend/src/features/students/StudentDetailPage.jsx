import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import {
  addGuardian,
  createEnrollment,
  downloadDocument,
  getStudent,
  listBatches,
  listEnrollments,
  updateStudent,
  uploadDocument,
} from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { PageHeader } from "../../components/PageHeader";
import { Panel } from "../../components/Panel";
import { SelectField } from "../../components/SelectField";
import { Spinner } from "../../components/Spinner";
import { TextField } from "../../components/TextField";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import { emptyToNull, reportError } from "../records/form";

const profileSchema = z.object({
  first_name: z.string().min(1, "Enter a first name").max(100),
  last_name: z.string().min(1, "Enter a last name").max(100),
  gender: z.enum(["female", "male", "other", "unspecified"]),
  grade_level: z.string().max(64),
  school_name: z.string().max(200),
  status: z.enum(["active", "graduated", "dropped", "suspended"]),
});

const guardianSchema = z.object({
  full_name: z.string().min(2, "Enter a name").max(200),
  relationship: z.string().min(2, "Enter a relationship").max(64),
  phone: z.string().max(32).optional(),
  email: z.union([z.literal(""), z.string().email("Enter a valid email")]),
});

export function StudentDetailPage() {
  const { studentId } = useParams();
  const query = useQuery({
    queryKey: ["students", studentId],
    queryFn: () => getStudent(studentId),
  });
  const seats = useQuery({
    queryKey: ["enrollments", "student", studentId],
    queryFn: () => listEnrollments({ student_id: studentId, page_size: 100, sort: "enrolled_on" }),
    enabled: usePermission("enrollment:read"),
  });

  if (query.isLoading) {
    return <Spinner label="Loading student" />;
  }
  if (query.isError) {
    return <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  }
  const student = query.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={student.admission_no}
        title={student.full_name}
        description={`Admitted ${formatDate(student.admission_date)}`}
        actions={<Badge tone={statusTone(student.status)}>{student.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/students">
          Back to students
        </Link>
      </p>
      <ProfileForm student={student} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Guardians student={student} />
        <Documents student={student} />
      </div>
      <Seats studentId={student.id} query={seats} />
    </div>
  );
}

function ProfileForm({ student }) {
  const canUpdate = usePermission("students:update");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm({ resolver: zodResolver(profileSchema) });
  useEffect(() => {
    reset({
      first_name: student.first_name,
      last_name: student.last_name,
      gender: student.gender,
      grade_level: student.grade_level || "",
      school_name: student.school_name || "",
      status: student.status,
    });
  }, [student, reset]);
  const mutation = useMutation({
    mutationFn: (payload) => updateStudent(student.id, payload),
    onSuccess: () => {
      push({ tone: "success", message: "Student updated." });
      queryClient.invalidateQueries({ queryKey: ["students"] });
    },
    onError: (error) => reportError(error, setError, push),
  });

  return (
    <Panel title="Profile">
      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            ...values,
            grade_level: emptyToNull(values.grade_level),
            school_name: emptyToNull(values.school_name),
          }),
        )}
      >
        <TextField
          label="First name"
          disabled={!canUpdate}
          error={errors.first_name?.message}
          {...register("first_name")}
        />
        <TextField
          label="Last name"
          disabled={!canUpdate}
          error={errors.last_name?.message}
          {...register("last_name")}
        />
        <SelectField label="Gender" disabled={!canUpdate} {...register("gender")}>
          <option value="unspecified">Unspecified</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="other">Other</option>
        </SelectField>
        <SelectField label="Status" disabled={!canUpdate} {...register("status")}>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="graduated">Graduated</option>
          <option value="dropped">Dropped</option>
        </SelectField>
        <TextField label="Grade" disabled={!canUpdate} {...register("grade_level")} />
        <TextField label="School" disabled={!canUpdate} {...register("school_name")} />
        {canUpdate ? (
          <div className="sm:col-span-2 flex justify-end">
            <Button type="submit" disabled={mutation.isPending}>
              Save profile
            </Button>
          </div>
        ) : null}
      </form>
    </Panel>
  );
}

function Guardians({ student }) {
  const canUpdate = usePermission("students:update");
  const [open, setOpen] = useState(false);
  return (
    <Panel
      title="Guardians"
      actions={
        canUpdate ? (
          <Button variant="secondary" onClick={() => setOpen(true)}>
            Add guardian
          </Button>
        ) : null
      }
    >
      {student.guardians.length === 0 ? (
        <p className="text-sm text-ink-700">No guardian is linked yet.</p>
      ) : (
        <ul className="space-y-3">
          {student.guardians.map((guardian) => (
            <li key={guardian.id} className="rounded-xl border border-line px-3 py-2 text-sm">
              <p className="font-medium">
                {guardian.full_name}
                {guardian.is_primary ? " · primary" : ""}
              </p>
              <p className="text-ink-700">
                {guardian.relationship}
                {guardian.phone ? ` · ${guardian.phone}` : ""}
                {guardian.email ? ` · ${guardian.email}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
      {open ? <GuardianForm studentId={student.id} onClose={() => setOpen(false)} /> : null}
    </Panel>
  );
}

function GuardianForm({ studentId, onClose }) {
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(guardianSchema),
    defaultValues: { relationship: "Parent", email: "", phone: "" },
  });
  const mutation = useMutation({
    mutationFn: (payload) => addGuardian(studentId, payload),
    onSuccess: () => {
      push({ tone: "success", message: "Guardian added." });
      queryClient.invalidateQueries({ queryKey: ["students", String(studentId)] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <div className="mt-4 border-t border-line pt-4">
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            full_name: values.full_name,
            relationship: values.relationship,
            phone: emptyToNull(values.phone),
            email: emptyToNull(values.email),
            is_primary: false,
          }),
        )}
      >
        <TextField label="Name" error={errors.full_name?.message} {...register("full_name")} />
        <TextField
          label="Relationship"
          error={errors.relationship?.message}
          {...register("relationship")}
        />
        <TextField label="Phone" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Email" error={errors.email?.message} {...register("email")} />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            Save guardian
          </Button>
        </div>
      </form>
    </div>
  );
}

function Documents({ student }) {
  const canUpload = usePermission("documents:create");
  const [docType, setDocType] = useState("other");
  const [file, setFile] = useState(null);
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => uploadDocument(student.id, file, docType),
    onSuccess: () => {
      push({ tone: "success", message: "Document stored." });
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["students", String(student.id)] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });

  return (
    <Panel title="Documents">
      {student.documents.length === 0 ? (
        <p className="text-sm text-ink-700">No files uploaded.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {student.documents.map((document) => (
            <li key={document.id}>
              <button
                type="button"
                className="text-pine-800 underline-offset-2 hover:underline"
                onClick={() => downloadDocument(student.id, document.id, document.file_name)}
              >
                {document.file_name}
              </button>
              <span className="text-ink-500"> · {document.doc_type.replaceAll("_", " ")}</span>
            </li>
          ))}
        </ul>
      )}
      {canUpload ? (
        <form
          className="mt-4 grid gap-3 border-t border-line pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (file) mutation.mutate();
          }}
        >
          <SelectField
            label="Type"
            value={docType}
            onChange={(event) => setDocType(event.target.value)}
          >
            <option value="birth_certificate">Birth certificate</option>
            <option value="photo">Photo</option>
            <option value="report">Report</option>
            <option value="id_copy">ID copy</option>
            <option value="other">Other</option>
          </SelectField>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">File</span>
            <input
              className="block w-full text-sm"
              type="file"
              accept="application/pdf,image/jpeg,image/png,image/webp"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="flex justify-end">
            <Button type="submit" disabled={!file || mutation.isPending}>
              Upload
            </Button>
          </div>
        </form>
      ) : null}
    </Panel>
  );
}

function Seats({ studentId, query }) {
  const canRead = usePermission("enrollment:read");
  const canEnroll = usePermission("enrollment:create");
  const [batchId, setBatchId] = useState("");
  const batches = useQuery({
    queryKey: ["batches", "options"],
    queryFn: () => listBatches({ page_size: 100, sort: "name" }),
    enabled: canEnroll,
  });
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      createEnrollment({ student_id: Number(studentId), batch_id: Number(batchId) }),
    onSuccess: (seat) => {
      push({
        tone: "success",
        message: seat.status === "waitlisted" ? "Added to the waitlist." : "Seat confirmed.",
      });
      setBatchId("");
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      queryClient.invalidateQueries({ queryKey: ["batches"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  if (!canRead) return null;
  return (
    <Panel title="Enrollment">
      {query.isLoading ? <Spinner label="Loading seats" /> : null}
      {query.isError ? (
        <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />
      ) : null}
      <ul className="space-y-2 text-sm">
        {(query.data?.items ?? []).map((seat) => (
          <li key={seat.id} className="flex flex-wrap items-center justify-between gap-2">
            <span>
              {seat.batch_name} · {seat.course_name}
              {seat.waitlist_position ? ` · waitlist ${seat.waitlist_position}` : ""}
            </span>
            <Badge tone={statusTone(seat.status)}>{seat.status}</Badge>
          </li>
        ))}
      </ul>
      {canEnroll ? (
        <form
          className="mt-4 flex flex-wrap items-end gap-3 border-t border-line pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (batchId) mutation.mutate();
          }}
        >
          <div className="min-w-56 flex-1">
            <SelectField
              label="Batch"
              value={batchId}
              onChange={(event) => setBatchId(event.target.value)}
            >
              <option value="">Choose a batch</option>
              {(batches.data?.items ?? []).map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.name} · {batch.active_count}/{batch.capacity}
                </option>
              ))}
            </SelectField>
          </div>
          <Button type="submit" disabled={!batchId || mutation.isPending}>
            Enroll
          </Button>
        </form>
      ) : null}
    </Panel>
  );
}
