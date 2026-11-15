import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { logout } from "../api/auth";
import { listBranches } from "../api/resources";
import { ChangePasswordDialog } from "../features/auth/ChangePasswordDialog";
import { usePermission } from "../hooks/usePermission";
import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";

export function TopBar() {
  const user = useAuthStore((state) => state.user);
  const clear = useAuthStore((state) => state.clear);
  const canReadBranches = usePermission("branches:read");
  const branchId = useUiStore((state) => state.branchId);
  const setBranchId = useUiStore((state) => state.setBranchId);
  const toggleCollapsed = useUiStore((state) => state.toggleCollapsed);
  const setMobileNavOpen = useUiStore((state) => state.setMobileNavOpen);
  const [menuOpen, setMenuOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const queryClient = useQueryClient();
  const branches = useQuery({
    queryKey: ["branches", "switcher"],
    queryFn: () => listBranches(),
    enabled: canReadBranches,
  });

  async function signOut() {
    try {
      await logout();
    } finally {
      clear();
    }
  }

  return (
    <header className="flex h-16 items-center justify-between gap-3 border-b border-line bg-card px-4">
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-lg px-2 py-1 text-sm md:hidden"
          onClick={() => setMobileNavOpen(true)}
        >
          Menu
        </button>
        <button
          type="button"
          className="hidden rounded-lg px-2 py-1 text-sm text-ink-700 md:inline"
          onClick={toggleCollapsed}
        >
          Collapse
        </button>
      </div>
      <div className="flex items-center gap-3">
        {canReadBranches && (branches.data?.items?.length || 0) > 0 ? (
          <label className="text-sm text-ink-700">
            <span className="sr-only">Branch</span>
            <select
              className="field w-44"
              value={branchId || ""}
              onChange={(event) => {
                setBranchId(event.target.value);
                queryClient.invalidateQueries();
              }}
            >
              {user?.all_branches ? <option value="">All branches</option> : null}
              {branches.data.items.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <div className="relative">
          <button
            type="button"
            className="rounded-lg px-2 py-1 text-sm font-medium"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {user?.full_name}
          </button>
          {menuOpen ? (
            <div className="absolute right-0 z-20 mt-2 w-52 rounded-xl border border-line bg-card p-2 shadow-card">
              <p className="px-2 py-1 text-xs text-ink-500">{user?.email}</p>
              <button
                type="button"
                className="block w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-paper"
                onClick={() => {
                  setMenuOpen(false);
                  setPasswordOpen(true);
                }}
              >
                Change password
              </button>
              <button
                type="button"
                className="block w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-paper"
                onClick={signOut}
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>
      {passwordOpen ? <ChangePasswordDialog onClose={() => setPasswordOpen(false)} /> : null}
    </header>
  );
}
