import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { resetPassword } from "../../api/auth";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { AuthShell } from "./AuthShell";
import { passwordSchema } from "./passwordSchema";

const schema = z
  .object({
    password: passwordSchema,
    confirm: z.string().min(1, "Confirm the new password"),
  })
  .refine((value) => value.password === value.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const push = useToastStore((state) => state.push);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  async function onSubmit(values) {
    try {
      await resetPassword({ token, password: values.password });
      push({ tone: "success", message: "Password updated. Sign in with the new password." });
      navigate("/login");
    } catch (error) {
      setError("root", { message: errorMessage(error) });
    }
  }

  return (
    <AuthShell title="Choose a new password" subtitle="This link works once.">
      {token ? (
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <TextField
            label="New password"
            type="password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...register("password")}
          />
          <TextField
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            error={errors.confirm?.message}
            {...register("confirm")}
          />
          {errors.root ? <p className="text-sm text-danger">{errors.root.message}</p> : null}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Saving" : "Update password"}
          </Button>
        </form>
      ) : (
        <p className="text-sm text-ink-700">
          This reset link is missing its token. Request a new one.
        </p>
      )}
      <p className="mt-4 text-sm">
        <Link className="text-pine-700" to="/forgot-password">
          Request a new link
        </Link>
      </p>
    </AuthShell>
  );
}
