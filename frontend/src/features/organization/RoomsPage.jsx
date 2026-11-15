import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createRoom, listRooms } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { TextField } from "../../components/TextField";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  name: z.string().min(1, "Enter a name").max(100),
  capacity: z.coerce.number().int().min(1).max(10000),
});

export function RoomsPage() {
  const paging = usePagination({ sort: "name" });
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("rooms:create");
  const query = useQuery({
    queryKey: ["rooms", paging.page, paging.sort],
    queryFn: () => listRooms({ page: paging.page, page_size: paging.pageSize, sort: paging.sort }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Campus"
        title="Rooms"
        description="Rooms are where batches meet. Capacity here is the physical limit, separate from a batch's seat count."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New room</Button> : null}
      />
      <DataTable
        columns={[
          {
            key: "name",
            header: "Room",
            sortKey: "name",
            render: (row) => <RecordLink to={`/rooms/${row.id}`}>{row.name}</RecordLink>,
          },
          { key: "capacity", header: "Capacity", sortKey: "capacity" },
          {
            key: "status",
            header: "Status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No rooms"
        emptyBody="Add a classroom before you schedule a batch in it."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <RoomForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function RoomForm({ onClose }) {
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
    defaultValues: { branch_id: campuses.defaultId, capacity: 20 },
  });
  const mutation = useMutation({
    mutationFn: createRoom,
    onSuccess: () => {
      push({ tone: "success", message: "Room created." });
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Modal title="New room" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            name: values.name,
            capacity: values.capacity,
          }),
        )}
      >
        <CampusSelect
          register={register}
          error={errors.branch_id?.message}
          items={campuses.items}
        />
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField
          label="Capacity"
          type="number"
          error={errors.capacity?.message}
          {...register("capacity")}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save room
          </Button>
        </div>
      </form>
    </Modal>
  );
}
