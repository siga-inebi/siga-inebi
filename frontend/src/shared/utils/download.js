/** Nombre de archivo del cabezal `Content-Disposition`, o `fallback`. */
export function filenameFromDisposition(disposition, fallback) {
  const match = /filename="?([^";]+)"?/i.exec(disposition || "");
  return match ? match[1] : fallback;
}

/** Descarga un archivo ya recibido sin dejar su URL viva en la pagina. */
export function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1000);
}

/**
 * Descarga la respuesta de `apiClient.postForFile`/`getFile` con el nombre que
 * manda el servidor en `Content-Disposition`, o `fallback` si no lo manda.
 *
 * @param {{blob: Blob, headers: Headers}} file
 * @param {string} fallback
 */
export function downloadResponseFile({ blob, headers }, fallback) {
  downloadBlob(
    filenameFromDisposition(headers?.get("Content-Disposition"), fallback),
    blob
  );
}
