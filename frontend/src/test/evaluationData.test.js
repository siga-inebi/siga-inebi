import { afterEach, describe, expect, test, vi } from "vitest";

import { defaultUnit } from "@evaluation/evaluationData.js";

afterEach(() => {
  vi.useRealTimers();
});

describe("evaluationData", () => {
  test("elige la unidad del dia institucional durante la tarde de Guatemala", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-20T01:30:00Z"));
    const localDay = {
      public_id: "local-day",
      status: "open",
      capture_starts_on: "2026-08-19",
      capture_ends_on: "2026-08-19",
    };
    const utcDay = {
      public_id: "utc-day",
      status: "open",
      capture_starts_on: "2026-08-20",
      capture_ends_on: "2026-08-20",
    };

    expect(defaultUnit([utcDay, localDay])).toBe(localDay);
  });
});
