/** Tope de seguridad: ningun listado deberia recorrer mas paginas que estas. */
const MAX_PAGES = 40;

/**
 * Recorre todas las paginas de un listado del backend y devuelve las filas.
 *
 * Los listados responden `{ count, next, previous, results }` con 25 filas por
 * pagina. Una pantalla que pagina y filtra del lado del cliente necesita el
 * conjunto completo: con solo la primera pagina, su propio paginador anuncia
 * "25 de 25" y el resto de los registros deja de existir para quien busca.
 *
 * @param {(params: object) => Promise<{results: Array, next: ?string}>} fetchPage
 */
export async function collectAllPages(fetchPage) {
  const collected = [];

  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const payload = await fetchPage({ page });
    collected.push(...(payload?.results ?? []));
    if (!payload?.next) {
      break;
    }
  }

  return collected;
}
