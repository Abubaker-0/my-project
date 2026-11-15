import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { listPermissions, listRoles, updateRolePermissions } from "../../api/resources";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { PageHeader } from "../../components/PageHeader";
import { Spinner } from "../../components/Spinner";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";

export function RolesPage() {
  const canAssign = usePermission("permissions:assign");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: () => listRoles({ page_size: 100, sort: "name" }),
  });
  const permissions = useQuery({ queryKey: ["permissions"], queryFn: listPermissions });
  const [selectedId, setSelectedId] = useState(null);
  const [draft, setDraft] = useState(null);
  const selected = (roles.data?.items ?? []).find(
    (role) => role.id === (selectedId ?? roles.data?.items?.[0]?.id),
  );

  const grouped = useMemo(() => {
    const groups = new Map();
    for (const permission of permissions.data ?? []) {
      const current = groups.get(permission.module) ?? [];
      current.push(permission);
      groups.set(permission.module, current);
    }
    return [...groups.entries()];
  }, [permissions.data]);

  const activeIds = draft ?? selected?.permissions.map((item) => item.id) ?? [];
  const locked = selected?.name === "super_admin" || !canAssign;

  const save = useMutation({
    mutationFn: () => updateRolePermissions(selected.id, activeIds),
    onSuccess: () => {
      push({ tone: "success", message: "Permissions updated." });
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });

  function choose(role) {
    setSelectedId(role.id);
    setDraft(role.permissions.map((item) => item.id));
  }

  function toggle(id) {
    if (selected && selectedId == null) {
      setSelectedId(selected.id);
    }
    setDraft((current) => {
      const base = current ?? selected.permissions.map((item) => item.id);
      return base.includes(id) ? base.filter((item) => item !== id) : [...base, id];
    });
  }

  if (roles.isLoading || permissions.isLoading) {
    return <Spinner label="Loading roles" />;
  }
  if (roles.isError || permissions.isError) {
    return (
      <ErrorState
        body="Roles could not be loaded."
        onRetry={() => {
          roles.refetch();
          permissions.refetch();
        }}
      />
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Roles"
        description="Roles are bundles of module:action permissions. Super Admin always keeps the full catalog."
      />
      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <ul className="space-y-1">
          {roles.data.items.map((role) => (
            <li key={role.id}>
              <button
                type="button"
                onClick={() => choose(role)}
                className={`w-full rounded-xl px-3 py-2 text-left text-sm ${
                  selected?.id === role.id ? "bg-pine-700 text-white" : "bg-card hover:bg-white"
                }`}
              >
                <span className="block font-medium">{role.label}</span>
                <span className={selected?.id === role.id ? "text-pine-50" : "text-ink-500"}>
                  {role.name}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {selected ? (
          <section className="rounded-2xl border border-line bg-card p-5 shadow-card">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-serif text-2xl">{selected.label}</h2>
                <p className="mt-1 text-sm text-ink-700">{selected.description}</p>
              </div>
              {canAssign ? (
                <Button onClick={() => save.mutate()} disabled={locked || save.isPending}>
                  {save.isPending ? "Saving" : "Save permissions"}
                </Button>
              ) : null}
            </div>
            <div className="mt-6 space-y-5">
              {grouped.map(([module, items]) => (
                <fieldset key={module} className="border-t border-line pt-3">
                  <legend className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-500">
                    {module}
                  </legend>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {items.map((permission) => (
                      <label key={permission.id} className="flex items-start gap-2 text-sm">
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={activeIds.includes(permission.id)}
                          disabled={locked}
                          onChange={() => toggle(permission.id)}
                        />
                        <span>
                          <span className="block font-medium">{permission.code}</span>
                          <span className="text-ink-500">{permission.description}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
