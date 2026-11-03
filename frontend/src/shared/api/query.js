/**
 * query.js — Armado de query string para los endpoints del backend.
 *
 * Un solo lugar: cada servicio que se escribia su propio `withQuery` acababa
 * decidiendo distinto que hacer con `false` y con la cadena vacia, y eso se
 * nota cuando un filtro apagado viaja como `?include_inactive=false` y el
 * backend lo interpreta como presente.
 */

/**
 * @param {string} path
 * @param {object} [params]
 * @param {object} [options]
 * @param {boolean} [options.dropFalse=true] Omite los booleanos en `false`.
 *   Es el default porque en esta API un filtro apagado se expresa NO enviando
 *   el parametro. Pasar `false` cuando el valor `false` si es significativo
 *   (por ejemplo `?is_active=false`, que pide justamente los inactivos).
 */
export function withQuery(path, params, { dropFalse = true } = {}) {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    if (dropFalse && value === false) continue;
    query.set(key, String(value));
  }

  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}
