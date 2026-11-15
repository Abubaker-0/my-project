import { zodResolver } from "@hookform/resolvers/zod";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  cancelSession,
  createSession,
  getBatch,
  listBatches,
  listRooms,
  listSessions,
} from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { SelectField } from "../../components/SelectField";
import { TextField } from "../../components/TextField";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { calendarDay, weekdayName } from "../../utils/format";
import { reportError } from "../records/form";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const schema = z.object({
  batch_id: z.string().min(1, "Choose a batch"),
  room_id: z.string().optional(),
  staff_id: z.string().optional(),
  weekday: z.string().min(1, "Choose a day"),
  start_time: z.string().min(1, "Choose a start time"),
  end_time: z.string().min(1, "Choose an end time"),
});

export function TimetablePage() {
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("timetable:create");
  const canCancel = usePermission("timetable:delete");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["class-sessions"],
    queryFn: () => listSessions({ page_size: 100, sort: "weekday" }),
  });
  const cancel = useMutation({
    mutationFn: cancelSession,
    onSuccess: () => {
      push({ tone: "success", message: "Session cancelled. The room is free." });
      queryClient.invalidateQueries({ queryKey: ["class-sessions"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  const sessions = query.data?.items ?? [];
  const events = sessions
    .filter((session) => session.status === "scheduled")
    .map((session) => ({
      id: String(session.id),
      title: `${session.batch_name}${session.room_name ? ` · ${session.room_name}` : ""}`,
      daysOfWeek: [calendarDay(session.weekday)],
      startTime: String(session.start_time).slice(0, 5),
      endTime: String(session.end_time).slice(0, 5),
    }));

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Academics"
        title="Timetable"
        description="A room and a teacher can each hold one session at a time. Cancelling a slot keeps the record and frees both."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New session</Button> : null}
      />
      <div className="rounded-2xl border border-line bg-card p-4 shadow-card">
        <FullCalendar
          plugins={[timeGridPlugin]}
          initialView="timeGridWeek"
          headerToolbar={false}
          allDaySlot={false}
          slotMinTime="08:00:00"
          slotMaxTime="21:00:00"
          height={640}
          events={events}
          dayHeaderFormat={{ weekday: "short" }}
        />
      </div>
      <DataTable
        columns={[
          { key: "batch_name", header: "Batch" },
          { key: "weekday", header: "Day", render: (row) => weekdayName(row.weekday) },
          {
            key: "time",
            header: "Time",
            render: (row) =>
              `${String(row.start_time).slice(0, 5)}–${String(row.end_time).slice(0, 5)}`,
          },
          { key: "room_name", header: "Room", render: (row) => row.room_name || "—" },
          { key: "teacher_name", header: "Teacher", render: (row) => row.teacher_name || "—" },
          {
            key: "status",
            header: "Status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
          {
            key: "cancel",
            header: "",
            render: (row) =>
              canCancel && row.status === "scheduled" ? (
                <Button variant="secondary" onClick={() => cancel.mutate(row.id)}>
                  Cancel
                </Button>
              ) : null,
          },
        ]}
        rows={sessions}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No sessions"
        emptyBody="Add the first weekly slot for a batch."
        page={1}
        pageSize={100}
        total={query.data?.total}
        onPage={() => {}}
      />
      {creating ? <SessionForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function SessionForm({ onClose }) {
  const batches = useQuery({
    queryKey: ["batches", "options"],
    queryFn: () => listBatches({ page_size: 100, sort: "name" }),
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
    defaultValues: { room_id: "", staff_id: "", weekday: "0" },
  });
  const batchId = watch("batch_id");
  const batch = useQuery({
    queryKey: ["batches", batchId],
    queryFn: () => getBatch(batchId),
    enabled: Boolean(batchId),
  });
  const mutation = useMutation({
    mutationFn: createSession,
    onSuccess: () => {
      push({ tone: "success", message: "Session added." });
      queryClient.invalidateQueries({ queryKey: ["class-sessions"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New session" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            batch_id: Number(values.batch_id),
            room_id: values.room_id ? Number(values.room_id) : null,
            staff_id: values.staff_id ? Number(values.staff_id) : null,
            weekday: Number(values.weekday),
            start_time: values.start_time,
            end_time: values.end_time,
          }),
        )}
      >
        <SelectField label="Batch" error={errors.batch_id?.message} {...register("batch_id")}>
          <option value="">Choose a batch</option>
          {(batches.data?.items ?? []).map((batchOption) => (
            <option key={batchOption.id} value={batchOption.id}>
              {batchOption.name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Room" {...register("room_id")}>
          <option value="">No room</option>
          {(rooms.data?.items ?? []).map((room) => (
            <option key={room.id} value={room.id}>
              {room.name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Teacher" {...register("staff_id")}>
          <option value="">No teacher</option>
          {(batch.data?.teachers ?? []).map((teacher) => (
            <option key={teacher.staff_id} value={teacher.staff_id}>
              {teacher.full_name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Day" error={errors.weekday?.message} {...register("weekday")}>
          {WEEKDAYS.map((name, index) => (
            <option key={name} value={index}>
              {name}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Starts"
          type="time"
          error={errors.start_time?.message}
          {...register("start_time")}
        />
        <TextField
          label="Ends"
          type="time"
          error={errors.end_time?.message}
          {...register("end_time")}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save session
          </Button>
        </div>
      </form>
    </Modal>
  );
}
