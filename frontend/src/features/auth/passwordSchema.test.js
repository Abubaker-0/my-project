import { describe, expect, it } from "vitest";

import { passwordSchema } from "./passwordSchema";

describe("passwordSchema", () => {
  it("accepts a password that matches the API policy", () => {
    expect(passwordSchema.safeParse("Admin@12345").success).toBe(true);
  });

  it("rejects a password without a digit", () => {
    const result = passwordSchema.safeParse("AdminOnly");
    expect(result.success).toBe(false);
  });
});
