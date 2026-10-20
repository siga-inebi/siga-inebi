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

/**
 * Imprime el carné del estudiante (RF-CRE-002): el contenido imprimible que
 * entrega el backend y el QR de la emisión (PNG en base64). El QR solo existe
 * en la respuesta de emisión, así que esta hoja no se puede rehacer después.
 * Devuelve `false` si el navegador bloqueó la ventana.
 *
 * @param {object} content  Respuesta de `credentials/print-content/`.
 * @param {string} qrBase64 `qr_code` de la emisión.
 */
export function printStudentCard(content, qrBase64) {
  const printWindow = window.open("", "_blank", "width=480,height=640");
  if (!printWindow) return false;
  const photo = content.photo_url
    ? `<img class="photo" alt="Fotografía" src="${escapeHtml(content.photo_url)}">`
    : "";
  const line = (label, value) =>
    value ? `<p><span>${escapeHtml(label)}</span>${escapeHtml(value)}</p>` : "";
  printWindow.document.write(
    `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Carné de ${escapeHtml(
      content.full_name
    )}</title><style>body{font-family:system-ui,sans-serif;margin:24px}.card{width:86mm;border:1px solid #333;border-radius:8px;padding:12px;display:grid;gap:6px}h1{font-size:13px;margin:0;text-transform:uppercase;letter-spacing:.04em}h2{font-size:16px;margin:4px 0}p{margin:0;font-size:12px}p span{display:block;font-size:9px;text-transform:uppercase;color:#555}.row{display:flex;gap:10px;align-items:flex-start}.photo{width:22mm;height:28mm;object-fit:cover;border:1px solid #ccc}.qr{width:32mm;height:32mm;justify-self:center}</style></head><body><div class="card"><h1>${escapeHtml(
      content.institution_name
    )}</h1><div class="row">${photo}<div><h2>${escapeHtml(
      content.full_name
    )}</h2>${line("Grado y sección", [content.grade_name, content.section_name].filter(Boolean).join(" "))}${line(
      "Ciclo escolar",
      content.academic_cycle_name
    )}</div></div><img class="qr" alt="Código QR del carné" src="data:image/png;base64,${escapeHtml(
      qrBase64
    )}"></div></body></html>`
  );
  printWindow.document.close();
  printWindow.focus();
  const qr = printWindow.document.querySelector("img.qr");
  const go = () => printWindow.print();
  if (qr && !qr.complete) qr.addEventListener("load", go, { once: true });
  else go();
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
