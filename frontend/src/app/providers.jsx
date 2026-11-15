import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter } from "react-router-dom";

import { ToastViewport } from "../components/ToastViewport";
import { SessionGate } from "./SessionGate";

export function AppProviders({ children }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <SessionGate>{children}</SessionGate>
        <ToastViewport />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
