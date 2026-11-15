import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchSessions } from "../../api/auth";
import { fetchHealth } from "../../api/resources";
import { Badge } from "../../components/Badge";
import { PageHeader } from "../../components/PageHeader";
import { Spinner } from "../../components/Spinner";
import { useAuthStore } from "../../store/authStore";
import { formatDateTime } from "../../utils/format";

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: fetchSessions });
  const counts = new Map();
  for (const code of user?.permissions ?? []) {
    const module = code.split(":")[0];
    counts.set(module, (counts.get(module) || 0) + 1);
  }
  const chartData = [...counts.entries()]
    .map(([module, count]) => ({ module, count }))
    .sort((left, right) => right.count - left.count)
    .slice(0, 8);

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title={`Hello, ${user?.full_name?.split(" ")[0] || "there"}`}
        description="Your access, the API, and the sessions currently open for this account."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <article className="rounded-2xl border border-line bg-card p-5 shadow-card">
          <p className="text-xs uppercase tracking-[0.14em] text-ink-500">Signed in as</p>
          <p className="mt-2 font-medium">{user?.email}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(user?.roles ?? []).map((role) => (
              <Badge key={`${role.role_id}-${role.branch_id ?? "all"}`} tone="good">
                {role.role_label}
                {role.branch_name
                  ? ` · ${role.branch_name}`
                  : role.branch_id
                    ? ""
                    : " · all branches"}
              </Badge>
            ))}
          </div>
        </article>
        <article className="rounded-2xl border border-line bg-card p-5 shadow-card">
          <p className="text-xs uppercase tracking-[0.14em] text-ink-500">API</p>
          {health.isLoading ? <Spinner label="Checking" /> : null}
          {health.isError ? (
            <p className="mt-2 text-sm text-danger">The API health check failed.</p>
          ) : null}
          {health.data ? (
            <p className="mt-2 text-sm">
              {health.data.app} {health.data.version} · database {health.data.database}
            </p>
          ) : null}
        </article>
        <article className="rounded-2xl border border-line bg-card p-5 shadow-card">
          <p className="text-xs uppercase tracking-[0.14em] text-ink-500">Permissions</p>
          <p className="mt-2 font-serif text-4xl">{user?.permissions?.length ?? 0}</p>
          <p className="text-sm text-ink-700">
            {user?.all_branches ? "All branches" : "Limited to assigned branches"}
          </p>
        </article>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <article className="rounded-2xl border border-line bg-card p-5 shadow-card lg:col-span-3">
          <h2 className="font-serif text-2xl">Access by module</h2>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis
                  dataKey="module"
                  tick={{ fontSize: 12 }}
                  interval={0}
                  angle={-25}
                  height={60}
                  textAnchor="end"
                />
                <YAxis allowDecimals={false} width={28} />
                <Tooltip />
                <Bar dataKey="count" fill="#1f6f68" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
        <article className="rounded-2xl border border-line bg-card p-5 shadow-card lg:col-span-2">
          <h2 className="font-serif text-2xl">Sessions</h2>
          {sessions.isLoading ? (
            <div className="mt-4">
              <Spinner label="Loading sessions" />
            </div>
          ) : null}
          {sessions.isError ? (
            <p className="mt-4 text-sm text-danger">Sessions could not be loaded.</p>
          ) : null}
          <ul className="mt-4 space-y-3">
            {(sessions.data ?? []).map((session) => (
              <li key={session.id} className="rounded-xl bg-paper px-3 py-2 text-sm">
                <p className="font-medium">{session.current ? "This browser" : "Other session"}</p>
                <p className="text-ink-700">{session.ip || "Unknown address"}</p>
                <p className="text-ink-500">Opened {formatDateTime(session.created_at)}</p>
              </li>
            ))}
            {!sessions.isLoading && (sessions.data ?? []).length === 0 ? (
              <li className="text-sm text-ink-700">No active refresh sessions were found.</li>
            ) : null}
          </ul>
        </article>
      </div>
    </div>
  );
}
