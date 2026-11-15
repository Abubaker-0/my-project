import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { useAuthStore } from "../store/authStore";
import { RequireAuth } from "./RequireAuth";

describe("RequireAuth", () => {
  it("sends anonymous visitors to the login page", () => {
    useAuthStore.setState({ status: "anonymous", user: null, accessToken: null });
    render(
      <MemoryRouter
        initialEntries={["/secret"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/secret" element={<p>Secret</p>} />
          </Route>
          <Route path="/login" element={<p>Login screen</p>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("Login screen")).toBeInTheDocument();
  });
});
