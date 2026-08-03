function escapeCsvValue(value) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

// `columns`: [{ label, value(row) }]. Serializa solo lo que ya se esta
// pintando en la tabla (filas visibles/filtradas) — sin logica de negocio,
// sin pedir nada nuevo al backend.
export function buildCsv(columns, rows) {
  const lines = [columns.map((column) => column.label), ...rows.map(
    (row) => columns.map((column) => escapeCsvValue(column.value(row)))
  )];
  return lines.map((line) => line.join(",")).join("\r\n");
}

export function triggerCsvDownload(filename, csv) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function downloadCsv(filename, columns, rows) {
  triggerCsvDownload(filename, buildCsv(columns, rows));
}
