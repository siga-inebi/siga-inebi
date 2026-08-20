/**
 * format.js — Unico lugar donde se formatea para mostrar.
 *
 * Los formateadores viven aqui y solo aqui: una copia local en un componente es
 * la forma en que dos pantallas del mismo sistema terminan mostrando la misma
 * fecha de dos maneras distintas.
 */

/** Locale y zona horaria del establecimiento (Guatemala, UTC-6 sin horario de verano). */
export const APP_LOCALE = "es-GT";
export const APP_TIMEZONE = "America/Guatemala";

/** Marcador de valor ausente. Em dash, se pinta en `text.disabled`. */
export const EMPTY_VALUE = "—";

const dateFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: APP_TIMEZONE,
});

const dateLongFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: APP_TIMEZONE,
});

const dateTimeFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: APP_TIMEZONE,
});

/**
 * Convierte a Date solo si el valor es utilizable.
 *
 * Las fechas del backend llegan como `YYYY-MM-DD`, que el motor interpreta como
 * UTC; formatearlas en America/Guatemala las correria un dia hacia atras. Por
 * eso las fechas sin hora se anclan al mediodia, lejos de cualquier borde.
 */
function toDate(value) {
  if (!value) return null;
  const isDateOnly =
    typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
  const date = new Date(isDateOnly ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "6 ago 2026" */
export function formatDate(value) {
  const date = toDate(value);
  return date ? dateFormatter.format(date) : EMPTY_VALUE;
}

/** "6 de agosto de 2026" */
export function formatDateLong(value) {
  const date = toDate(value);
  return date ? dateLongFormatter.format(date) : EMPTY_VALUE;
}

/** "6 ago 2026, 03:45 p.m." */
export function formatDateTime(value) {
  const date = toDate(value);
  return date ? dateTimeFormatter.format(date) : EMPTY_VALUE;
}

/**
 * Hoy, en el formato `YYYY-MM-DD` que espera un `<input type="date">`.
 *
 * Se arma con las partes LOCALES de la fecha y no con `toISOString()`: ese
 * convierte a UTC, asi que en Guatemala (UTC-6) cualquier momento despues de las
 * 18:00 devolveria el dia siguiente. "Hoy" tiene que ser hoy aca.
 */
export function todayInputValue(now = new Date()) {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/** Devuelve el texto tal cual, o el marcador de ausencia si esta vacio. */
export function orEmpty(value) {
  if (value == null) return EMPTY_VALUE;
  const text = String(value).trim();
  return text === "" ? EMPTY_VALUE : text;
}

/** "87 %" — el espacio fino antes del signo es convencion tipografica en espanol. */
export function formatPercent(value, decimals = 0) {
  if (value == null || Number.isNaN(Number(value))) return EMPTY_VALUE;
  return `${Number(value).toFixed(decimals)} %`;
}

/** Nombre completo a partir de las partes que expone el backend. */
export function formatFullName(person) {
  if (!person) return EMPTY_VALUE;
  if (person.full_name) return person.full_name;
  const parts = [person.first_name, person.last_name].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : EMPTY_VALUE;
}
