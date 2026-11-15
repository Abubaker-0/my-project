import { useEffect } from "react";

import { fetchMe } from "../api/auth";
import { refreshAccessToken } from "../api/client";
import { FullScreenLoader } from "../components/Spinner";
import { useAuthStore } from "../store/authStore";

export function SessionGate({ children }) {
  const status = useAuthStore((state) => state.status);
  const setSession = useAuthStore((state) => state.setSession);
  const clear = useAuthStore((state) => state.clear);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const accessToken = await refreshAccessToken();
        const user = await fetchMe(accessToken);
        if (!cancelled) {
          setSession({ accessToken, user });
        }
      } catch {
        if (!cancelled) {
          clear();
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clear, setSession]);

  if (status === "unknown") {
    return <FullScreenLoader label="Checking your session" />;
  }
  return children;
}
