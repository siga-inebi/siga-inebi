// Tope de seguridad: ningun selector deberia recorrer mas paginas que estas.
const MAX_PAGES = 40;

/**
 * Junta todas las filas de un listado paginado.
 *
 * Los selectores necesitan el catalogo entero: uno que solo ofreciera la
 * primera pagina ocultaria registros existentes sin avisar. `loader` recibe el
 * numero de pagina y devuelve la respuesta paginada del backend.
 */
export async function collectAllPages(loader) {
  const collected = [];

  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const payload = await loader(page);
    collected.push(...(payload?.results || []));
    if (!payload?.next) {
      break;
    }
  }

  return collected;
}
