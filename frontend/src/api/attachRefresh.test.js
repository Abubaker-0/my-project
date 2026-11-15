import { describe, expect, it, vi } from "vitest";

import { attachRefreshInterceptor, createRefreshGate, isPublicAuthRequest } from "./attachRefresh";

describe("refresh handling", () => {
  it("recognises public auth routes", () => {
    expect(isPublicAuthRequest("/auth/login")).toBe(true);
    expect(isPublicAuthRequest("/users")).toBe(false);
  });

  it("runs one refresh for overlapping callers", async () => {
    const gate = createRefreshGate();
    const task = vi.fn(() => new Promise((resolve) => setTimeout(() => resolve("token"), 15)));
    const [first, second] = await Promise.all([gate.run(task), gate.run(task)]);
    expect(first).toBe("token");
    expect(second).toBe("token");
    expect(task).toHaveBeenCalledTimes(1);
  });

  it("retries a protected request once after refresh", async () => {
    const calls = [];
    const handlers = [];
    const client = (config) => {
      const start = Promise.resolve().then(() => transport(config));
      return handlers.reduce(
        (promise, handler) => promise.then(handler.success, handler.failure),
        start,
      );
    };
    client.interceptors = {
      response: {
        use(success, failure) {
          handlers.push({ success, failure });
        },
      },
    };
    function transport(config) {
      calls.push(config.url);
      if (config.url === "/secure" && !config.headers?.Authorization) {
        return Promise.reject({ config, response: { status: 401 } });
      }
      return Promise.resolve({ data: { ok: true }, config });
    }
    attachRefreshInterceptor(client, {
      refresh: () => Promise.resolve("fresh-token"),
      setToken: vi.fn(),
      onFailure: vi.fn(),
    });
    const result = await client({ url: "/secure", headers: {} });
    expect(result.data.ok).toBe(true);
    expect(calls).toEqual(["/secure", "/secure"]);
  });
});
