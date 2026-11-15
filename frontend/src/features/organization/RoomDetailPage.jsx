import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { getRoom, updateRoom } from "../../api/resources";
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
import { reportError } from "../records/form";

const schema = z.object({
  name: z.string().min(1).max(100),
  capacity: z.coerce.number().int().min(1).max(10000),
  status: z.enum(["active", "inactive"]),
});

export function RoomDetailPage() {
  const { roomId } = useParams();
  const canUpdate = usePermission("rooms:update");
  const query = useQuery({ queryKey: ["rooms", roomId], queryFn: () => getRoom(roomId) });
  if (query.isLoading) return <Spinner label="Loading room" />;
  if (query.isError) {
    return <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  }
  const room = query.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Room"
        title={room.name}
        description={`Holds ${room.capacity} people`}
        actions={<Badge tone={statusTone(room.status)}>{room.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/rooms">
          Back to rooms
        </Link>
      </p>
      <Editor room={room} canUpdate={canUpdate} />
    </div>
  );
}

function Editor({ room, canUpdate }) {
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
    reset({ name: room.name, capacity: room.capacity, status: room.status });
  }, [room, reset]);
  const mutation = useMutation({
    mutationFn: (payload) => updateRoom(room.id, payload),
    onSuccess: () => {
      push({ tone: "success", message: "Room updated." });
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Panel title="Details">
      <form
        className="grid max-w-lg gap-3"
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
      >
        <TextField
          label="Name"
          disabled={!canUpdate}
          error={errors.name?.message}
          {...register("name")}
        />
        <TextField
          label="Capacity"
          type="number"
          disabled={!canUpdate}
          error={errors.capacity?.message}
          {...register("capacity")}
        />
        <SelectField label="Status" disabled={!canUpdate} {...register("status")}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </SelectField>
        {canUpdate ? (
          <div className="flex justify-end">
            <Button type="submit" disabled={mutation.isPending}>
              Save room
            </Button>
          </div>
        ) : null}
      </form>
    </Panel>
  );
}
