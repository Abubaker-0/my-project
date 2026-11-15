import { describe, expect, it } from "vitest";

import { calendarDay, seatSummary } from "./format";

describe("calendarDay", () => {
  it("maps Monday to FullCalendar's Monday and Sunday to its Sunday", () => {
    expect(calendarDay(0)).toBe(1);
    expect(calendarDay(6)).toBe(0);
  });
});

describe("seatSummary", () => {
  it("mentions the waitlist only when someone is waiting", () => {
    expect(seatSummary(12, 12, 3)).toBe("12 of 12 seats filled, 3 waiting");
    expect(seatSummary(8, 12, 0)).toBe("8 of 12 seats filled");
  });
});
