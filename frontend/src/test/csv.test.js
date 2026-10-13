import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { buildCsv, triggerCsvDownload } from "@shared/utils/csv.js";

describe("buildCsv", () => {
  const columns = [
    { label: "Nombre", value: (row) => row.name },
    { label: "Edad", value: (row) => row.age },
  ];

  test("builds a header row plus one row per record", () => {
    const csv = buildCsv(columns, [
      { name: "Ana", age: 16 },
      { name: "Luis", age: 15 },
    ]);

    expect(csv).toBe("Nombre,Edad\r\nAna,16\r\nLuis,15");
  });

  test("escapes values containing commas, quotes or newlines", () => {
    const csv = buildCsv(
      [{ label: "Texto", value: (row) => row.text }],
      [{ text: 'Contiene, coma y "comillas"\nsalto de linea' }]
    );

    expect(csv).toBe(
      'Texto\r\n"Contiene, coma y ""comillas""\nsalto de linea"'
    );
  });

  test("renders null/undefined values as empty cells", () => {
    const csv = buildCsv(columns, [{ name: "Sin edad", age: null }]);

    expect(csv).toBe("Nombre,Edad\r\nSin edad,");
  });

  test("returns just the header when there are no rows", () => {
    expect(buildCsv(columns, [])).toBe("Nombre,Edad");
  });
});

describe("triggerCsvDownload", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test-csv");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tagName, options) => {
      const element = originalCreateElement(tagName, options);

      if (tagName === "a") {
        vi.spyOn(element, "click").mockImplementation(() => {});
      }

      return element;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  test("keeps the object URL alive long enough for the browser to start the download", () => {
    triggerCsvDownload("alumnos.csv", "nombre,codigo\nAna,EST-2026-0001");

    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test-csv");
  });
});
