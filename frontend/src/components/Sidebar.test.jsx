import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { useAuthStore } from "../store/authStore";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("hides links the user cannot open", () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "token",
      user: {
        full_name: "Ada Admin",
        permissions: ["users:read"],
        roles: [],
      },
    });
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Audit log" })).not.toBeInTheDocument();
  });
});
