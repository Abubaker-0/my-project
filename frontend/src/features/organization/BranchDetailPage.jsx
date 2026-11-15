import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { getBranch, updateBranch } from "../../api/resources";
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

const schema = z.object({
  name: z.string().min(2).max(200),
  phone: z.string().max(32),
  email: z.union([z.literal(""), z.string().email("Enter a valid email")]),
  address: z.string().max(2000),
  status: z.enum(["active", "inactive"]),
});

export function BranchDetailPage() {
  const { branchId } = useParams();
  const canUpdate = usePermission("branches:update");
  const query = useQuery({ queryKey: ["branches", branchId], queryFn: () => getBranch(branchId) });
  if (query.isLoading) return <Spinner label="Loading branch" />;
  if (query.isError) {
    return <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  }
  const branch = query.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={branch.code}
        title={branch.name}
        actions={<Badge tone={statusTone(branch.status)}>{branch.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/branches">
          Back to branches
        </Link>
      </p>
      <Editor branch={branch} canUpdate={canUpdate} />
    </div>
  );
}

function Editor({ branch, canUpdate }) {
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
      name: branch.name,
      phone: branch.phone || "",
      email: branch.email || "",
      address: branch.address || "",
      status: branch.status,
    });
  }, [branch, reset]);
  const mutation = useMutation({
    mutationFn: (values) =>
      updateBranch(branch.id, {
        name: values.name,
        phone: emptyToNull(values.phone),
        email: emptyToNull(values.email),
        address: emptyToNull(values.address),
        status: values.status,
      }),
    onSuccess: () => {
      push({ tone: "success", message: "Branch updated." });
      queryClient.invalidateQueries({ queryKey: ["branches"] });
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <Panel title="Campus details">
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
          label="Phone"
          disabled={!canUpdate}
          error={errors.phone?.message}
          {...register("phone")}
        />
        <TextField
          label="Email"
          disabled={!canUpdate}
          error={errors.email?.message}
          {...register("email")}
        />
        <TextArea label="Address" disabled={!canUpdate} {...register("address")} />
        <SelectField label="Status" disabled={!canUpdate} {...register("status")}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </SelectField>
        {canUpdate ? (
          <div className="flex justify-end">
            <Button type="submit" disabled={mutation.isPending}>
              Save branch
            </Button>
          </div>
        ) : null}
      </form>
    </Panel>
  );
}
