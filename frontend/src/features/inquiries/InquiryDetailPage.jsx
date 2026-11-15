import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import {
  addFollowup,
  convertInquiry,
  getInquiry,
  listBatches,
  updateInquiry,
} from "../../api/resources";
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
import { formatDate, formatDateTime } from "../../utils/format";
import { emptyToNull, reportError } from "../records/form";

const followupSchema = z.object({
  note: z.string().min(1, "Write a note").max(4000),
  next_date: z.string().optional(),
});

export function InquiryDetailPage() {
  const { inquiryId } = useParams();
  const query = useQuery({
    queryKey: ["inquiries", inquiryId],
    queryFn: () => getInquiry(inquiryId),
  });
  if (query.isLoading) return <Spinner label="Loading inquiry" />;
  if (query.isError) {
    return <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  }
  const inquiry = query.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Inquiry"
        title={inquiry.name}
        description={inquiry.course_name || "No course chosen yet"}
        actions={<Badge tone={statusTone(inquiry.status)}>{inquiry.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/inquiries">
          Back to inquiries
        </Link>
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <StatusPanel inquiry={inquiry} />
        <ConvertPanel inquiry={inquiry} />
      </div>
      <Followups inquiry={inquiry} />
    </div>
  );
}

function StatusPanel({ inquiry }) {
  const canUpdate = usePermission("inquiries:update");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const [status, setStatus] = useState(
    inquiry.status === "converted" ? "converted" : inquiry.status,
  );
  const mutation = useMutation({
    mutationFn: () => updateInquiry(inquiry.id, { status }),
    onSuccess: () => {
      push({ tone: "success", message: "Inquiry updated." });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  return (
    <Panel title="Lead">
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-ink-500">Phone</dt>
          <dd>{inquiry.phone || "—"}</dd>
        </div>
        <div>
          <dt className="text-ink-500">Email</dt>
          <dd>{inquiry.email || "—"}</dd>
        </div>
        <div>
          <dt className="text-ink-500">Source</dt>
          <dd>{inquiry.source.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt className="text-ink-500">Notes</dt>
          <dd>{inquiry.notes || "—"}</dd>
        </div>
      </dl>
      {canUpdate && inquiry.status !== "converted" ? (
        <form
          className="mt-4 grid gap-3 border-t border-line pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <SelectField
            label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="lost">Lost</option>
          </SelectField>
          <div className="flex justify-end">
            <Button type="submit" disabled={mutation.isPending}>
              Save status
            </Button>
          </div>
        </form>
      ) : null}
    </Panel>
  );
}

function ConvertPanel({ inquiry }) {
  const canConvert = usePermission("inquiries:convert");
  const navigate = useNavigate();
  const [grade, setGrade] = useState("");
  const [batchId, setBatchId] = useState("");
  const batches = useQuery({
    queryKey: ["batches", "options", inquiry.branch_id],
    queryFn: () => listBatches({ page_size: 100, sort: "name" }),
    enabled: canConvert && inquiry.status !== "converted",
  });
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      convertInquiry(inquiry.id, {
        grade_level: emptyToNull(grade),
        batch_id: batchId ? Number(batchId) : null,
      }),
    onSuccess: (student) => {
      push({ tone: "success", message: `${student.full_name} is now a student.` });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
      navigate(`/students/${student.id}`);
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });

  if (inquiry.converted_student_id) {
    return (
      <Panel title="Admission">
        <p className="text-sm">
          This lead is already a student.{" "}
          <Link className="text-pine-800" to={`/students/${inquiry.converted_student_id}`}>
            Open the record
          </Link>
        </p>
      </Panel>
    );
  }
  return (
    <Panel title="Convert to a student">
      <p className="mb-3 text-sm text-ink-700">
        A lost lead has to be reopened before it can be admitted. A full batch places the new
        student on the waitlist.
      </p>
      {canConvert ? (
        <form
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <TextField
            label="Grade"
            value={grade}
            onChange={(event) => setGrade(event.target.value)}
          />
          <SelectField
            label="Batch"
            value={batchId}
            onChange={(event) => setBatchId(event.target.value)}
          >
            <option value="">Do not enroll yet</option>
            {(batches.data?.items ?? []).map((batch) => (
              <option key={batch.id} value={batch.id}>
                {batch.name} · {batch.active_count}/{batch.capacity}
              </option>
            ))}
          </SelectField>
          <div className="flex justify-end">
            <Button type="submit" disabled={inquiry.status === "lost" || mutation.isPending}>
              Convert
            </Button>
          </div>
        </form>
      ) : (
        <p className="text-sm text-ink-700">You can view this lead but not admit it.</p>
      )}
    </Panel>
  );
}

function Followups({ inquiry }) {
  const canUpdate = usePermission("inquiries:update");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(followupSchema),
    defaultValues: { note: "", next_date: "" },
  });
  const mutation = useMutation({
    mutationFn: (payload) => addFollowup(inquiry.id, payload),
    onSuccess: () => {
      push({ tone: "success", message: "Follow-up saved." });
      reset();
      queryClient.invalidateQueries({ queryKey: ["inquiries", String(inquiry.id)] });
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Panel title="Follow-ups">
      <ul className="space-y-3">
        {inquiry.followups.length === 0 ? (
          <li className="text-sm text-ink-700">No notes yet.</li>
        ) : (
          inquiry.followups.map((item) => (
            <li key={item.id} className="rounded-xl border border-line px-3 py-2 text-sm">
              <p>{item.note}</p>
              <p className="mt-1 text-ink-500">
                {formatDateTime(item.created_at)}
                {item.next_date ? ` · next ${formatDate(item.next_date)}` : ""}
              </p>
            </li>
          ))
        )}
      </ul>
      {canUpdate && inquiry.status !== "converted" ? (
        <form
          className="mt-4 grid gap-3 border-t border-line pt-4"
          onSubmit={handleSubmit((values) =>
            mutation.mutate({
              note: values.note,
              next_date: emptyToNull(values.next_date),
            }),
          )}
        >
          <TextArea label="Note" error={errors.note?.message} {...register("note")} />
          <TextField label="Next date" type="date" {...register("next_date")} />
          <div className="flex justify-end">
            <Button type="submit" disabled={mutation.isPending}>
              Add follow-up
            </Button>
          </div>
        </form>
      ) : null}
    </Panel>
  );
}
