const PUBLIC_PATHS = [
  "/auth/login",
  "/auth/refresh",
  "/auth/forgot-password",
  "/auth/reset-password",
];

export function isPublicAuthRequest(url = "") {
  return PUBLIC_PATHS.some((path) => url.includes(path));
}

export function createRefreshGate() {
  let inflight = null;
  return {
    reset() {
      inflight = null;
    },
    run(task) {
      if (!inflight) {
        inflight = Promise.resolve()
          .then(task)
          .finally(() => {
            inflight = null;
          });
      }
      return inflight;
    },
  };
}

export function attachRefreshInterceptor(client, { refresh, setToken, onFailure }) {
  const gate = createRefreshGate();
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config;
      if (
        error.response?.status !== 401 ||
        !original ||
        original._retry ||
        isPublicAuthRequest(original.url)
      ) {
        return Promise.reject(error);
      }
      original._retry = true;
      try {
        const token = await gate.run(refresh);
        setToken(token);
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${token}` };
        return client(original);
      } catch (refreshError) {
        onFailure(refreshError);
        return Promise.reject(refreshError);
      }
    },
  );
  return gate;
}
