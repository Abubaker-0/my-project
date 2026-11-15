import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "../app/navigation";
import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";

export function Sidebar() {
  const permissions = useAuthStore((state) => state.user?.permissions ?? []);
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const mobileOpen = useUiStore((state) => state.mobileNavOpen);
  const setMobileNavOpen = useUiStore((state) => state.setMobileNavOpen);
  const items = NAV_ITEMS.filter(
    (item) => !item.permission || permissions.includes(item.permission),
  );

  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-20 bg-ink-950/40 md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex h-screen flex-col bg-ink-950 text-paper transition-transform md:static md:h-screen md:shrink-0 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } ${collapsed ? "md:w-20" : "w-64"}`}
      >
        <div className="flex h-16 items-center gap-3 px-4">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-pine-700 font-serif text-lg">
            T
          </span>
          {collapsed ? null : (
            <div>
              <p className="font-serif text-lg leading-none">Tuition Center</p>
              <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-300">
                Management
              </p>
            </div>
          )}
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2" aria-label="Primary">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMobileNavOpen(false)}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-ink-300 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {collapsed ? item.label.slice(0, 1) : item.label}
            </NavLink>
          ))}
        </nav>
        {collapsed ? null : (
          <p className="px-4 pb-4 text-xs leading-5 text-ink-500">
            Admissions, courses, and enrollment sit on the same permissions and audit trail.
          </p>
        )}
      </aside>
    </>
  );
}
