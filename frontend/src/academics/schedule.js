/** Dias ISO (1 = lunes) con su nombre visible. */
export const WEEKDAYS = [
  [1, "Lunes"],
  [2, "Martes"],
  [3, "Miércoles"],
  [4, "Jueves"],
  [5, "Viernes"],
  [6, "Sábado"],
  [7, "Domingo"],
];

/** "07:30:00" -> "07:30". */
export function formatTime(value) {
  if (!value) return "";
  return String(value).slice(0, 5);
}

export function blockLabel(block) {
  if (!block) return "—";
  const name = block.name || `Bloque ${block.number}`;
  const range =
    block.starts_on && block.ends_on
      ? `${formatTime(block.starts_on)}–${formatTime(block.ends_on)}`
      : "";
  return range ? `${name} · ${range}` : name;
}
