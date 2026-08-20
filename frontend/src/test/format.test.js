import { describe, expect, test } from "vitest";

import {
  EMPTY_VALUE,
  formatDate,
  formatDateLong,
  formatDateTime,
  formatFullName,
  formatPercent,
  orEmpty,
  todayInputValue,
} from "@shared/utils/format.js";

describe("format", () => {
  describe("fechas", () => {
    test("formatea una fecha sin hora en la zona del establecimiento", () => {
      expect(formatDate("2026-08-06")).toBe("6 ago 2026");
    });

    test("no corre el dia hacia atras en una fecha sin hora", () => {
      // El motor interpreta "2026-01-01" como UTC; formatearlo en America/Guatemala
      // (UTC-6) daria 31 dic si no se anclara al mediodia. Este test existe para
      // que ese anclaje no se elimine por parecer innecesario.
      expect(formatDate("2026-01-01")).toBe("1 ene 2026");
      expect(formatDateLong("2026-01-01")).toBe("1 de enero de 2026");
    });

    test("formato largo", () => {
      expect(formatDateLong("2026-08-06")).toBe("6 de agosto de 2026");
    });

    test("formato con hora", () => {
      expect(formatDateTime("2026-08-06T21:45:00Z")).toMatch(/6 ago 2026/);
    });

    test("devuelve el marcador de ausencia cuando no hay valor", () => {
      expect(formatDate(null)).toBe(EMPTY_VALUE);
      expect(formatDate("")).toBe(EMPTY_VALUE);
      expect(formatDateLong(undefined)).toBe(EMPTY_VALUE);
      expect(formatDateTime(null)).toBe(EMPTY_VALUE);
    });

    test("devuelve el marcador de ausencia cuando la fecha es invalida", () => {
      expect(formatDate("no-es-fecha")).toBe(EMPTY_VALUE);
    });
  });

  describe("orEmpty", () => {
    test("deja pasar el texto con contenido", () => {
      expect(orEmpty("Ana")).toBe("Ana");
    });

    test("trata como ausente el vacio y el espacio en blanco", () => {
      expect(orEmpty("")).toBe(EMPTY_VALUE);
      expect(orEmpty("   ")).toBe(EMPTY_VALUE);
      expect(orEmpty(null)).toBe(EMPTY_VALUE);
      expect(orEmpty(undefined)).toBe(EMPTY_VALUE);
    });

    test("conserva el cero, que si es un valor", () => {
      expect(orEmpty(0)).toBe("0");
    });
  });

  describe("formatPercent", () => {
    test("agrega el signo con espacio", () => {
      expect(formatPercent(87)).toBe("87 %");
    });

    test("respeta los decimales pedidos", () => {
      expect(formatPercent(87.456, 1)).toBe("87.5 %");
    });

    test("devuelve el marcador de ausencia sin valor numerico", () => {
      expect(formatPercent(null)).toBe(EMPTY_VALUE);
      expect(formatPercent("abc")).toBe(EMPTY_VALUE);
    });
  });

  describe("formatFullName", () => {
    test("prefiere el nombre completo que ya trae el backend", () => {
      expect(
        formatFullName({
          full_name: "Ana Gomez Lopez",
          first_name: "Ana",
          last_name: "Gomez",
        })
      ).toBe("Ana Gomez Lopez");
    });

    test("compone el nombre con las partes disponibles", () => {
      expect(formatFullName({ first_name: "Ana", last_name: "Gomez" })).toBe(
        "Ana Gomez"
      );
      expect(formatFullName({ first_name: "Ana" })).toBe("Ana");
    });

    test("devuelve el marcador de ausencia sin persona", () => {
      expect(formatFullName(null)).toBe(EMPTY_VALUE);
      expect(formatFullName({})).toBe(EMPTY_VALUE);
    });
  });

  describe("todayInputValue", () => {
    test("usa la fecha LOCAL, no la UTC", () => {
      // 19:30 en Guatemala (UTC-6) ya es el dia siguiente en UTC. Con
      // `toISOString()` el boton "Hoy" habria puesto manana durante toda la
      // tarde, que es justo el horario en que se cierra la jornada.
      const lateEvening = new Date(2026, 7, 19, 19, 30);

      expect(todayInputValue(lateEvening)).toBe("2026-08-19");
    });

    test("rellena mes y dia a dos digitos", () => {
      // `<input type="date">` solo acepta YYYY-MM-DD; "2026-1-5" lo deja vacio.
      expect(todayInputValue(new Date(2026, 0, 5))).toBe("2026-01-05");
    });
  });
});
