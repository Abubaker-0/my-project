import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { fetchMe, login } from "../../api/auth";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { useAuthStore } from "../../store/authStore";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { AuthShell } from "./AuthShell";
import { loginSchema } from "./passwordSchema";

export function LoginPage() {
  const status = useAuthStore((state) => state.status);
  const setSession = useAuthStore((state) => state.setSession);
  const push = useToastStore((state) => state.push);
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(loginSchema) });

  if (status === "authenticated") {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(values) {
    try {
      const tokens = await login(values);
      const user = await fetchMe(tokens.access_token);
      setSession({ accessToken: tokens.access_token, user });
      navigate("/");
    } catch (error) {
      push({ tone: "danger", message: errorMessage(error) });
    }
  }

  return (
    <AuthShell title="Sign in" subtitle="Use the account issued by your centre.">
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <TextField
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.email?.message}
          {...register("email")}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in" : "Sign in"}
        </Button>
      </form>
      <p className="mt-4 text-sm">
        <Link className="text-pine-700" to="/forgot-password">
          Forgot your password?
        </Link>
      </p>
      {import.meta.env.VITE_SHOW_DEMO_HINT === "true" ? (
        <p className="mt-6 rounded-xl bg-paper px-4 py-3 text-sm text-ink-700">
          Local seed account: admin@tuition.example. The password is the SEED_ADMIN_PASSWORD value
          in the API environment file.
        </p>
      ) : null}
    </AuthShell>
  );
}
