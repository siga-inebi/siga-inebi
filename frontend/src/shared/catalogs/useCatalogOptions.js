import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * Nombre de cache de un `load`.
 *
 * Antes la key salia de `load.name`. En el build de produccion los nombres se
 * minifican ("a", "b"...), asi que dos catalogos de chunks distintos podian
 * compartir cubeta y mostrarse cruzados (ux-ui 1.2.4). Ahora el nombre es
 * explicito: `defineCatalog("teachers", load)` o la opcion `key`. Para no
 * romper a quien todavia pasa una funcion sin nombre declarado, se asigna un
 * identificador estable POR FUNCION (no por nombre): la misma funcion comparte
 * cache, dos funciones distintas nunca.
 */
const anonymousKeys = new WeakMap();
let anonymousSequence = 0;

export function catalogKeyOf(load, explicitKey) {
  if (explicitKey) return explicitKey;
  if (load?.catalogKey) return load.catalogKey;
  if (!anonymousKeys.has(load)) {
    anonymousSequence += 1;
    anonymousKeys.set(load, `anonymous-${anonymousSequence}`);
  }
  return anonymousKeys.get(load);
}

/**
 * Declara el nombre de cache de un catalogo. Devuelve la misma funcion.
 *
 * @template {Function} T
 * @param {string} key  Nombre explicito, idealmente de `CATALOG` en `queryKeys.js`.
 * @param {T} load
 * @returns {T}
 */
export function defineCatalog(key, load) {
  load.catalogKey = key;
  return load;
}

/**
 * Catalogo cargado una vez y expuesto como opciones `{value,label}`.
 *
 * Es la base de todos los selectores que reemplazaron a los campos donde antes
 * se tecleaba un UUID a mano. El hook devuelve tambien `loading` y `error`
 * porque un desplegable vacio es ambiguo: "todavia no llega" y "no hay nada
 * registrado" son respuestas distintas y el formulario debe poder distinguirlas.
 *
 * Dos componentes que llaman al mismo catalogo (una pantalla y un modal que
 * abre sobre ella) comparten una sola peticion: la key es la misma.
 *
 * `reloadToken` fuerza la relectura despues de crear un registro del catalogo
 * desde otra pantalla. Ya no es imprescindible: toda escritura invalida
 * `["catalog", ...]` (ver `invalidation.js`).
 *
 * @param {() => Promise<Array<{value:string,label:string}>>} load
 * @param {number} [reloadToken]
 * @param {{key?: string}} [options]
 */
export function useCatalogOptions(load, reloadToken = 0, { key } = {}) {
  const queryKey = queryKeys.catalog(catalogKeyOf(load, key), reloadToken);
  const { data, loading, error } = useResourceQuery(queryKey, load, {
    defaultData: [],
  });

  return { options: data, error, loading };
}

/**
 * Combina varios catalogos en el estado agregado que necesita un formulario.
 *
 * Un formulario con cuatro selectores no puede razonar sobre cuatro estados de
 * carga sueltos: le basta saber si TODOS llegaron y si ALGUNO fallo.
 */
export function useCatalogsStatus(catalogs) {
  const loading = catalogs.some((catalog) => catalog.loading);
  const error = catalogs.map((catalog) => catalog.error).find(Boolean) ?? "";
  return { loading, error };
}

/**
 * Envuelve un `load` para que solo corra cuando ya se conoce su dependencia.
 *
 * Algunos catalogos dependen de otro valor del formulario (las secciones de un
 * ciclo, por ejemplo). Sin dependencia resuelta se devuelve una lista vacia en
 * vez de pedir el listado completo: ofrecer secciones de otro ciclo seria peor
 * que no ofrecer ninguna.
 *
 * La dependencia forma parte de la key: "secciones del ciclo A" y "secciones
 * del ciclo B" no comparten cubeta.
 */
export function useDependentCatalogOptions(
  buildLoad,
  dependency,
  { key } = {}
) {
  const queryKey = queryKeys.catalog(
    catalogKeyOf(buildLoad, key),
    "by",
    dependency ?? ""
  );
  const { data, loading, error } = useResourceQuery(
    queryKey,
    () => buildLoad(dependency),
    { enabled: Boolean(dependency), defaultData: [] }
  );

  return { options: data, error, loading, ready: Boolean(dependency) };
}
