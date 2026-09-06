import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * Catalogo cargado una vez y expuesto como opciones `{value,label}`.
 *
 * Es la base de todos los selectores que reemplazaron a los campos donde antes
 * se tecleaba un UUID a mano. El hook devuelve tambien `loading` y `error`
 * porque un desplegable vacio es ambiguo: "todavia no llega" y "no hay nada
 * registrado" son respuestas distintas y el formulario debe poder distinguirlas.
 *
 * `load` debe ser estable (definida a nivel de modulo, con nombre propio): el
 * hook la usa como parte de la query key, no solo como dependencia de un
 * efecto. Esto es lo que hace que dos componentes que llaman al mismo catalogo
 * (p.ej. una pantalla y un modal que abre sobre ella) compartan una sola
 * peticion en vez de disparar la suya por separado — antes cada instancia de
 * este hook tenia su propio estado local y su propio fetch.
 *
 * `reloadToken` fuerza la relectura despues de crear un registro del catalogo
 * desde otra pantalla.
 *
 * @param {() => Promise<Array<{value:string,label:string}>>} load
 * @param {number} [reloadToken]
 */
export function useCatalogOptions(load, reloadToken = 0) {
  const key = queryKeys.catalog(load.name, reloadToken);
  const { data, loading, error } = useResourceQuery(key, load, {
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
 */
export function useDependentCatalogOptions(buildLoad, dependency) {
  // No delega en `useCatalogOptions`: esa funcion arma su key con el nombre
  // de `load`, y aqui `load` es un closure anonimo (mismo nombre para
  // cualquier dependencia). Incluir `dependency` en la key evita que "secciones
  // del ciclo A" y "secciones del ciclo B" compartan una cubeta de cache.
  const key = queryKeys.catalog(`${buildLoad.name}:${dependency ?? ""}`);
  const { data, loading, error } = useResourceQuery(
    key,
    () => buildLoad(dependency),
    { enabled: Boolean(dependency), defaultData: [] }
  );

  return { options: data, error, loading, ready: Boolean(dependency) };
}
