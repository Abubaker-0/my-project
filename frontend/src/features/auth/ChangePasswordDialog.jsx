import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { changePassword } from "../../api/auth";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { TextField } from "../../components/TextField";
import { useAuthStore } from "../../store/authStore";
import { useToastStore } from "../../store/toastStore";
import { errorMessage, fieldErrors } from "../../utils/errors";
import { passwordSchema } from "./passwordSchema";

const schema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: passwordSchema,
    confirm: z.string().min(1, "Confirm the new password"),
  })
  .refine((value) => value.new_password === value.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });

export function ChangePasswordDialog({ onClose }) {
  const clear = useAuthStore((state) => state.clear);
  const push = useToastStore((state) => state.push);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  async function onSubmit(values) {
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      push({ tone: "success", message: "Password updated. Sign in again." });
      clear();
    } catch (error) {
      const fields = fieldErrors(error);
      Object.entries(fields).forEach(([field, message]) => setError(field, { message }));
      if (!Object.keys(fields).length) {
        push({ tone: "danger", message: errorMessage(error) });
      }
    }
  }

  return (
    <Modal title="Change password" onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <TextField
          label="Current password"
          type="password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...register("current_password")}
        />
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <TextField
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm?.message}
          {...register("confirm")}
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving" : "Update password"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
