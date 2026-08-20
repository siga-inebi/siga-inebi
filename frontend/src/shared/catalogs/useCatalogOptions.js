import { useCallback, useEffect, useState } from "react";

/**
 * Catalogo cargado una vez y expuesto como opciones `{value,label}`.
 *
 * Es la base de todos los selectores que reemplazaron a los campos donde antes
 * se tecleaba un UUID a mano. El hook devuelve tambien `loading` y `error`
 * porque un desplegable vacio es ambiguo: "todavia no llega" y "no hay nada
 * registrado" son respuestas distintas y el formulario debe poder distinguirlas.
 *
 * `load` debe ser estable (definida a nivel de modulo); el hook la usa como
 * dependencia del efecto. `reloadToken` fuerza la relectura despues de crear un
 * registro del catalogo desde otra pantalla.
 *
 * @param {() => Promise<Array<{value:string,label:string}>>} load
 * @param {number} [reloadToken]
 */
export function useCatalogOptions(load, reloadToken = 0) {
  const [options, setOptions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    load()
      .then((collected) => {
        if (active) {
          setOptions(collected);
        }
      })
      .catch((requestError) => {
        if (active) {
          setOptions([]);
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [load, reloadToken]);

  return { options, error, loading };
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
  const load = useCallback(
    () => (dependency ? buildLoad(dependency) : Promise.resolve([])),
    [buildLoad, dependency]
  );

  const catalog = useCatalogOptions(load);
  return { ...catalog, ready: Boolean(dependency) };
}
