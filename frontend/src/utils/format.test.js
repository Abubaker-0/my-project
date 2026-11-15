import { describe, expect, it } from "vitest";

import { seatSummary } from "./format";

describe("seatSummary", () => {
  it("mentions the waitlist only when someone is waiting", () => {
    expect(seatSummary(12, 12, 3)).toBe("12 of 12 seats filled, 3 waiting");
    expect(seatSummary(8, 12, 0)).toBe("8 of 12 seats filled");
  });
});
