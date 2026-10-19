import { collectAllPages } from "@shared/api/pages.js";

import { buildCsv, triggerCsvDownload } from "./csv.js";

/**
 * Exportacion CSV completa (docs/ux-ui.md 1.1): usa los filtros vigentes,
 * recorre TODAS las paginas del servidor (sin el tope de 1 000 filas que tenia
 * `collectAllPages`), informa el avance y se puede cancelar.
 *
 * Antes las pantallas exportaban "lo que ya se habia descargado", que tenia el
 * tope silencioso; ahora se pide a proposito, cuando la persona lo solicita.
 *
 * @param {object} options
 * @param {(params: object) => Promise<{results: Array, next: ?string, count: number}>} options.fetchPage
 * @param {object} [options.params] Filtros vigentes (p.ej. `list.exportParams` de `useServerList`).
 * @param {Array<{label: string, value: (row: object) => any}>} options.columns
 * @param {string} options.filename
 * @param {(progress: {loaded: number, total: number}) => void} [options.onProgress]
 * @param {AbortSignal} [options.signal]
 * @returns {Promise<number>} Filas exportadas.
 */
export async function exportAllToCsv({
  fetchPage,
  params = {},
  columns,
  filename,
  onProgress,
  signal,
}) {
  const rows = await collectAllPages(
    (pageParams) => fetchPage({ ...params, ...pageParams }),
    { onProgress, signal }
  );
  triggerCsvDownload(filename, buildCsv(columns, rows));
  return rows.length;
}
