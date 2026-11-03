import { APP_LOCALE, APP_TIMEZONE, EMPTY_VALUE } from "./format.js";

const weekdayDateFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: APP_TIMEZONE,
});

const numericDateTimeFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: APP_TIMEZONE,
});

const partsFormatter = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
  timeZone: APP_TIMEZONE,
});

/** Año actual según el reloj del establecimiento, no el del navegador. */
export function institutionalYear(now = new Date()) {
  const year = partsFormatter
    .formatToParts(now)
    .find(({ type }) => type === "year")?.value;
  return Number(year);
}

/** "miércoles, 19 de agosto" en la zona institucional. */
export function formatWeekdayDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? EMPTY_VALUE
    : weekdayDateFormatter.format(date);
}

/** "19/08/2026, 07:30 p.m." en la zona institucional. */
export function formatNumericDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? EMPTY_VALUE
    : numericDateTimeFormatter.format(date);
}

function offsetMilliseconds(instant) {
  const parts = Object.fromEntries(
    partsFormatter
      .formatToParts(instant)
      .filter(({ type }) => type !== "literal")
      .map(({ type, value }) => [type, Number(value)])
  );
  const representedAsUtc = Date.UTC(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second
  );
  return representedAsUtc - Math.floor(instant.getTime() / 1000) * 1000;
}

/** Convierte el inicio o fin de una fecha institucional a un instante ISO. */
export function dateInputBoundaryToIso(value, endOfDay = false) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
  const [year, month, day] = value.split("-").map(Number);
  const boundary = endOfDay ? [23, 59, 59] : [0, 0, 0];
  const wallClockUtc = Date.UTC(year, month - 1, day, ...boundary);
  let instant = new Date(wallClockUtc);
  for (let pass = 0; pass < 2; pass += 1) {
    instant = new Date(wallClockUtc - offsetMilliseconds(instant));
  }
  return instant.toISOString();
}
