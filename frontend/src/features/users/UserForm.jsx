import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createUser, listBranches, listRoles } from "../../api/resources";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { SelectField } from "../../components/SelectField";
import { TextField } from "../../components/TextField";
import { useAuthStore } from "../../store/authStore";
import { useToastStore } from "../../store/toastStore";
import { errorMessage, fieldErrors } from "../../utils/errors";
import { passwordSchema } from "../auth/passwordSchema";

function buildSchema(allBranches) {
  return z
    .object({
      full_name: z.string().min(2, "Enter the full name").max(200),
      email: z.string().email("Enter a valid email address"),
      phone: z.string().max(32).optional(),
      password: passwordSchema,
      role_id: z.string().min(1, "Choose a role"),
      branch_id: z.string(),
    })
    .superRefine((value, context) => {
      if (!allBranches && !value.branch_id) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["branch_id"],
          message: "Choose a branch",
        });
      }
    });
}

export function UserForm({ onClose }) {
  const allBranches = useAuthStore((state) => state.user?.all_branches);
  const schema = buildSchema(Boolean(allBranches));
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const roles = useQuery({
    queryKey: ["roles", "options"],
    queryFn: () => listRoles({ page_size: 100, sort: "name" }),
  });
  const branches = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => listBranches(),
  });
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { phone: "", branch_id: "" },
  });
  const mutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      push({ tone: "success", message: "User created." });
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (error) => {
      const fields = fieldErrors(error);
      Object.entries(fields).forEach(([field, message]) => setError(field, { message }));
      if (!Object.keys(fields).length) {
        push({ tone: "danger", message: errorMessage(error) });
      }
    },
  });

  function onSubmit(values) {
    mutation.mutate({
      full_name: values.full_name,
      email: values.email,
      phone: values.phone || null,
      password: values.password,
      assignments: [
        {
          role_id: Number(values.role_id),
          branch_id: values.branch_id ? Number(values.branch_id) : null,
        },
      ],
    });
  }

  return (
    <Modal title="New user" onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <TextField label="Full name" error={errors.full_name?.message} {...register("full_name")} />
        <TextField
          label="Email"
          type="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <TextField label="Phone" error={errors.phone?.message} {...register("phone")} />
        <TextField
          label="Temporary password"
          type="password"
          error={errors.password?.message}
          {...register("password")}
        />
        <SelectField label="Role" error={errors.role_id?.message} {...register("role_id")}>
          <option value="">Choose a role</option>
          {(roles.data?.items ?? []).map((role) => (
            <option key={role.id} value={role.id}>
              {role.label}
            </option>
          ))}
        </SelectField>
        <SelectField label="Branch" error={errors.branch_id?.message} {...register("branch_id")}>
          {allBranches ? (
            <option value="">All branches</option>
          ) : (
            <option value="">Choose a branch</option>
          )}
          {(branches.data?.items ?? []).map((branch) => (
            <option key={branch.id} value={branch.id}>
              {branch.name}
            </option>
          ))}
        </SelectField>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving" : "Create user"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
