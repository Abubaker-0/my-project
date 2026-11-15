import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { forgotPassword } from "../../api/auth";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { errorMessage } from "../../utils/errors";
import { AuthShell } from "./AuthShell";

const schema = z.object({ email: z.string().email("Enter a valid email address") });

export function ForgotPasswordPage() {
  const [notice, setNotice] = useState("");
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  async function onSubmit(values) {
    try {
      const result = await forgotPassword(values.email);
      setNotice(result.message);
    } catch (error) {
      setError("root", { message: errorMessage(error) });
    }
  }

  return (
    <AuthShell
      title="Reset password"
      subtitle="We will send a one-time link if the account is active."
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <TextField
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.email?.message}
          {...register("email")}
        />
        {errors.root ? <p className="text-sm text-danger">{errors.root.message}</p> : null}
        {notice ? (
          <p className="rounded-xl bg-pine-50 px-4 py-3 text-sm text-pine-900">{notice}</p>
        ) : null}
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Sending" : "Send reset link"}
        </Button>
      </form>
      <p className="mt-4 text-sm">
        <Link className="text-pine-700" to="/login">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}
