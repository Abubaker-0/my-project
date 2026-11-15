import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useUiStore = create(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      mobileNavOpen: false,
      branchId: null,
      toggleCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setMobileNavOpen: (mobileNavOpen) => set({ mobileNavOpen }),
      setBranchId: (branchId) => set({ branchId: branchId || null }),
    }),
    {
      name: "tcm-ui",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        branchId: state.branchId,
      }),
    },
  ),
);
