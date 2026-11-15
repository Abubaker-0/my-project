import { Outlet } from "react-router-dom";

import { Sidebar } from "../components/Sidebar";
import { TopBar } from "../components/TopBar";

export function AppLayout() {
  return (
    <div className="h-screen overflow-hidden md:flex">
      <Sidebar />
      <div className="flex h-screen min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
