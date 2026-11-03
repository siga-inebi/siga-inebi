import { describe, expect, test } from "vitest";

import {
  evaluateBuildBudget,
  formatBudgetReport,
} from "./check-build-budget.mjs";

const manifest = {
  "index.html": {
    file: "assets/index.js",
    isEntry: true,
    imports: ["vendor"],
    dynamicImports: ["src/pages/AttendancePage.jsx"],
    css: ["assets/index.css"],
    assets: ["assets/logo.webp"],
  },
  vendor: { file: "assets/vendor.js" },
  "src/pages/AttendancePage.jsx": {
    file: "assets/attendance.js",
    isDynamicEntry: true,
    imports: ["vendor"],
  },
};

function sizes(overrides = {}) {
  return {
    "index.html": { raw: 1_000, gzip: 500 },
    "assets/index.js": { raw: 20_000, gzip: 10_000 },
    "assets/index.css": { raw: 4_000, gzip: 2_000 },
    "assets/logo.webp": { raw: 5_000, gzip: 4_000 },
    "assets/vendor.js": { raw: 100_000, gzip: 50_000 },
    "assets/attendance.js": { raw: 10_000, gzip: 5_000 },
    ...overrides,
  };
}

describe("frontend build budget", () => {
  test("passes when initial, lazy route, cold page, and raster stay below caps", () => {
    const result = evaluateBuildBudget(manifest, sizes());

    expect(result.initialGzip).toBe(66_500);
    expect(result.routes).toEqual([
      expect.objectContaining({
        key: "src/pages/AttendancePage.jsx",
        incrementGzip: 5_000,
        coldPageGzip: 71_500,
      }),
    ]);
    expect(result.violations).toEqual([]);
  });

  test("reports every exceeded cap with the responsible resource or route", () => {
    const result = evaluateBuildBudget(
      manifest,
      sizes({
        "assets/logo.webp": { raw: 25_001, gzip: 20_000 },
        "assets/attendance.js": { raw: 50_000, gzip: 20_001 },
      }),
      {
        initialGzip: 70_000,
        routeIncrementGzip: 20_000,
        coldPageGzip: 80_000,
        rasterRaw: 25_000,
      }
    );
    const report = formatBudgetReport(result, {
      initialGzip: 70_000,
      routeIncrementGzip: 20_000,
      coldPageGzip: 80_000,
      rasterRaw: 25_000,
    });

    expect(result.violations).toHaveLength(4);
    expect(report).toContain("initial static");
    expect(report).toContain("route src/pages/AttendancePage.jsx");
    expect(report).toContain("cold page src/pages/AttendancePage.jsx");
    expect(report).toContain("raster assets/logo.webp");
  });
});
