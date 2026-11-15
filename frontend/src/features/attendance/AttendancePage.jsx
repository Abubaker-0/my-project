import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getAttendance, listBatches, saveAttendance } from "../../api/resources";
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

function todayInput() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

export function AttendancePage() {
  const canMark = usePermission("attendance:mark");
  const [batchId, setBatchId] = useState("");
  const [attendedOn, setAttendedOn] = useState(todayInput);
  const [marks, setMarks] = useState({});
  const batches = useQuery({
    queryKey: ["batches", "options"],
    queryFn: () => listBatches({ page_size: 100, sort: "name" }),
  });
  const roster = useQuery({
    queryKey: ["attendance", batchId, attendedOn],
    queryFn: () => getAttendance(batchId, attendedOn),
    enabled: Boolean(batchId && attendedOn),
  });
  useEffect(() => {
    const next = {};
    for (const row of roster.data?.marks ?? []) {
      next[row.student_id] = { status: row.status || "present", note: row.note || "" };
    }
    setMarks(next);
  }, [roster.data]);
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: () =>
      saveAttendance({
        batch_id: Number(batchId),
        attended_on: attendedOn,
        marks: (roster.data?.marks ?? []).map((row) => ({
          student_id: row.student_id,
          status: marks[row.student_id]?.status || "present",
          note: marks[row.student_id]?.note || null,
        })),
      }),
    onSuccess: () => {
      push({ tone: "success", message: "Attendance saved." });
      queryClient.invalidateQueries({ queryKey: ["attendance", batchId, attendedOn] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Academics"
        title="Attendance"
        description="Mark the active students in a batch for one date. A teacher can open only their own batches."
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <SelectField
          label="Batch"
          value={batchId}
          onChange={(event) => setBatchId(event.target.value)}
        >
          <option value="">Choose a batch</option>
          {(batches.data?.items ?? []).map((batch) => (
            <option key={batch.id} value={batch.id}>
              {batch.name}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Date"
          type="date"
          value={attendedOn}
          onChange={(event) => setAttendedOn(event.target.value)}
        />
      </div>
      {!batchId ? (
        <p className="text-sm text-ink-700">Choose a batch to load its register.</p>
      ) : null}
      {roster.isLoading ? <Spinner label="Loading register" /> : null}
      {roster.isError ? (
        <ErrorState body={errorMessage(roster.error)} onRetry={() => roster.refetch()} />
      ) : null}
      {roster.data ? (
        <Panel
          title={roster.data.batch_name}
          actions={
            canMark ? (
              <Button onClick={() => save.mutate()} disabled={save.isPending}>
                Save register
              </Button>
            ) : null
          }
        >
          <ul className="space-y-3">
            {roster.data.marks.map((row) => (
              <li
                key={row.student_id}
                className="grid gap-3 border-b border-line pb-3 sm:grid-cols-3"
              >
                <div>
                  <p className="font-medium">{row.student_name}</p>
                  <p className="text-sm text-ink-500">{row.admission_no}</p>
                </div>
                <SelectField
                  label="Status"
                  value={marks[row.student_id]?.status || "present"}
                  disabled={!canMark}
                  onChange={(event) =>
                    setMarks((current) => ({
                      ...current,
                      [row.student_id]: { ...current[row.student_id], status: event.target.value },
                    }))
                  }
                >
                  <option value="present">Present</option>
                  <option value="absent">Absent</option>
                  <option value="late">Late</option>
                  <option value="excused">Excused</option>
                </SelectField>
                <TextField
                  label="Note"
                  value={marks[row.student_id]?.note || ""}
                  disabled={!canMark}
                  onChange={(event) =>
                    setMarks((current) => ({
                      ...current,
                      [row.student_id]: { ...current[row.student_id], note: event.target.value },
                    }))
                  }
                />
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}
