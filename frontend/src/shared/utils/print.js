function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Imprime una hoja de instrucciones simple (codigo de activacion, enlace de
 * restablecimiento) sin depender de la pagina actual. Devuelve `false` si el
 * navegador bloqueo la ventana, para que la pantalla pueda decirlo.
 *
 * @param {string} title
 * @param {Array<{label?: string, value: string}>} lines
 */
export function printInstructions(title, lines) {
  const printWindow = window.open("", "_blank", "width=640,height=720");
  if (!printWindow) return false;
  const body = lines
    .map((line) =>
      line.label
        ? `<p><strong>${escapeHtml(line.label)}:</strong> ${escapeHtml(line.value)}</p>`
        : `<p>${escapeHtml(line.value)}</p>`
    )
    .join("");
  printWindow.document.write(
    `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${escapeHtml(
      title
    )}</title><style>body{font-family:system-ui,sans-serif;padding:32px;line-height:1.5}h1{font-size:20px}</style></head><body><h1>${escapeHtml(
      title
    )}</h1>${body}</body></html>`
  );
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
  return true;
}

/** Copia al portapapeles; devuelve `false` si el navegador no lo permite. */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
