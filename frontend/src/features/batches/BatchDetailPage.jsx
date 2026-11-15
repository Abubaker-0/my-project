import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  assignTeacher,
  getBatch,
  listEnrollments,
  listUsers,
  updateBatch,
  withdrawEnrollment,
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
import { formatDate, seatSummary } from "../../utils/format";
import { RecordLink } from "../records/RecordLink";

export function BatchDetailPage() {
  const { batchId } = useParams();
  const batch = useQuery({ queryKey: ["batches", batchId], queryFn: () => getBatch(batchId) });
  const roster = useQuery({
    queryKey: ["enrollments", "batch", batchId],
    queryFn: () => listEnrollments({ batch_id: batchId, page_size: 100, sort: "status" }),
  });
  if (batch.isLoading) return <Spinner label="Loading batch" />;
  if (batch.isError) {
    return <ErrorState body={errorMessage(batch.error)} onRetry={() => batch.refetch()} />;
  }
  const record = batch.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={record.course_name}
        title={record.name}
        description={`${record.term_name} · ${record.room_name || "No room"} · ${formatDate(record.start_date)} to ${formatDate(record.end_date)}`}
        actions={<Badge tone={statusTone(record.status)}>{record.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/batches">
          Back to batches
        </Link>
      </p>
      <Panel title="Seats">
        <p className="text-sm">
          {seatSummary(record.active_count, record.capacity, record.waitlist_count)}
        </p>
        <CapacityEditor batch={record} />
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Teachers batch={record} />
        <Roster batchId={record.id} query={roster} />
      </div>
    </div>
  );
}

function CapacityEditor({ batch }) {
  const canUpdate = usePermission("batches:update");
  const [capacity, setCapacity] = useState(String(batch.capacity));
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => updateBatch(batch.id, { capacity: Number(capacity) }),
    onSuccess: () => {
      push({ tone: "success", message: "Capacity updated." });
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  if (!canUpdate) return null;
  return (
    <form
      className="mt-4 flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <div className="w-32">
        <TextField
          label="Capacity"
          type="number"
          min="1"
          value={capacity}
          onChange={(event) => setCapacity(event.target.value)}
        />
      </div>
      <Button type="submit" variant="secondary" disabled={mutation.isPending}>
        Update seats
      </Button>
    </form>
  );
}

function Teachers({ batch }) {
  const canUpdate = usePermission("batches:update");
  const [userId, setUserId] = useState("");
  const users = useQuery({
    queryKey: ["users", "teachers"],
    queryFn: () => listUsers({ page_size: 100, sort: "full_name" }),
    enabled: canUpdate,
  });
  const teachers = (users.data?.items ?? []).filter((user) =>
    user.roles.some((role) => role.role_name === "teacher"),
  );
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      assignTeacher(batch.id, {
        user_id: Number(userId),
        role: batch.teachers.some((teacher) => teacher.role === "primary")
          ? "assistant"
          : "primary",
      }),
    onSuccess: () => {
      push({ tone: "success", message: "Teacher assigned." });
      setUserId("");
      queryClient.invalidateQueries({ queryKey: ["batches", String(batch.id)] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  return (
    <Panel title="Teachers">
      <ul className="space-y-2 text-sm">
        {batch.teachers.length === 0 ? <li>No teacher assigned.</li> : null}
        {batch.teachers.map((teacher) => (
          <li key={teacher.staff_id}>
            {teacher.full_name} · {teacher.role} · {teacher.employee_no}
          </li>
        ))}
      </ul>
      {canUpdate ? (
        <form
          className="mt-4 grid gap-3 border-t border-line pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (userId) mutation.mutate();
          }}
        >
          <SelectField
            label="Add a teacher"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
          >
            <option value="">Choose a teacher</option>
            {teachers.map((teacher) => (
              <option key={teacher.id} value={teacher.id}>
                {teacher.full_name}
              </option>
            ))}
          </SelectField>
          <div className="flex justify-end">
            <Button type="submit" variant="secondary" disabled={!userId || mutation.isPending}>
              Assign
            </Button>
          </div>
        </form>
      ) : null}
    </Panel>
  );
}

function Roster({ batchId, query }) {
  const canWithdraw = usePermission("enrollment:withdraw");
  const [reason, setReason] = useState("Family request");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (enrollmentId) => withdrawEnrollment(enrollmentId, reason),
    onSuccess: () => {
      push({
        tone: "success",
        message:
          "Seat released. The next waiting student moves up when the batch is still running.",
      });
      queryClient.invalidateQueries({ queryKey: ["enrollments", "batch", String(batchId)] });
      queryClient.invalidateQueries({ queryKey: ["batches"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  return (
    <Panel title="Roster">
      {query.isLoading ? <Spinner label="Loading roster" /> : null}
      {query.isError ? (
        <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />
      ) : null}
      <ul className="space-y-2 text-sm">
        {(query.data?.items ?? []).map((seat) => (
          <li key={seat.id} className="flex flex-wrap items-center justify-between gap-2">
            <span>
              <RecordLink to={`/students/${seat.student_id}`}>{seat.student_name}</RecordLink>
              <span className="text-ink-500"> · {seat.admission_no}</span>
              {seat.waitlist_position ? ` · waitlist ${seat.waitlist_position}` : ""}
            </span>
            <span className="flex items-center gap-2">
              <Badge tone={statusTone(seat.status)}>{seat.status}</Badge>
              {canWithdraw && (seat.status === "active" || seat.status === "waitlisted") ? (
                <Button
                  variant="secondary"
                  disabled={reason.trim().length < 2 || mutation.isPending}
                  onClick={() => mutation.mutate(seat.id)}
                >
                  Withdraw
                </Button>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
      {canWithdraw ? (
        <div className="mt-4 border-t border-line pt-4">
          <TextField
            label="Withdrawal reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>
      ) : null}
    </Panel>
  );
}
